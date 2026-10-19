"""Build a new private runtime candidate; never modify a running or existing DB."""
import json
import os
from pathlib import Path
import re
import sqlite3
from contextlib import closing
from firebase_eps_bank import import_bank
from firebase_learning_migration import apply_learning
from firebase_migration import inspect_transfer
from firebase_reconciliation import reconcile_transfer
from firebase_curriculum import load_source,apply_source_overrides,import_static_drafts


def build_candidate(payload,destination,source=None):
    records,inspection=inspect_transfer(payload);plan=reconcile_transfer(payload)
    identities=[]
    for identity in plan['identities']:
        issues=set(identity['issues'])-{'deleted_profile'}
        if issues:raise ValueError('Resolve ambiguous identity data before building runtime')
        if 'deleted_profile' in identity['issues']:continue
        name=identity['username']
        if not re.fullmatch(r'[a-z0-9_.]{1,100}',name):raise ValueError('Unsupported original username; explicit mapping required')
        identities.append(identity)
    destination=Path(destination).expanduser().absolute();parent=destination.parent.resolve()
    root=Path(__file__).resolve().parent
    if parent==root or root in parent.parents:raise ValueError('Private candidate must be outside source')
    if not parent.is_dir():raise ValueError('Select an existing private parent directory')
    patched,overrides=apply_source_overrides(source or load_source(),payload['collections'])
    destination.mkdir(mode=0o700,exist_ok=False)
    def connect(name):
        path=destination/name;fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        return closing(sqlite3.connect(path))
    profiles={row['id']:row['data'] for row in payload['collections'].get('thana_users',[])}
    users={}
    for identity in identities:
        profile=profiles[identity['firebase_uid']];name=profile.get('name')
        users[identity['username']]=dict(username=identity['username'],name=name if isinstance(name,str) and name.strip() else identity['username'],
            role=identity['source_role'],status='approved' if identity['approved'] else 'pending',
            auth_version=1,auth_method='firebase_only',firebase_uid=identity['firebase_uid'],pw=None)
    with connect('legacy.sqlite3') as db,db:
        db.execute('CREATE TABLE documents (name TEXT PRIMARY KEY, content TEXT NOT NULL)')
        db.executemany('INSERT INTO documents VALUES (?,?)',[(name,json.dumps(value,ensure_ascii=False)) for name,value in [('users.json',users),('progress.json',{})]])
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    with connect('platform.sqlite3') as db,db:
        db.executescript('CREATE TABLE courses(id TEXT PRIMARY KEY,title TEXT,language TEXT,instruction TEXT,description TEXT); CREATE TABLE course_lessons(id TEXT PRIMARY KEY,course TEXT,draft TEXT,published TEXT,revision INTEGER,updated REAL); CREATE TABLE course_rules(course TEXT PRIMARY KEY,sequential INTEGER); CREATE TABLE lesson_revisions(lesson TEXT,revision INTEGER,content TEXT,actor TEXT,created REAL,PRIMARY KEY(lesson,revision)); CREATE TABLE firebase_account_bindings(uid TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,enabled INTEGER NOT NULL DEFAULT 0); CREATE TABLE firebase_source_records(collection TEXT NOT NULL,document_id TEXT NOT NULL,data TEXT NOT NULL,firestore_fields TEXT,PRIMARY KEY(collection,document_id)); CREATE TABLE firebase_candidate_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);')
        db.executemany('INSERT INTO firebase_account_bindings VALUES (?,?,0)',[(u['firebase_uid'],u['username']) for u in identities])
        db.executemany('INSERT INTO firebase_source_records VALUES (?,?,?,?)',records)
        added=import_static_drafts(db,'firebase-runtime-candidate',patched)
        db.execute('CREATE TABLE course_progress(owner TEXT,lesson TEXT,score INTEGER,completed REAL,PRIMARY KEY(owner,lesson))')
        db.execute('CREATE TABLE premium_courses(course TEXT PRIMARY KEY)')
        db.execute('CREATE TABLE lesson_access(lesson TEXT PRIMARY KEY,mode TEXT NOT NULL,revision INTEGER NOT NULL)')
        for course in ('firebase-thana-lessons-v1','firebase-thana-seasonal-v1'):db.execute('INSERT INTO premium_courses VALUES (?)',(course,))
        for lesson in patched['constants']['DEFAULT_LESSONS']:
            if lesson.get('free') is True:db.execute('INSERT INTO lesson_access VALUES (?,?,1)',(lesson['id'],'free'))
        eps_added=import_bank(db,patched)
        learning=apply_learning(db,payload)
        report=dict(status='prepared-not-enabled',profiles=len(users),deleted_profiles_not_activated=plan['summary']['issues'].get('deleted_profile',0),
            eps_draft_questions=eps_added,eps_question_progress=learning['eps_question_rows_added'],disabled_uid_bindings=len(identities),source_records=len(records),drafts=added,published=0,
            unresolved_progress_owners=plan['summary']['issues'].get('unknown_owner',0),overrides=overrides,
            active_progress=learning['lesson_completions_added'],scoped_entitlement_rows=learning['scope_rows_added'],learning_import=learning,applied_entitlements=0,
            pending=['Firebase credentials and explicit binding enablement','Original lesson/media/EPS review','Remaining history/media review and learner acceptance','Production preflight and acceptance'])
        db.execute('INSERT INTO firebase_candidate_metadata VALUES (?,?)',('status',json.dumps(report)))
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    fd=os.open(destination/'candidate-report.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(report,output,ensure_ascii=False)
    return report
