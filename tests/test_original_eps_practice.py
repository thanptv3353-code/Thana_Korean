import json
import os
import secrets
import sqlite3
import unittest
from test_platform import legacy
from firebase_curriculum import load_source
from firebase_eps_bank import import_bank

class OriginalEpsPracticeTests(unittest.TestCase):
    def setUp(self):
        self.prefix='original_'+secrets.token_hex(4);self.learner=self.prefix+'_student';self.staff=self.prefix+'_admin';self.other=self.prefix+'_other'
        for name,role in ((self.learner,'student'),(self.staff,'admin'),(self.other,'student')):legacy.users[name]=dict(username=name,name='Synthetic',role=role,status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users);self.admin=self.client(self.staff);self.student=self.client(self.learner)
        self.source={q['id']:q for c in load_source()['eps'] for q in c['questions']}
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('DELETE FROM firebase_eps_bank');db.execute('DELETE FROM firebase_eps_publications');db.execute('DELETE FROM firebase_eps_media_map');import_bank(db,load_source())
    def client(self,name):
        client=legacy.app.test_client()
        with client.session_transaction() as s:s['username']=name
        return client
    def post(self,client,path,body):return client.post(path,json=body,headers={'X-CSRF-Token':client.get('/api/csrf').json['token']})
    def publish(self,qid):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:revision=db.execute('SELECT revision FROM firebase_eps_bank WHERE id=?',(qid,)).fetchone()[0]
        response=self.post(self.admin,'/api/platform/admin/firebase-eps/'+qid,dict(revision=revision,answer=self.source[qid]['correct_answer_index'],explanation='Synthetic reviewed explanation',reviewed=True));self.assertEqual(response.status_code,200)
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/'+qid+'/publication',dict(revision=response.json['revision'],published=True)).status_code,200)
    def start(self):return self.post(self.student,'/api/platform/original-eps',dict(category='blank',count=1))
    def tearDown(self):
        for name in (self.learner,self.staff,self.other):legacy.users.pop(name,None)
        legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            for name in (self.learner,self.staff,self.other):
                db.execute('DELETE FROM firebase_eps_attempts WHERE owner=?',(name,));db.execute('DELETE FROM firebase_eps_question_progress WHERE owner=?',(name,))
            db.execute('DELETE FROM firebase_scope_entitlements WHERE uid=?',(self.prefix,));db.execute('DELETE FROM firebase_account_bindings WHERE uid=?',(self.prefix,))
            db.execute('DELETE FROM firebase_eps_publications');db.execute('DELETE FROM firebase_eps_media_map');db.execute('DELETE FROM firebase_eps_bank')
    def test_publication_gates_and_no_answer_leak_before_finish(self):
        self.assertEqual(self.student.get('/api/platform/original-eps').json['categories'],[])
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/201/publication',dict(revision=1,published=True)).status_code,409)
        self.publish('201');started=self.start();self.assertEqual(started.status_code,200)
        question=started.json['questions'][0];self.assertEqual(question['id'],'201');self.assertNotIn('answer',question);self.assertNotIn('explanation',question)
        aid=started.json['id'];self.assertNotIn('answer',self.student.get('/api/platform/original-eps/'+aid).json['questions'][0])
        empty=self.post(self.student,'/api/platform/original-eps/'+aid,dict(answers={}));self.assertEqual(empty.status_code,200);self.assertNotIn('answer',empty.json['detail'][0])
        self.assertEqual(len(self.student.get('/api/platform/original-eps').json['categories']),1)
    def test_snapshot_grading_trial_limit_and_idempotent_finish(self):
        self.publish('201');started=self.start().json;aid=started['id']
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/201',dict(revision=2,answer=0,explanation='Changed after start',reviewed=True)).status_code,200)
        result=self.post(self.student,'/api/platform/original-eps/'+aid,dict(answers={'201':self.source['201']['correct_answer_index']}));self.assertEqual(result.json['correct'],1)
        self.assertEqual(self.post(self.student,'/api/platform/original-eps/'+aid,dict(answers={'201':0})).json,result.json)
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/201/publication',dict(revision=3,published=True)).status_code,200)
        self.assertEqual(self.start().status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('INSERT INTO firebase_account_bindings VALUES (?,?,1)',(self.prefix,self.learner));db.execute('INSERT INTO firebase_scope_entitlements VALUES (?,?,1)',(self.prefix,'general'))
        self.assertEqual(self.start().status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('INSERT INTO firebase_scope_entitlements VALUES (?,?,1)',(self.prefix,'eps'))
        self.assertEqual(self.start().status_code,200)
    def test_owner_roles_csrf_and_strict_answers(self):
        self.publish('201');aid=self.start().json['id'];other=self.client(self.other)
        self.assertEqual(other.get('/api/platform/original-eps/'+aid).status_code,404)
        self.assertEqual(self.post(other,'/api/platform/original-eps/'+aid,dict(answers={})).status_code,404)
        for answers in ({'201':True},{'201':99},{'unknown':0}):self.assertEqual(self.post(self.student,'/api/platform/original-eps/'+aid,dict(answers=answers)).status_code,400)
        self.assertEqual(self.student.post('/api/platform/original-eps/'+aid,json={'answers':{}}).status_code,403)
        self.assertEqual(self.post(self.student,'/api/platform/admin/firebase-eps/201/publication',dict(revision=2,published=False)).status_code,403)
        self.assertEqual(self.post(self.student,'/api/platform/original-eps',dict(category=[],count=1)).status_code,400)
        legacy.users[self.learner]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.student.get('/api/platform/original-eps/'+aid).status_code,401)
    def test_single_active_resume_cancel_and_media_publication_gate(self):
        self.publish('201');first=self.start().json;second=self.start().json
        self.assertEqual(first['id'],second['id']);self.assertTrue(second['resumed'])
        self.assertEqual(self.post(self.student,'/api/platform/original-eps/'+first['id']+'/cancel',{}).status_code,200)
        self.assertTrue(self.student.get('/api/platform/original-eps/'+first['id']).json['result']['cancelled'])
        self.assertNotEqual(self.start().json['id'],first['id'])
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/1/publication',dict(revision=1,published=True)).status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:self.assertEqual(db.execute('SELECT count(*) FROM firebase_eps_question_progress WHERE owner=?',(self.learner,)).fetchone()[0],0)
    def test_unpublishing_hides_catalog_but_does_not_rewrite_owned_snapshot(self):
        self.publish('201');aid=self.start().json['id']
        self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/201/publication',dict(revision=2,published=False)).status_code,200)
        self.assertEqual(self.student.get('/api/platform/original-eps').json['categories'],[])
        self.assertEqual(self.post(self.student,'/api/platform/original-eps/'+aid,dict(answers={'201':3})).status_code,200)
        history=self.student.get('/api/platform/original-eps').json['history'];self.assertEqual(len(history),1);self.assertEqual(history[0]['result']['answered'],1)
    def test_listening_pair_is_not_split_or_offered_half_published(self):
        asset=self.prefix+'_audio'
        try:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('INSERT INTO media_assets VALUES (?,?,?,?,1)',(asset,'Synthetic pair metadata','c'*32+'.wav','audio'))
                db.execute('INSERT INTO firebase_eps_media_map VALUES (?,?,1)',('audio/listening/q921.mp3',asset))
                db.execute("UPDATE firebase_eps_bank SET reviewed=1 WHERE id IN ('L921-1','L921-2')")
            self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/L921-1/publication',dict(revision=1,published=True)).status_code,200)
            self.assertEqual(self.student.get('/api/platform/original-eps').json['categories'],[])
            self.assertEqual(self.post(self.admin,'/api/platform/admin/firebase-eps/L921-2/publication',dict(revision=1,published=True)).status_code,200)
            started=self.post(self.student,'/api/platform/original-eps',dict(category='listen_story_pair',count=2)).json
            self.assertEqual({q['id'] for q in started['questions']},{'L921-1','L921-2'})
            result=self.post(self.student,'/api/platform/original-eps/'+started['id'],dict(answers={qid:self.source[qid]['correct_answer_index'] for qid in ('L921-1','L921-2')}))
            self.assertEqual(result.json['correct'],2)
        finally:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('DELETE FROM media_assets WHERE id=?',(asset,))
    def test_imported_original_trial_and_correct_flags_are_preserved_monotonically(self):
        from firebase_eps_practice import import_source_progress
        self.publish('201')
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            result=import_source_progress(db,self.learner,dict(correct={'201':True},attempted={'201':True},freeUsed={'201':True,'unknown-original-id':True}))
            self.assertEqual(result['added'],1);self.assertEqual(result['unknown'],1)
            import_source_progress(db,self.learner,dict(correct={'201':False},attempted={'201':False},freeUsed={'201':False}))
            self.assertEqual(db.execute('SELECT correct,attempted,free_used FROM firebase_eps_question_progress WHERE owner=?',(self.learner,)).fetchone(),(1,1,1))
            self.assertEqual(import_source_progress(db,self.learner,dict(correct={'201':1}))['status'],'invalid-eps-history')
        self.assertEqual(self.start().status_code,409)
