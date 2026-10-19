import copy
import json
import os
import secrets
import sqlite3
import tempfile
import unittest
from firebase_learning_migration import apply_learning,course_entitled
from firebase_runtime_candidate import build_candidate
from test_platform import legacy

class FirebaseLearningMigrationTests(unittest.TestCase):
    def payload(self):
        return dict(project='korean-lao-exam',collections={
            'thana_users':[dict(id='synthetic-uid',data=dict(username='migrated_user',role='student',approved=True,paid=True,epsPaid=True,seasonalPaid=False))],
            'thana_progress':[dict(id='passed',data=dict(uid='synthetic-uid',lessonId='lesson-1',score=9,total=10,passed=True,completedAt='2026-10-01T10:20:30Z')),dict(id='not-passed',data=dict(uid='synthetic-uid',lessonId='lesson-2',score=9,total=10,passed=False,completedAt='2026-10-01T10:20:30Z')),dict(id='orphan',data=dict(uid='unknown',lessonId='lesson-3',score=10,total=10,passed=True,completedAt='2026-10-01T10:20:30Z')),dict(id='eps',data=dict(uid='synthetic-uid',correct={'L401':True},attempted={'L401':True}))]})
    def test_progress_semantics_scope_isolation_disabled_bindings_and_idempotency(self):
        payload=self.payload()
        payload['collections']['thana_users'].append(dict(id='deleted-uid',data=dict(username='deleted_user',role='student',approved=True,deletedAt='synthetic')))
        payload['collections']['thana_progress'].append(dict(id='deleted-owner-result',data=dict(uid='deleted-uid',correct={'L401':True})))
        with tempfile.TemporaryDirectory() as temp:
            dest=os.path.join(temp,'runtime');report=build_candidate(payload,dest)
            self.assertEqual(report['active_progress'],1)
            self.assertEqual(report['learning_import']['eps_question_rows_added'],1)
            with sqlite3.connect(os.path.join(dest,'platform.sqlite3')) as db:
                row=db.execute('SELECT owner,lesson,score,completed FROM course_progress').fetchone()
                self.assertEqual(row[:3],('migrated_user','lesson-1',90));self.assertGreater(row[3],0)
                self.assertFalse(course_entitled(db,'migrated_user','firebase-thana-lessons-v1'))
                db.execute('UPDATE firebase_account_bindings SET enabled=1')
                self.assertTrue(course_entitled(db,'migrated_user','firebase-thana-lessons-v1'))
                self.assertFalse(course_entitled(db,'migrated_user','firebase-thana-seasonal-v1'))
                self.assertFalse(course_entitled(db,'migrated_user','unrelated-course'))
                self.assertEqual(db.execute("SELECT correct,attempted,free_used FROM firebase_eps_question_progress WHERE owner='migrated_user' AND qid='L401'").fetchone(),(1,1,0))
                second=apply_learning(db,payload);self.assertEqual(second['lesson_completions_added'],0);self.assertEqual(second['already_recorded'],5)
                self.assertEqual(db.execute("SELECT status FROM firebase_progress_imports WHERE document='deleted-owner-result'").fetchone()[0],'inactive-source-owner')
                changed=copy.deepcopy(payload);changed['collections']['thana_progress'][0]['data']['score']=10
                with self.assertRaises(ValueError):apply_learning(db,changed)
                self.assertEqual(db.execute('SELECT score FROM course_progress').fetchone()[0],90)
    def test_scoped_permission_is_enforced_by_actual_lesson_endpoint(self):
        name='scope_'+secrets.token_hex(4);uid='uid_'+secrets.token_hex(4);course='firebase-thana-lessons-v1';lesson='scope-lesson-'+secrets.token_hex(4)
        legacy.users[name]=dict(username=name,name='Synthetic',role='student',status='approved');legacy._save(legacy.USERS_FILE,legacy.users)
        try:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',(course,'Synthetic','ko','lo',''))
                content=json.dumps(dict(title='Synthetic',blocks=[],quiz=[]))
                db.execute('INSERT INTO course_lessons VALUES (?,?,?,?,?,?)',(lesson,course,content,content,1,0))
                db.execute('INSERT OR IGNORE INTO premium_courses VALUES (?)',(course,))
                db.execute('INSERT INTO firebase_account_bindings VALUES (?,?,0)',(uid,name))
                db.execute('INSERT INTO firebase_scope_entitlements VALUES (?,?,1)',(uid,'general'))
            client=legacy.app.test_client()
            with client.session_transaction() as s:s['username']=name
            self.assertEqual(client.get('/api/platform/lessons/'+lesson).status_code,403)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('UPDATE firebase_account_bindings SET enabled=1 WHERE uid=?',(uid,))
            self.assertEqual(client.get('/api/platform/lessons/'+lesson).status_code,200)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('UPDATE firebase_scope_entitlements SET granted=0 WHERE uid=?',(uid,))
            self.assertEqual(client.get('/api/platform/lessons/'+lesson).status_code,403)
        finally:
            legacy.users.pop(name,None);legacy._save(legacy.USERS_FILE,legacy.users)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('DELETE FROM firebase_scope_entitlements WHERE uid=?',(uid,));db.execute('DELETE FROM firebase_account_bindings WHERE uid=?',(uid,));db.execute('DELETE FROM course_lessons WHERE id=?',(lesson,));db.execute('DELETE FROM premium_courses WHERE course=?',(course,));db.execute('DELETE FROM courses WHERE id=?',(course,))
