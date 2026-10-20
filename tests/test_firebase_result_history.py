import copy
import json
import os
import secrets
import sqlite3
import unittest
from firebase_result_history import initialize,import_results,COLLECTION
from test_platform import legacy


class OriginalResultTests(unittest.TestCase):
    def payload(self):
        return dict(collections={'thana_users':[dict(id='uid',data=dict(username='synthetic'))],
                                COLLECTION:[dict(id='original-id',data=dict(uid='uid',groupId='original-group',score=7,total=10,pct=70,passed=True,submittedAt='2026-10-01T10:00:00Z'))]})

    def database(self):
        db=sqlite3.connect(':memory:');self.addCleanup(db.close)
        db.execute('CREATE TABLE firebase_account_bindings(uid TEXT,username TEXT,enabled INTEGER)')
        db.execute("INSERT INTO firebase_account_bindings VALUES ('uid','synthetic',0)")
        return db

    def test_original_identity_score_date_and_idempotency_without_new_attempt(self):
        db=self.database();payload=self.payload();original=copy.deepcopy(payload)
        self.assertEqual(import_results(db,payload)['added'],1)
        self.assertEqual(import_results(db,payload)['added'],0)
        self.assertEqual(payload,original)
        row=db.execute('SELECT document,uid,score,total,pct,passed,submitted FROM firebase_original_results').fetchone()
        self.assertEqual(row[:6],('original-id','uid',7,10,70,1));self.assertGreater(row[6],0)
        self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='mock_attempts'").fetchone())
        changed=copy.deepcopy(payload);changed['collections'][COLLECTION][0]['data']['score']=8
        with self.assertRaises(ValueError):import_results(db,changed)
        self.assertEqual(db.execute('SELECT score FROM firebase_original_results').fetchone()[0],7)

    def test_unknown_deleted_and_wrong_binding_do_not_guess_ownership(self):
        for kind in ('unknown','deleted','wrong_binding'):
            db=self.database();payload=self.payload()
            if kind=='unknown':payload['collections'][COLLECTION][0]['data']['uid']='unknown'
            if kind=='deleted':payload['collections']['thana_users'][0]['data']['deletedAt']='synthetic'
            if kind=='wrong_binding':db.execute("UPDATE firebase_account_bindings SET username='other'")
            self.assertEqual(import_results(db,payload)['added'],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM firebase_result_imports').fetchone()[0],1)

    def test_inconsistent_score_pass_and_timestamp_are_source_only(self):
        for change in ({'score':True},{'score':11},{'total':0},{'pct':71},{'passed':False},
                       {'submittedAt':'2026-10-01T10:00:00'},{'submittedAt':None},{'groupId':''}):
            db=self.database();payload=self.payload();payload['collections'][COLLECTION][0]['data'].update(change)
            report=import_results(db,payload)
            self.assertEqual(report['statuses'],{'invalid-source-result':1})
            self.assertEqual(db.execute('SELECT COUNT(*) FROM firebase_original_results').fetchone()[0],0)

    def test_old_eps_collection_is_not_linked_by_similar_username(self):
        db=self.database();payload=self.payload();payload['collections']['examResults']=payload['collections'].pop(COLLECTION)
        self.assertEqual(import_results(db,payload)['added'],0)

    def test_http_owner_binding_approval_pagination_and_no_raw_data(self):
        name='hist_'+secrets.token_hex(5);uid='uid_'+secrets.token_hex(5);doc='result_'+secrets.token_hex(5)
        legacy.users[name]=dict(username=name,name='Synthetic',role='student',status='approved',firebase_uid=uid)
        legacy._save(legacy.USERS_FILE,legacy.users)
        client=legacy.app.test_client()
        with client.session_transaction() as session:session.update(username=name,role='student')
        try:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('INSERT INTO firebase_account_bindings VALUES (?,?,0)',(uid,name))
                db.execute('INSERT INTO firebase_original_results VALUES (?,?,?,?,?,?,?,?,?)',(COLLECTION,doc,uid,'group',7,10,70,1,1000))
            self.assertEqual(client.get('/api/platform/original-history').json['total'],0)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('UPDATE firebase_account_bindings SET enabled=1 WHERE uid=?',(uid,))
            response=client.get('/api/platform/original-history?limit=1')
            self.assertEqual(response.json['results'][0]['id'],doc);self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertNotIn(uid,response.text);self.assertNotIn('source',response.json['results'][0])
            self.assertEqual(client.get('/api/platform/original-history?offset=1').json['results'],[])
            for query in ('limit=0','limit=101','offset=-1','offset=bad'):
                self.assertEqual(client.get('/api/platform/original-history?'+query).status_code,400)
            self.assertEqual(legacy.app.test_client().get('/api/platform/original-history').status_code,401)
            legacy.users[name]['firebase_uid']='other';legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(client.get('/api/platform/original-history').json['total'],0)
            legacy.users[name]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(client.get('/api/platform/original-history').status_code,401)
        finally:
            legacy.users.pop(name,None);legacy._save(legacy.USERS_FILE,legacy.users)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('DELETE FROM firebase_account_bindings WHERE uid=?',(uid,))
                db.execute('DELETE FROM firebase_original_results WHERE document=?',(doc,))
