import json
import os
import secrets
import sqlite3
import unittest
import quiz_engine
from lao_draft_pack import COURSE_ID, lessons
from test_platform import legacy


class LaoDraftPackTests(unittest.TestCase):
    def setUp(self):
        self.name='draftpack_'+secrets.token_hex(4)
        legacy.users[self.name]=dict(username=self.name,name='Synthetic pack admin',role='admin',status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as session:session['username']=self.name
        self.path='/api/platform/admin/lao-draft-pack'

    def post(self,body=None):
        return self.c.post(self.path,json=body if body is not None else {'pack':'lao-beginner-v1'},headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for item in lessons():
                c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(item['id'],))
                c.execute('DELETE FROM course_lessons WHERE id=?',(item['id'],))
            c.execute('DELETE FROM courses WHERE id=?',(COURSE_ID,))
            c.execute('DELETE FROM course_levels WHERE course=?',(COURSE_ID,))
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_import_is_draft_only_idempotent_and_preserves_teacher_edits(self):
        before={c['id'] for c in self.c.get('/api/platform/courses').json['courses']}
        self.assertEqual(self.post().json['added'],6)
        self.assertEqual(self.post().json['added'],0)
        after={c['id'] for c in self.c.get('/api/platform/courses').json['courses']}
        self.assertEqual(before,after)
        item=lessons()[0]
        self.assertEqual(self.c.get('/api/platform/lessons/'+item['id']).status_code,404)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            rows=c.execute('SELECT id,draft,published,revision FROM course_lessons WHERE course=?',(COURSE_ID,)).fetchall()
            self.assertEqual(len(rows),6)
            for lid,draft,published,revision in rows:
                self.assertIsNone(published);self.assertEqual(revision,1)
                content=json.loads(draft);self.assertTrue(content['objectives']);self.assertIn('교사 검토',content['blocks'][0]['value'])
                self.assertTrue(all(quiz_engine.valid(q) for q in content['quiz']))
            c.execute('UPDATE course_lessons SET draft=?,published=?,revision=8 WHERE id=?',('teacher draft','teacher publication',item['id']))
            c.execute('UPDATE courses SET title=? WHERE id=?',('Teacher title',COURSE_ID))
        self.assertEqual(self.post().json['added'],0)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(c.execute('SELECT draft,published,revision FROM course_lessons WHERE id=?',(item['id'],)).fetchone(),('teacher draft','teacher publication',8))
            self.assertEqual(c.execute('SELECT title FROM courses WHERE id=?',(COURSE_ID,)).fetchone()[0],'Teacher title')

    def test_roles_validation_csrf_and_collision_rollback(self):
        self.assertEqual(self.c.post(self.path,json={'pack':'lao-beginner-v1'}).status_code,403)
        for body in [{},[],{'pack':'unknown'},{'pack':'lao-beginner-v1','publish':True}]:self.assertEqual(self.post(body).status_code,400)
        for role,status in [('student','approved'),('teacher','approved'),('admin','pending')]:
            legacy.users[self.name].update(role=role,status=status);legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.post().status_code,403)
        legacy.users[self.name].update(role='superadmin',status='approved');legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO course_lessons VALUES (?,?,?,?,?,?)',(lessons()[-1]['id'],'foreign','{}',None,1,0))
        self.assertEqual(self.post().status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM courses WHERE id=?',(COURSE_ID,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM course_lessons WHERE course=?',(COURSE_ID,)).fetchone()[0],0)
        with self.c.session_transaction() as session:session.clear()
        self.assertEqual(self.post().status_code,403)
