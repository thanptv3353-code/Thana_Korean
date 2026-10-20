"""Preserve legacy seasonal results separately from current exam attempts."""
import datetime
import json
import math

COLLECTION='thana_seasonal_exam_results'


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS firebase_result_imports (collection TEXT,document TEXT,source TEXT NOT NULL,status TEXT NOT NULL,PRIMARY KEY(collection,document))')
    db.execute('CREATE TABLE IF NOT EXISTS firebase_original_results (collection TEXT,document TEXT,uid TEXT NOT NULL,group_id TEXT NOT NULL,score INTEGER NOT NULL,total INTEGER NOT NULL,pct INTEGER NOT NULL,passed INTEGER NOT NULL,submitted REAL NOT NULL,PRIMARY KEY(collection,document))')
    db.execute('CREATE INDEX IF NOT EXISTS firebase_original_results_owner ON firebase_original_results(uid,submitted)')


def import_results(db,payload):
    initialize(db)
    profiles={r['id']:r['data'] for r in payload['collections'].get('thana_users',[])}
    bindings=dict(db.execute('SELECT uid,username FROM firebase_account_bindings').fetchall())
    rows=payload['collections'].get(COLLECTION,[])
    # Reject changed journal inputs before any result is applied.
    for row in rows:
        old=db.execute('SELECT source FROM firebase_result_imports WHERE collection=? AND document=?',(COLLECTION,row['id'])).fetchone()
        if old and json.loads(old[0])!=row['data']:
            raise ValueError('Original result changed; explicit review required')
    added=0;statuses={}
    for row in rows:
        if db.execute('SELECT 1 FROM firebase_result_imports WHERE collection=? AND document=?',(COLLECTION,row['id'])).fetchone():continue
        data=row['data'];uid=data.get('uid');profile=profiles.get(uid) if isinstance(uid,str) else None
        status='unresolved-owner'
        if profile and profile.get('deletedAt') is not None:status='inactive-source-owner'
        elif profile and bindings.get(uid)==profile.get('username'):
            try:
                group=data['groupId'];score=data['score'];total=data['total'];pct=data['pct'];passed=data['passed']
                if not isinstance(group,str) or not 1<=len(group)<=200:raise ValueError()
                if type(score) is not int or type(total) is not int or not 1<=total<=100000 or not 0<=score<=total:raise ValueError()
                if type(pct) is not int or pct!=math.floor(100*score/total+0.5):raise ValueError()
                if type(passed) is not bool or passed!=(pct>=70):raise ValueError()
                stamp=datetime.datetime.fromisoformat(data['submittedAt'].replace('Z','+00:00'))
                if stamp.tzinfo is None or not math.isfinite(stamp.timestamp()) or stamp.timestamp()<=0:raise ValueError()
            except (KeyError,ValueError,TypeError,AttributeError,OverflowError):status='invalid-source-result'
            else:
                db.execute('INSERT INTO firebase_original_results VALUES (?,?,?,?,?,?,?,?,?)',(COLLECTION,row['id'],uid,group,score,total,pct,int(passed),stamp.timestamp()))
                status='imported-original-result';added+=1
        statuses[status]=statuses.get(status,0)+1
        db.execute('INSERT INTO firebase_result_imports VALUES (?,?,?,?)',(COLLECTION,row['id'],json.dumps(data,ensure_ascii=False),status))
    return dict(added=added,statuses=statuses)
