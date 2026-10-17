import json
import os
import secrets
import sqlite3
import unittest
from test_platform import legacy


class QuizPreviewTests(unittest.TestCase):
    def setUp(self):
        self.name='preview_'+secrets.token_hex(4)
        legacy.users[self.name]=dict(username=self.name,name='Synthetic preview teacher',role='teacher',status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as session:session['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',dict(title='Preview course',language='lo')).json['id']
        self.path='/api/platform/admin/courses/'+self.cid+'/preview-grade'
        self.content=dict(title='Unsaved quiz rehearsal',blocks=[dict(type='text',value='Synthetic')],quiz=[
            dict(type='choice',question='Choice',options=['A','B'],answer=1,explanation='B explanation',source='Synthetic source'),
            dict(type='blank',question='Blank',accepted=['ປຶ້ມ'],explanation='Synthetic'),
            dict(type='matching',question='Match',pairs=[dict(left='one',right='1'),dict(left='two',right='2')]),
            dict(type='ordering',question='Order',options=['second','first'],answer=[1,0])])
        self.answers={'0':1,'1':'ປຶ້ມ','2':['1','2'],'3':[1,0]}

    def post(self,path,body):
        return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def preview(self,**changes):
        return self.post(self.path,dict(content=self.content,answers=self.answers,**changes))

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('DELETE FROM courses WHERE id=?',(self.cid,))
            c.execute('DELETE FROM teacher_course_scopes WHERE username=?',(self.name,))
            c.execute('DELETE FROM teacher_course_assignments WHERE username=?',(self.name,))
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_all_types_score_without_writing_lessons_history_or_progress(self):
        tables=['course_lessons','lesson_revisions','course_progress','lesson_visits','audit_log']
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:before={t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
        response=self.preview()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['score'],100);self.assertTrue(response.json['preview']);self.assertFalse(response.json['saved'])
        self.assertEqual(response.json['detail'][0]['source'],'Synthetic source')
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        wrong=self.post(self.path,dict(content=self.content,answers={}))
        self.assertEqual(wrong.json['score'],0)
        self.assertEqual(len(wrong.json['detail']),4)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:self.assertEqual(before,{t:c.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables})
        self.assertEqual(self.c.get('/api/platform/learning-progress').json['xp'],0)

    def test_scope_current_role_missing_course_and_csrf(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO teacher_course_scopes VALUES (?,1)',(self.name,))
        self.assertEqual(self.preview().status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO teacher_course_assignments VALUES (?,?)',(self.name,self.cid))
        self.assertEqual(self.preview().status_code,200)
        self.assertEqual(self.c.post(self.path,json=dict(content=self.content,answers=self.answers)).status_code,403)
        self.assertEqual(self.post('/api/platform/admin/courses/missing/preview-grade',dict(content=self.content,answers={})).status_code,404)
        for role,status in [('student','approved'),('teacher','pending')]:
            legacy.users[self.name].update(role=role,status=status);legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.preview().status_code,403)
        with self.c.session_transaction() as session:session.clear()
        self.assertEqual(self.preview().status_code,403)

    def test_bad_answers_content_and_unknown_fields_rejected(self):
        body=dict(content=self.content,answers=self.answers)
        for bad in [[],{},dict(body,answers=[]),dict(body,content={}),dict(body,action='publish'),dict(body,answers={'99':0}),dict(body,answers={'0':True}),dict(body,answers={'1':3}),dict(body,answers={'2':['invalid','2']}),dict(body,answers={'3':[0,0]})]:
            self.assertEqual(self.post(self.path,bad).status_code,400,repr(bad)[:100])
