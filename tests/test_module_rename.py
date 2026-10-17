import json
import os
import sqlite3
import unittest
import test_course_metadata as metadata_fixture
from test_platform import legacy


class ModuleRenameTests(unittest.TestCase):
    setUp = metadata_fixture.CourseMetadataTests.setUp
    tearDown = metadata_fixture.CourseMetadataTests.tearDown
    post = metadata_fixture.CourseMetadataTests.post

    def rename(self, **updates):
        body = dict(source='Unit', target='새 단원', lessons=[dict(id=self.lid, revision=2)])
        body.update(updates)
        return self.post('/api/platform/admin/courses/'+self.cid+'/rename-module', body)

    def snapshot(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            return c.execute('SELECT draft,published,revision FROM course_lessons WHERE id=?',(self.lid,)).fetchone()

    def test_atomic_draft_rename_preserves_public_and_history(self):
        original = self.snapshot()
        self.assertEqual(self.rename().json, dict(ok=True, changed=1))
        draft,published,revision = self.snapshot()
        self.assertEqual(json.loads(draft)['module'], '새 단원')
        self.assertEqual((published, revision), (original[1], 3))
        self.assertEqual(json.loads(published)['module'], 'Unit')
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            history=c.execute('SELECT content,actor FROM lesson_revisions WHERE lesson=? AND revision=3',(self.lid,)).fetchone()
            self.assertEqual((history[0],history[1]), (draft,self.name))
            audit=c.execute("SELECT target FROM audit_log WHERE actor=? AND action='rename_course_module'",(self.name,)).fetchone()
            self.assertEqual(json.loads(audit[0]),dict(cid=self.cid))
        self.assertEqual(self.rename().status_code,409)
        self.assertEqual(self.rename(source='새 단원',lessons=[dict(id=self.lid,revision=3)]).json['changed'],0)

    def test_concurrent_addition_and_invalid_input_leave_all_drafts_unchanged(self):
        extra = self.post('/api/platform/admin/courses/'+self.cid+'/lessons',self.content).json['id']
        try:
            before=self.snapshot()
            self.assertEqual(self.rename().status_code,409)
            for changes in [dict(target=' '),dict(target='x'*201),dict(lessons=[]),dict(lessons=[dict(id=self.lid,revision=True)]),dict(lessons=[dict(id=self.lid,revision=2)]*2)]:
                self.assertEqual(self.rename(**changes).status_code,400)
            self.assertEqual(self.snapshot(),before)
            body=[dict(id=self.lid,revision=2),dict(id=extra,revision=1)]
            self.assertEqual(self.rename(lessons=body).json['changed'],2)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
                self.assertEqual(json.loads(c.execute('SELECT draft FROM course_lessons WHERE id=?',(extra,)).fetchone()[0])['module'],'새 단원')
        finally:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
                c.execute('DELETE FROM course_lessons WHERE id=?',(extra,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(extra,))

    def test_current_scope_role_and_csrf(self):
        path='/api/platform/admin/courses/'+self.cid+'/rename-module'
        self.assertEqual(self.c.post(path,json={}).status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_scopes VALUES (?,1)',(self.name,))
        self.assertEqual(self.rename().status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_assignments VALUES (?,?)',(self.name,self.cid))
        self.assertEqual(self.rename().status_code,200)
        legacy.users[self.name]['status']='pending';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.rename().status_code,403)
