import json
import os
import secrets
import sqlite3
import unittest
from test_platform import legacy
from audit_routes import CONTENT_ACTIONS


class ContentAuditTests(unittest.TestCase):
    def setUp(self):
        self.name='audit_'+secrets.token_hex(5)
        self.c=legacy.app.test_client()
        legacy.users[self.name]={'username':self.name,'name':'Synthetic auditor','role':'admin','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=self.name
        self.courses=[]

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
            for cid in self.courses:c.execute('DELETE FROM courses WHERE id=?',(cid,))
        legacy.users.pop(self.name,None)
        legacy._save(legacy.USERS_FILE,legacy.users)

    def post(self,path,body):
        token=self.c.get('/api/csrf').json['token']
        return self.c.post(path,json=body,headers={'X-CSRF-Token':token})

    def events(self):
        return self.c.get('/api/platform/admin/audit?q='+self.name).json['events']

    def test_mutation_metadata_not_payload_or_preview(self):
        marker='private-text-never-log-'+secrets.token_hex(5)
        response=self.post('/api/platform/admin/courses',{'title':marker,'language':'ko','description':marker})
        self.assertEqual(response.status_code,201)
        cid=response.json['id'];self.courses.append(cid)
        events=self.events();self.assertEqual(len(events),1)
        self.assertEqual(events[0]['action'],'create_course')
        self.assertEqual(json.loads(events[0]['target']),{'id':cid})
        self.assertNotIn(marker,json.dumps(events))
        self.assertEqual(self.post('/api/platform/admin/courses',{'title':''}).status_code,400)
        self.assertEqual(self.post('/api/platform/admin/vocabulary/import',{'csv':'ko,lo\n'+marker+',fixture','commit':False}).status_code,200)
        self.assertEqual(len(self.events()),1)
        self.assertEqual(self.c.get('/api/platform/admin/courses').status_code,200)
        self.assertEqual(len(self.events()),1)

    def test_teacher_mutation_logged_but_only_admin_reads(self):
        legacy.users[self.name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
        r=self.post('/api/platform/admin/courses',{'title':'Synthetic teacher course','language':'lo'})
        self.assertEqual(r.status_code,201);self.courses.append(r.json['id'])
        self.assertEqual(self.c.get('/api/platform/admin/audit').status_code,403)
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post('/api/platform/admin/courses',{'title':'Forbidden','language':'lo'}).status_code,403)
        self.assertEqual(self.c.get('/api/platform/admin/audit').status_code,403)
        legacy.users[self.name]['role']='admin';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(len(self.events()),1)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.c.get('/api/platform/admin/audit').status_code,403)

    def test_literal_search_pagination_and_endpoint_coverage(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.executemany('INSERT INTO audit_log(actor,action,target,created) VALUES (?,?,?,?)',[(self.name,'synthetic','%',1)]*101)
        r=self.c.get('/api/platform/admin/audit?q='+self.name)
        self.assertEqual(r.headers['Cache-Control'],'no-store')
        self.assertEqual((r.json['total'],len(r.json['events'])),(101,100))
        page=self.c.get('/api/platform/admin/audit?q='+self.name+'&page=2').json
        self.assertEqual(len(page['events']),1)
        self.assertGreater(r.json['events'][0]['id'],page['events'][0]['id'])
        self.assertEqual(self.c.get('/api/platform/admin/audit?q='+self.name+'%25').json['total'],0)
        for value in ('0','-1','x','100001'):
            self.assertEqual(self.c.get('/api/platform/admin/audit?page='+value).status_code,400)
        self.assertTrue(CONTENT_ACTIONS<=set(legacy.app.view_functions))
        excluded={'account_save','change_password','issue_recovery','recover_account','payment_request','speech_recognize'}
        self.assertFalse(CONTENT_ACTIONS&excluded)
