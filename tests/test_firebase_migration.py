import copy
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from firebase_migration import inspect_transfer,stage_transfer

class FirebaseMigrationTests(unittest.TestCase):
    def payload(self):
        return {'project':'korean-lao-exam','collections':{
            'thana_users':[{'id':'uid_with_underscore','data':{'username':'synthetic','name':'ທົດລອງ','role':'student','approved':True,'epsPaid':True}}],
            'thana_progress':[
                {'id':'uid_with_underscore_L1','data':{'uid':'uid_with_underscore','lessonId':'L1','score':3,'total':4,'passed':True}},
                {'id':'uid_with_underscore_eps','data':{'uid':'uid_with_underscore','correct':{'original_q':True},'attempted':{'original_q':True},'freeUsed':{}}},
                {'id':'uid_with_underscore_missed','data':{'uid':'uid_with_underscore','words':{'original_word':2}}}],
            'thana_lesson_meta':[{'id':'L1','data':{'title':'Owner title','unknownField':{'preserve':True}}}]}}

    def test_staging_preserves_all_ids_fields_and_does_not_enable_accounts(self):
        payload=self.payload();before=copy.deepcopy(payload)
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'transfer.sqlite3';report=stage_transfer(payload,target)
            self.assertEqual(payload,before);self.assertEqual(report['records'],5)
            self.assertEqual(report['progress_kinds'],{'lesson':1,'eps':1,'missed_words':1})
            self.assertEqual(report['progress_without_known_profile'],0)
            self.assertEqual(os.stat(target).st_mode&0o777,0o600)
            with sqlite3.connect(target) as db:
                for collection,documents in payload['collections'].items():
                    for doc in documents:
                        data=db.execute('SELECT data FROM firebase_source_records WHERE collection=? AND document_id=?',(collection,doc['id'])).fetchone()[0]
                        self.assertEqual(json.loads(data),doc['data'])
                self.assertEqual({r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")},{'firebase_source_records','firebase_transfer_metadata'})
                self.assertEqual(db.execute('SELECT status FROM firebase_transfer_metadata').fetchone()[0],'staged-not-applied')
            with self.assertRaises(FileExistsError):stage_transfer(payload,target)

    def test_rejects_wrong_project_duplicate_ids_config_and_source_destination(self):
        for mutate in [lambda p:p.update(project='other'),lambda p:p['collections'].update(adminConfig=[]),lambda p:p['collections']['thana_users'].append(p['collections']['thana_users'][0]),lambda p:p['collections']['thana_users'][0].update(id='../unsafe'),lambda p:p['collections']['thana_users'][0].update(data=[]),lambda p:p['collections']['thana_users'][0]['data'].update(score=float('nan'))]:
            p=self.payload();mutate(p)
            with self.assertRaises(ValueError):inspect_transfer(p)
        with self.assertRaises(ValueError):stage_transfer(self.payload(),Path(__file__).resolve().parents[1]/'forbidden-migration.sqlite3')

    def test_reports_unresolved_progress_and_roles_without_silently_dropping(self):
        p=self.payload();p['collections']['thana_progress'][0]['data']['uid']='missing'
        p['collections']['thana_users'][0]['data']['role']='owner'
        records,report=inspect_transfer(p)
        self.assertEqual(len(records),5);self.assertEqual(report['progress_without_known_profile'],1)
        self.assertEqual(report['profiles_with_unknown_role'],1)
        encoded=json.dumps(report)
        self.assertNotIn('uid_with_underscore',encoded);self.assertNotIn('synthetic',encoded)
        self.assertNotIn('ທົດລອງ',encoded)
        records,report=inspect_transfer({'project':'korean-lao-exam','collections':{'thana_grammar_overrides':[{'id':'original-grammar-id','data':{'text':'Synthetic revised grammar'}}]}})
        self.assertEqual(len(records),1)
        self.assertEqual(report['collections']['thana_grammar_overrides'],1)
