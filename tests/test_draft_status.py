import json
import os
import sqlite3
import unittest
import test_course_metadata as metadata_fixture


class DraftStatusTests(unittest.TestCase):
    setUp = metadata_fixture.CourseMetadataTests.setUp
    tearDown = metadata_fixture.CourseMetadataTests.tearDown
    post = metadata_fixture.CourseMetadataTests.post

    def row(self):
        return next(l for l in self.c.get('/api/platform/admin/courses').json['lessons'] if l['id']==self.lid)

    def save(self, content, action):
        return self.post('/api/platform/admin/lessons/'+self.lid, dict(content=content,revision=self.row()['revision'],action=action))

    def test_publish_edit_revert_and_unpublish_state(self):
        self.assertFalse(self.row()['draft_changed'])
        edited=dict(self.content,title='Changed title')
        saved=self.save(edited,'save').json
        self.assertTrue(saved['draft_changed']);self.assertTrue(saved['published'])
        self.assertTrue(self.row()['draft_changed'])
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(json.loads(c.execute('SELECT published FROM course_lessons WHERE id=?',(self.lid,)).fetchone()[0]),self.content)
        self.assertFalse(self.save(self.content,'save').json['draft_changed'])
        self.assertTrue(self.save(edited,'save').json['draft_changed'])
        self.assertFalse(self.save(edited,'publish').json['draft_changed'])
        unpublished=self.save(edited,'unpublish').json
        self.assertFalse(unpublished['published']);self.assertFalse(unpublished['draft_changed'])
        self.assertFalse(self.row()['draft_changed'])

    def test_semantic_comparison_and_bulk_rename_status(self):
        # Formatting/key ordering from older imports must not create false alerts.
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('UPDATE course_lessons SET draft=? WHERE id=?',(json.dumps(self.content,sort_keys=True,indent=2),self.lid))
        self.assertFalse(self.row()['draft_changed'])
        self.assertEqual(self.post('/api/platform/admin/courses/'+self.cid+'/rename-module',dict(source='Unit',target='Renamed',lessons=[dict(id=self.lid,revision=2)])).status_code,200)
        self.assertTrue(self.row()['draft_changed'])
        # Publishing the current draft clears the queue without changing lesson IDs.
        self.save(self.row()['draft'],'publish')
        self.assertFalse(self.row()['draft_changed'])
