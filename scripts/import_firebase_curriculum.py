"""Explicit additive draft import; accepts optional private content overrides."""
import argparse
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_curriculum import load_source,apply_source_overrides,import_static_drafts
from firebase_migration import inspect_transfer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,type=Path)
    parser.add_argument('--transfer',type=Path,help='Actual private Firebase working transfer; content overrides only')
    args=parser.parse_args();source=load_source();report={}
    if not args.database.is_file():parser.error('Select an existing initialized database')
    if args.transfer:
        if args.transfer.stat().st_size>64*1024*1024:parser.error('Transfer exceeds 64 MB')
        payload=json.loads(args.transfer.read_text(encoding='utf-8'));inspect_transfer(payload)
        source,report=apply_source_overrides(source,payload['collections'])
    with sqlite3.connect(args.database) as db:
        required={'courses','course_lessons','lesson_revisions','course_rules'}
        if not required<={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}:parser.error('Database is not initialized')
        db.execute('BEGIN IMMEDIATE');added=import_static_drafts(db,'firebase-content-migration',source)
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
    print(json.dumps(dict(added_drafts=added,published_new=0,overrides=report),ensure_ascii=False))

if __name__=='__main__':main()
