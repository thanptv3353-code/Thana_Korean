"""Transactional compatibility store for preserved legacy JSON document schemas.

Imports original files once; subsequent writes go only to SQLite. This is an
intermediate migration, not a normalized PostgreSQL schema.
"""
import json,os,sqlite3,threading
from flask import g,has_request_context

class LegacyStorage:
    def __init__(self,directory):
        self.path=os.path.join(directory,'legacy.sqlite3')
        self.gate=threading.RLock()
        c=self.connect()
        try:
            with c:c.execute('CREATE TABLE IF NOT EXISTS documents (name TEXT PRIMARY KEY, content TEXT NOT NULL)')
        finally:c.close()
    def connect(self):
        c=sqlite3.connect(self.path,timeout=30);c.execute('PRAGMA busy_timeout=30000');return c
    def load(self,path,default):
        name=os.path.basename(path)
        if has_request_context() and getattr(g,'legacy_connection',None):
            row=g.legacy_connection.execute('SELECT content FROM documents WHERE name=?',(name,)).fetchone()
            return json.loads(row[0]) if row else default
        c=self.connect()
        try:
            with c:
                row=c.execute('SELECT content FROM documents WHERE name=?',(name,)).fetchone()
                if row:return json.loads(row[0])
                if not os.path.exists(path):return default
                with open(path,encoding='utf-8') as f:value=json.load(f)
                expected=list if name=='lessons.json' else dict
                if not isinstance(value,expected):raise ValueError('Unexpected legacy data schema: '+name)
                c.execute('INSERT OR IGNORE INTO documents VALUES (?,?)',(name,json.dumps(value,ensure_ascii=False)))
                return json.loads(c.execute('SELECT content FROM documents WHERE name=?',(name,)).fetchone()[0])
        finally:c.close()
    def save(self,path,value):
        name=os.path.basename(path);payload=json.dumps(value,ensure_ascii=False)
        if has_request_context() and getattr(g,'legacy_connection',None):
            g.legacy_connection.execute('INSERT OR REPLACE INTO documents VALUES (?,?)',(name,payload));return
        c=self.connect()
        try:
            with c:c.execute('INSERT OR REPLACE INTO documents VALUES (?,?)',(name,payload))
        finally:c.close()
    def install(self,app,namespace):
        @app.before_request
        def open_legacy_transaction():
            self.gate.acquire();g.legacy_gate=True
            c=self.connect();g.legacy_connection=c;c.execute('BEGIN IMMEDIATE')
            for key,path,default in [('users','USERS_FILE',{}),('lessons','LESSONS_FILE',[]),('progress','PROGRESS_FILE',{})]:
                namespace[key]=self.load(namespace[path],default)
        @app.after_request
        def finish_legacy_transaction(response):
            c=getattr(g,'legacy_connection',None)
            if c:
                if response.status_code>=400:c.rollback()
                else:c.commit()
            return response
        @app.teardown_request
        def close_legacy_transaction(error):
            c=getattr(g,'legacy_connection',None)
            if c:
                if c.in_transaction:c.rollback()
                c.close();g.legacy_connection=None
            if getattr(g,'legacy_gate',False):self.gate.release();g.legacy_gate=False
