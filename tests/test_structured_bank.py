import json,os,secrets,sqlite3,unittest
from test_platform import legacy

class StructuredBankTests(unittest.TestCase):
    def setUp(self):
        self.name='bank_'+secrets.token_hex(4);legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'teacher','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.ids=[];self.courses=[];self.lessons=[];self.url='/api/platform/admin/lesson-question-bank';self.tag=secrets.token_hex(6)
        self.q={'question':'Synthetic '+self.tag,'type':'choice','options':['a','b'],'answer':0,'category':self.tag,'source':'Synthetic reference','explanation':'Synthetic explanation'}
    def post(self,url,body):return self.c.post(url,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})
    def save(self,q=None,**extra):
        r=self.post(self.url,{'language':'ko','question':q or self.q,'archived':False,**extra})
        if r.status_code==200 and r.json['id'] not in self.ids:self.ids.append(r.json['id'])
        return r
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for qid in self.ids:c.execute('DELETE FROM structured_question_bank WHERE id=?',(qid,));c.execute('DELETE FROM structured_question_versions WHERE question=?',(qid,))
            for cid in self.courses:c.execute('DELETE FROM courses WHERE id=?',(cid,))
            for lid in self.lessons:
                for table,key in [('course_lessons','id'),('lesson_revisions','lesson'),('course_progress','lesson')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(lid,))
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_mixed_types_filters_archive_stale_and_roles(self):
        qs=[self.q,{'question':self.tag+' blank','type':'blank','accepted':['word']},{'question':self.tag+' order','type':'ordering','options':['a','b'],'answer':[1,0]},{'question':self.tag+' match','type':'matching','pairs':[{'left':'a','right':'A'},{'left':'b','right':'B'}]}]
        for q in qs:self.assertEqual(self.save(q).status_code,200)
        r=self.c.get(self.url+'?q='+self.tag);self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.json['total'],4)
        self.assertEqual(self.c.get(self.url+'?q='+self.tag+'&type=matching').json['total'],1)
        self.assertEqual(self.c.get(self.url+'?q='+self.tag+'&language=lo').json['total'],0)
        qid=self.ids[0];self.assertEqual(self.save(id=qid,revision=1,archived=True).status_code,200)
        self.assertEqual(self.save(id=qid,revision=1).status_code,409)
        self.assertEqual(self.c.get(self.url+'?q='+self.tag+'&archived=1').json['total'],1)
        self.assertEqual(self.save(id=qid,revision=2).status_code,200)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM structured_question_versions WHERE question=?',(qid,)).fetchone()[0],3)
        for role in ('student',):
            legacy.users[self.name]['role']=role;legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.c.get(self.url).status_code,403);self.assertEqual(self.save().status_code,403)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.c.get(self.url).status_code,403)

    def test_copies_in_two_lessons_keep_original_snapshot(self):
        r=self.save();qid=r.json['id'];q={**self.q,'bank_id':qid,'bank_revision':1,'bank_language':'ko'}
        for i in range(2):
            cid=self.post('/api/platform/admin/courses',{'title':'Synthetic bank reuse','language':'ko'}).json['id'];self.courses.append(cid)
            content={'title':'Synthetic bank copy','blocks':[{'type':'text','value':'Fixture'}],'quiz':[q]}
            lid=self.post('/api/platform/admin/courses/'+cid+'/lessons',content).json['id'];self.lessons.append(lid)
            self.assertEqual(self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'}).status_code,200)
        self.assertEqual(self.save({**self.q,'answer':1,'question':'Changed bank text'},id=qid,revision=1).status_code,200)
        for lid in self.lessons:
            public=self.c.get('/api/platform/lessons/'+lid).json['lesson']['quiz'][0]
            self.assertEqual(public['question'],self.q['question']);self.assertNotIn('answer',public);self.assertNotIn('source',public);self.assertNotIn('bank_id',public)
            self.assertEqual(self.post('/api/platform/lessons/'+lid+'/complete',{'answers':{'0':0}}).json['score'],100)

    def test_invalid_payload_media_and_pagination(self):
        for body in ([],{'language':'ko','question':{},'archived':False},{'language':'xx','question':self.q,'archived':False},{'language':'ko','question':{**self.q,'private':'bad'},'archived':False}):self.assertEqual(self.post(self.url,body).status_code,400)
        self.assertEqual(self.save({**self.q,'audio_url':'/media/library/'+secrets.token_hex(16)+'.wav'}).status_code,400)
        for i in range(31):self.save({**self.q,'question':self.tag+' '+str(i)})
        first=self.c.get(self.url+'?q='+self.tag).json;second=self.c.get(self.url+'?q='+self.tag+'&page=2').json
        self.assertEqual(first['total'],31);self.assertEqual(len(first['questions']),30);self.assertEqual(len(second['questions']),1)
        self.assertFalse({q['id'] for q in first['questions']}&{q['id'] for q in second['questions']})
        self.assertEqual(self.c.get(self.url+'?page=0').status_code,400)
