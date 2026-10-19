import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from PIL import Image
from firebase_curriculum import load_source
from firebase_eps_bank import import_bank
from firebase_eps_media import inventory
from firebase_media_import import import_recovered_images
from scripts.collect_local_firebase_media import collect_local

class FirebaseRecoveredMediaTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.original=self.root/'original';(self.original/'images').mkdir(parents=True)
        for index,color in ((1,'red'),(2,'blue')):Image.new('RGB',(4,4),color).save(self.original/'images'/f'q{index:04d}.png')
        self.candidates=self.root/'candidates';collect_local(inventory(load_source()),self.original,self.candidates)
        self.runtime=self.root/'runtime';self.runtime.mkdir();self.library=self.runtime/'media';self.library.mkdir();self.database=self.runtime/'platform.sqlite3'
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE media_assets(id TEXT PRIMARY KEY,title TEXT,filename TEXT,kind TEXT,published INTEGER)');import_bank(db,load_source())
    def tearDown(self):self.temp.cleanup()
    def run_import(self,apply=False):return import_recovered_images(self.database,self.candidates,self.library,apply)
    def test_dry_run_private_draft_import_idempotency_and_preserved_staff_map(self):
        self.assertEqual(self.run_import()['new_draft_images'],2);self.assertEqual(list(self.library.iterdir()),[])
        with sqlite3.connect(self.database) as db:db.execute("INSERT INTO firebase_eps_media_map VALUES ('images/q0001.png','manual-choice',4)")
        report=self.run_import(True);self.assertEqual(report['new_mappings'],1);self.assertEqual(report['preserved_existing_mappings'],1)
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("SELECT asset,revision FROM firebase_eps_media_map WHERE path='images/q0001.png'").fetchone(),('manual-choice',4))
            self.assertEqual(db.execute('SELECT sum(published) FROM media_assets').fetchone()[0],0)
            db.execute("UPDATE media_assets SET title='Staff edit',published=1")
            filenames=[r[0] for r in db.execute('SELECT filename FROM media_assets')]
        for name in filenames:
            self.assertEqual((self.library/name).stat().st_mode&0o777,0o600)
            with Image.open(self.library/name) as image:self.assertEqual(image.format,'JPEG')
        repeat=self.run_import(True);self.assertEqual(repeat['already_imported'],2);self.assertEqual(repeat['new_draft_images'],0)
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute("SELECT count(*) FROM media_assets WHERE title='Staff edit' AND published=1").fetchone()[0],2)
    def test_tampered_receipt_is_rejected_before_any_output(self):
        receipt=self.candidates/'receipt.json';rows=json.loads(receipt.read_text())
        next(row for row in rows if row.get('path')=='images/q0002.png')['sha256']='0'*64
        receipt.write_text(json.dumps(rows))
        with self.assertRaises(ValueError):self.run_import(True)
        self.assertEqual(list(self.library.iterdir()),[])
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM media_assets').fetchone()[0],0)
    def test_database_failure_rolls_back_rows_and_removes_only_new_files(self):
        marker=self.library/'keep.txt';marker.write_text('existing private file')
        with sqlite3.connect(self.database) as db:db.execute("CREATE TRIGGER synthetic_failure BEFORE INSERT ON media_assets WHEN NEW.title LIKE '%q0002.png' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.original/'images').iterdir()}
        with self.assertRaises(sqlite3.IntegrityError):self.run_import(True)
        self.assertEqual([p.name for p in self.library.iterdir()],['keep.txt'])
        with sqlite3.connect(self.database) as db:self.assertEqual(db.execute('SELECT count(*) FROM media_assets').fetchone()[0],0)
        self.assertEqual(originals,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.original/'images').iterdir()})
