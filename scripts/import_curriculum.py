"""Explicit operator import into an existing initialized database; drafts only."""
import argparse
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from curriculum_pack import import_drafts

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--database',required=True,type=Path)
p.add_argument('--language',choices=('all','ko','lo'),default='all')
args=p.parse_args()
if not args.database.is_file():p.error('Select an existing initialized database')
with sqlite3.connect(args.database) as c:
    required={'courses','course_lessons','lesson_revisions','course_levels','course_rules'}
    present={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not required<=present:p.error('Database is not initialized for structured courses')
    c.execute('BEGIN IMMEDIATE')
    counts=import_drafts(c,'curriculum-authoring',args.language)
    assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print('New unpublished drafts:',sum(counts.values()),counts)
