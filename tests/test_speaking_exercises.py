import os
import sqlite3
import time
import unittest
import test_listening as helpers
from test_platform import legacy


class SpeakingExerciseTests(unittest.TestCase):
    post=helpers.ListeningTests.post
    audio=helpers.ListeningTests.audio

    def setUp(self):
        helpers.ListeningTests.setUp(self);self.exercises=[]

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for eid in self.exercises:c.execute('DELETE FROM speaking_exercises WHERE id=?',(eid,));c.execute('DELETE FROM speaking_progress WHERE exercise=?',(eid,))
        helpers.ListeningTests.tearDown(self)

    def exercise(self,audio,**extra):
        d={'title':'Synthetic speaking exercise','language':'ko','level':'beginner','reference':'Synthetic reference','translation':'Synthetic translation','audio':audio,'published':True};d.update(extra)
        r=self.post('/api/platform/admin/speaking',d);self.assertEqual(r.status_code,200,r.json)
        self.exercises.append(r.json['id']);return {**d,**r.json}

    def test_publication_filters_and_ai_provenance(self):
        asset=self.audio(False);d=self.exercise(asset['url'],published=False)
        self.assertEqual(self.c.get('/api/platform/speaking').json['exercises'],[])
        self.assertEqual(self.post('/api/platform/admin/speaking',{**d,'published':True}).status_code,400)
        self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
        saved=self.post('/api/platform/admin/speaking',{**d,'published':True});self.assertEqual(saved.status_code,200)
        self.exercise(asset['url'],language='lo',level='advanced')
        items=self.c.get('/api/platform/speaking?language=ko&level=beginner').json['exercises'];self.assertEqual(len(items),1)
        self.assertEqual(items[0]['id'],d['id']);self.assertFalse(items[0]['audio_ai_generated'])
        self.assertEqual(len(self.c.get('/api/platform/speaking?language=lo&level=advanced').json['exercises']),1)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO generated_audio VALUES (?,?,?,?,?,?,?)',(asset['id'],'fixture','fixture','ko','fixture',time.time(),1))
        self.assertTrue(self.c.get('/api/platform/speaking').json['exercises'][0]['audio_ai_generated'])
        self.post('/api/platform/admin/media/'+asset['id'],{'published':False})
        self.assertEqual(self.c.get('/api/platform/speaking').json['exercises'],[])
        self.assertEqual(self.post('/api/platform/speaking/'+d['id']+'/practice',{'practiced':True,'revision':saved.json['revision']}).status_code,404)

    def test_owner_scoped_self_report_and_revision_changes(self):
        item=self.exercise(self.audio()['url']);url='/api/platform/speaking/'+item['id']+'/practice'
        r=self.post(url,{'practiced':True,'revision':1,'score':100});self.assertEqual(r.status_code,200);self.assertTrue(r.json['self_reported']);self.assertNotIn('score',r.json)
        self.assertEqual(self.post(url,{'practiced':True,'revision':1}).json,r.json)
        response=self.c.get('/api/platform/speaking');self.assertEqual(response.headers['Cache-Control'],'no-store');self.assertTrue(response.json['exercises'][0]['practiced_current'])
        public=legacy.app.test_client().get('/api/platform/speaking').json['exercises'][0];self.assertIsNone(public['practiced']);self.assertFalse(public['practiced_current'])
        updated=self.post('/api/platform/admin/speaking',{**item,'reference':'Updated reference'});self.assertEqual(updated.json['revision'],2)
        self.assertFalse(self.c.get('/api/platform/speaking').json['exercises'][0]['practiced_current'])
        self.assertEqual(self.post(url,{'practiced':True,'revision':1}).status_code,409)
        self.assertEqual(self.post('/api/platform/admin/speaking',item).status_code,409)
        self.assertEqual(self.post(url,{'practiced':True,'revision':2}).status_code,200)

    def test_roles_and_validation(self):
        asset=self.audio();item=self.exercise(asset['url'])
        for changes in ({'level':'expert'},{'language':'xx'},{'reference':''},{'published':1},{'audio':'https://example.com/private.wav'},{'audio':''}):
            self.assertEqual(self.post('/api/platform/admin/speaking',{**item,**changes}).status_code,400)
        for body in ({},{'practiced':False,'revision':1},{'practiced':True,'revision':True}):
            self.assertEqual(self.post('/api/platform/speaking/'+item['id']+'/practice',body).status_code,400)
        self.assertEqual(self.c.get('/api/platform/speaking?level=expert').status_code,400)
        legacy.users[self.name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.c.get('/api/platform/admin/speaking').status_code,200)
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.c.get('/api/platform/admin/speaking').status_code,403)
        self.assertEqual(self.post('/api/platform/admin/speaking',item).status_code,403)
        legacy.users[self.name]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post('/api/platform/speaking/'+item['id']+'/practice',{'practiced':True,'revision':1}).status_code,401)
