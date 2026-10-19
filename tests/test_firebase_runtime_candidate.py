import copy
import json
import os
import subprocess
import sys
from pathlib import Path
import sqlite3
import tempfile
import unittest
from firebase_runtime_candidate import build_candidate
from legacy_storage import LegacyStorage

class FirebaseRuntimeCandidateTests(unittest.TestCase):
    def payload(self):
        return dict(project='korean-lao-exam',collections={
            'thana_users':[dict(id='uid_kept',data=dict(username='kept.user',name='Synthetic learner',role='admin',approved=True,epsPaid=True)),dict(id='uid_deleted',data=dict(username='deleted_user',role='student',approved=True,deletedAt='synthetic-timestamp'))],
            'thana_progress':[dict(id='unmatched',data=dict(uid='unknown',words={'synthetic':1}))]})
    def test_runtime_store_reads_original_identity_without_password_or_enabled_binding(self):
        payload=self.payload();original=copy.deepcopy(payload)
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'candidate';report=build_candidate(payload,dest)
            self.assertEqual(payload,original);self.assertEqual(report['profiles'],1);self.assertEqual(report['drafts'],81)
            self.assertEqual(report['deleted_profiles_not_activated'],1);self.assertEqual(report['unresolved_progress_owners'],1)
            users=LegacyStorage(str(dest)).load(str(dest/'users.json'),{})
            self.assertEqual(set(users),{'kept.user'});self.assertIsNone(users['kept.user']['pw'])
            self.assertEqual(users['kept.user']['firebase_uid'],'uid_kept');self.assertEqual(users['kept.user']['role'],'admin')
            with sqlite3.connect(dest/'platform.sqlite3') as db:
                self.assertEqual(db.execute('SELECT * FROM firebase_account_bindings').fetchall(),[('uid_kept','kept.user',0)])
                self.assertEqual(db.execute('SELECT count(*) FROM firebase_source_records').fetchone()[0],3)
                self.assertEqual(db.execute('SELECT count(*) FROM course_lessons WHERE published IS NOT NULL').fetchone()[0],0)
            self.assertEqual((dest/'legacy.sqlite3').stat().st_mode&0o777,0o600)
            env=dict(os.environ,THANA_DATA_DIR=str(dest),THANA_PLATFORM_DB=str(dest/'platform.sqlite3'),THANA_ENV='development',THANA_FIREBASE_AUTH_ENABLED='0')
            code="import app; c=app.app.test_client(); assert c.get('/health').status_code==200; token=c.get('/api/csrf').json['token']; r=c.post('/api/login',json={'username':'kept.user','password':'not-a-real-password'},headers={'X-CSRF-Token':token}); assert r.status_code==401; assert len(app.users)==1"
            subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=env,check=True,capture_output=True,text=True,timeout=30)
            self.assertFalse((dest/'bootstrap_credentials.txt').exists())
            with self.assertRaises(FileExistsError):build_candidate(payload,dest)
    def test_collision_and_ambiguous_roles_reject_before_output(self):
        for mutation in ('collision','role'):
            payload=self.payload()
            if mutation=='collision':payload['collections']['thana_users'][1]['data'].update(username='KEPT.USER',deletedAt=None)
            else:payload['collections']['thana_users'][0]['data']['role']='owner'
            with tempfile.TemporaryDirectory() as temp:
                dest=Path(temp)/'candidate'
                with self.assertRaises(ValueError):build_candidate(payload,dest)
                self.assertFalse(dest.exists())
