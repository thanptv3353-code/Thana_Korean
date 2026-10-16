import secrets,sqlite3,os,unittest
from test_platform import legacy

class LessonQuizMediaTests(unittest.TestCase):
    def setUp(self):
        self.name='quiz_media_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'teacher','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic media quiz','language':'ko'}).json['id'];self.ids=[];self.assets=[]
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for kind,ext in [('image','png'),('audio','wav')]:
                aid=secrets.token_hex(16);filename=aid+'.'+ext;self.assets.append((aid,filename,kind));c.execute('INSERT INTO media_assets VALUES (?,?,?,?,?)',(aid,'Synthetic asset',filename,kind,0))
        self.q={'question':'Synthetic audio/image question','options':['a','b'],'answer':0,'explanation':'Hidden until grading','image_url':'/media/library/'+self.assets[0][1],'audio_url':'/media/library/'+self.assets[1][1],'ai_audio':True}
        self.content={'title':'Synthetic lesson','blocks':[{'type':'text','value':'Fixture'}],'quiz':[self.q]}

    def post(self,path,body):return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.ids:
                c.execute('DELETE FROM course_lessons WHERE id=?',(lid,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(lid,));c.execute('DELETE FROM course_progress WHERE lesson=?',(lid,))
            for aid,_,_ in self.assets:c.execute('DELETE FROM media_assets WHERE id=?',(aid,))
            c.execute('DELETE FROM courses WHERE id=?',(self.cid,));c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_draft_publication_revocation_answer_privacy_and_grading(self):
        lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',self.content).json['id'];self.ids.append(lid);path='/api/platform/admin/lessons/'+lid
        self.assertEqual(self.post(path,{'content':self.content,'revision':1,'action':'publish'}).status_code,400)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for aid,_,_ in self.assets:c.execute('UPDATE media_assets SET published=1 WHERE id=?',(aid,))
        self.assertEqual(self.post(path,{'content':self.content,'revision':1,'action':'publish'}).status_code,200)
        public='/api/platform/lessons/'+lid;q=self.c.get(public).json['lesson']['quiz'][0]
        self.assertEqual(q['audio_url'],self.q['audio_url']);self.assertEqual(q['image_url'],self.q['image_url']);self.assertNotIn('answer',q);self.assertNotIn('explanation',q);self.assertNotIn('ai_audio',q)
        r=self.post(public+'/complete',{'answers':{'0':0}});self.assertEqual(r.json['score'],100);self.assertEqual(r.json['detail'][0]['explanation'],self.q['explanation'])
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for aid,_,_ in self.assets:c.execute('UPDATE media_assets SET published=0 WHERE id=?',(aid,))
        q=self.c.get(public).json['lesson']['quiz'][0];self.assertEqual(q['audio_url'],'');self.assertEqual(q['image_url'],'')
        self.assertEqual(self.post(path,{'content':self.content,'revision':2,'action':'publish'}).status_code,400)

    def test_invalid_urls_missing_media_and_wrong_kind(self):
        url='/api/platform/admin/courses/'+self.cid+'/lessons'
        for bad in (None,123,'javascript:alert(1)','https://example.com/audio.wav','/media/library/../secret.wav'):
            q={**self.q,'audio_url':bad};self.assertEqual(self.post(url,{**self.content,'quiz':[q]}).status_code,400)
        q={**self.q,'image_url':'','audio_url':'/media/library/'+secrets.token_hex(16)+'.wav'}
        lid=self.post(url,{**self.content,'quiz':[q]}).json['id'];self.ids.append(lid)
        path='/api/platform/admin/lessons/'+lid
        self.assertEqual(self.post(path,{'content':{**self.content,'quiz':[q]},'revision':1,'action':'publish'}).status_code,400)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('UPDATE media_assets SET kind=?,published=1 WHERE id=?',('image',self.assets[1][0]))
        self.assertEqual(self.post(path,{'content':{**self.content,'quiz':[{**self.q,'image_url':''}]},'revision':1,'action':'publish'}).status_code,400)
