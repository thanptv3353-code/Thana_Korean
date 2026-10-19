"""Offline Firebase transfer inspection/staging; never creates usable app accounts."""
import json
import os
import sqlite3
from collections import Counter
from contextlib import closing
from pathlib import Path

PROJECT='korean-lao-exam'
COLLECTIONS={'thana_users','thana_usernames','thana_progress','thana_lessons',
 'thana_lesson_meta','thana_phrases','thana_grammar_overrides','thana_eps_overrides',
 'thana_seasonal_overrides','thana_seasonal_exam_groups','thana_seasonal_exam_results',
 'thana_settings','thana_payments','thana_phone_orders','thana_announcements',
 'users','examConfig','examGroups','examResults','paymentProofs','paymentSettings'}


def inspect_transfer(payload):
    if not isinstance(payload,dict) or set(payload)!={'project','collections'} or payload['project']!=PROJECT:
        raise ValueError('Expected the korean-lao-exam project transfer')
    collections=payload['collections']
    if not isinstance(collections,dict) or not collections or set(collections)-COLLECTIONS:
        raise ValueError('Unsupported collection; credential/config exports are not accepted')
    records=[];schemas={};counts={};profiles={};progress=[]
    for collection,documents in collections.items():
        if not isinstance(documents,list):raise ValueError('Collection documents must be a list')
        seen=set();fields=set()
        for document in documents:
            if not isinstance(document,dict) or (set(document)-{'id','data','firestore_fields'} or not {'id','data'}<=set(document)):raise ValueError('Expected document id and data')
            identity=document['id'];data=document['data']
            if not isinstance(identity,str) or not identity or '/' in identity or len(identity)>1500 or identity in seen:
                raise ValueError('Invalid or duplicate document identity')
            if not isinstance(data,dict):raise ValueError('Document data must be an object')
            # Strict JSON: reject NaN/Infinity and unsupported Python objects.
            raw=json.dumps(data,ensure_ascii=False,allow_nan=False)
            wire=document.get('firestore_fields')
            if wire is not None:
                from scripts.read_firebase_transfer import value
                if not isinstance(wire,dict) or {k:value(v) for k,v in wire.items()}!=data:raise ValueError('Decoded Firestore data mismatch')
            seen.add(identity);fields.update(data);records.append((collection,identity,raw,json.dumps(wire,ensure_ascii=False,allow_nan=False) if wire is not None else None))
            if collection=='thana_users':profiles[identity]=data
            if collection=='thana_progress':progress.append(data)
        counts[collection]=len(documents);schemas[collection]=sorted(fields)
    kinds=Counter();orphaned=0;unknown_roles=0
    for data in progress:
        kind='lesson' if isinstance(data.get('lessonId'),str) else 'eps' if any(k in data for k in ('correct','attempted','freeUsed')) else 'missed_words' if 'words' in data else 'unclassified'
        kinds[kind]+=1
        if not isinstance(data.get('uid'),str) or data['uid'] not in profiles:orphaned+=1
    for data in profiles.values():
        if data.get('role') not in ('admin','student'):unknown_roles+=1
    report=dict(project=PROJECT,collections=counts,field_names=schemas,records=len(records),
        progress_kinds=dict(kinds),progress_without_known_profile=orphaned,
        profiles_with_unknown_role=unknown_roles,
        missing_collections=sorted(COLLECTIONS-set(collections)),
        authentication='Firebase Auth identities/passwords are not included; no local login is enabled',
        status='inspection-only; not a completed application migration')
    return records,report


def stage_transfer(payload,destination,source_root=None):
    records,report=inspect_transfer(payload)
    destination=Path(destination).expanduser().absolute()
    root=Path(source_root or Path(__file__).resolve().parent).resolve()
    parent=destination.parent.resolve()
    if parent==root or root in parent.parents:raise ValueError('Private migration data must be outside source')
    if not parent.is_dir():raise ValueError('Select an existing private destination directory')
    # Exclusive file creation prevents overwriting either staging or application DBs.
    descriptor=os.open(destination,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(destination)) as database, database:
            database.execute('CREATE TABLE firebase_source_records (collection TEXT NOT NULL, document_id TEXT NOT NULL, data TEXT NOT NULL, firestore_fields TEXT, PRIMARY KEY(collection,document_id))')
            database.executemany('INSERT INTO firebase_source_records VALUES (?,?,?,?)',records)
            database.execute('CREATE TABLE firebase_transfer_metadata (project TEXT NOT NULL, status TEXT NOT NULL)')
            database.execute('INSERT INTO firebase_transfer_metadata VALUES (?,?)',(PROJECT,'staged-not-applied'))
            if database.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Staging integrity check failed')
        return dict(report,status='staged-not-applied; no application accounts, access or progress changed')
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
