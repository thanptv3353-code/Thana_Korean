import json
import os
import secrets
import sqlite3
import unittest
from test_platform import legacy


class CourseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.name = 'metadata_' + secrets.token_hex(4)
        legacy.users[self.name] = dict(username=self.name, name='Synthetic teacher', role='teacher', status='approved')
        legacy._save(legacy.USERS_FILE, legacy.users)
        self.c = legacy.app.test_client()
        with self.c.session_transaction() as session:
            session['username'] = self.name
        self.cid = self.post('/api/platform/admin/courses', dict(title='Original', language='lo')).json['id']
        self.path = '/api/platform/admin/courses/' + self.cid + '/metadata'
        self.body = dict(title='  Updated <title>  ', description='설명\nຄຳອະທິບາຍ', revision=0)
        self.content = dict(title='Lesson', module='Unit', blocks=[dict(type='text', value='Synthetic')], quiz=[])
        self.lid = self.post('/api/platform/admin/courses/' + self.cid + '/lessons', self.content).json['id']
        self.post('/api/platform/admin/lessons/' + self.lid, dict(content=self.content, revision=1, action='publish'))

    def post(self, path, body):
        return self.c.post(path, json=body, headers={'X-CSRF-Token': self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for table, key, value in [('courses','id',self.cid),('course_metadata_revisions','course',self.cid),('course_lessons','id',self.lid),('lesson_revisions','lesson',self.lid),('teacher_course_scopes','username',self.name),('teacher_course_assignments','username',self.name),('audit_log','actor',self.name)]:
                c.execute('DELETE FROM '+table+' WHERE '+key+'=?', (value,))
        legacy.users.pop(self.name, None)
        legacy._save(legacy.USERS_FILE, legacy.users)

    def metadata(self):
        return next(c for c in self.c.get('/api/platform/admin/courses').json['courses'] if c['id'] == self.cid)

    def test_revision_public_update_and_preserved_curriculum(self):
        self.assertEqual(self.metadata()['metadata_revision'], 0)
        self.assertEqual(self.post(self.path, self.body).json['revision'], 1)
        self.assertEqual(self.post(self.path, self.body).status_code, 409)
        course = next(c for c in self.c.get('/api/platform/courses').json['courses'] if c['id'] == self.cid)
        self.assertEqual(course['title'], 'Updated <title>')
        self.assertEqual(course['description'], self.body['description'])
        self.assertEqual((course['language'], course['instruction']), ('lo', 'ko'))
        self.assertEqual(course['lessons'][0]['id'], self.lid)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            row = c.execute('SELECT draft,published,revision FROM course_lessons WHERE id=?', (self.lid,)).fetchone()
            self.assertEqual(json.loads(row[0]), self.content)
            self.assertEqual(json.loads(row[1]), self.content)
            self.assertEqual(row[2], 2)
            audit = c.execute("SELECT target FROM audit_log WHERE actor=? AND action='course_metadata_save'", (self.name,)).fetchone()
            self.assertEqual(json.loads(audit[0]), {'cid':self.cid})

    def test_scope_current_role_csrf_and_missing_course(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_scopes VALUES (?,1)', (self.name,))
        self.assertEqual(self.post(self.path, self.body).status_code, 403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_assignments VALUES (?,?)', (self.name,self.cid))
        self.assertEqual(self.c.post(self.path, json=self.body).status_code, 403)
        self.assertEqual(self.post(self.path, self.body).status_code, 200)
        self.assertEqual(self.post('/api/platform/admin/courses/missing/metadata', self.body).status_code, 404)
        for role, status in [('student','approved'),('teacher','pending')]:
            legacy.users[self.name].update(role=role, status=status)
            legacy._save(legacy.USERS_FILE, legacy.users)
            self.assertEqual(self.post(self.path, dict(self.body, revision=1)).status_code, 403)
        with self.c.session_transaction() as session:
            session.clear()
        self.assertEqual(self.post(self.path, self.body).status_code, 403)

    def test_strict_validation_and_no_partial_writes(self):
        for bad in [[], {}, dict(self.body,title='  '), dict(self.body,title=123),dict(self.body,title='x'*201),dict(self.body,description=None),dict(self.body,description='x'*10001),dict(self.body,revision=True),dict(self.body,revision=-1),dict(self.body,revision='0'),dict(self.body,language='ko')]:
            self.assertEqual(self.post(self.path,bad).status_code,400,repr(bad)[:100])
        self.assertEqual(self.metadata()['title'], 'Original')
        self.assertEqual(self.metadata()['metadata_revision'], 0)
