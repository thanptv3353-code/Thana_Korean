import os,secrets,sqlite3,unittest
from test_platform import legacy

class LessonVocabularyTests(unittest.TestCase):
    def setUp(self):
        self.name='word_lesson_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'admin','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.word={'ko':'Synthetic '+secrets.token_hex(4),'lo':'ທົດລອງ','example_ko':'Example','example_lo':'ຕົວຢ່າງ','category':'Fixture','published':True,'part_of_speech':'noun'}
        self.wid=self.post('/api/platform/admin/vocabulary',self.word).json['id']
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic shared words','language':'ko'}).json['id']
        self.content={'title':'Shared word','blocks':[{'type':'vocabulary','value':self.wid,'word':{'ko':'Injected stale copy'}}],'quiz':[]}
        self.lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',self.content).json['id']
        self.path='/api/platform/admin/lessons/'+self.lid

    def post(self,path,body):return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for table,key,value in [('vocabulary','id',self.wid),('vocabulary_details','word',self.wid),('courses','id',self.cid),('course_lessons','id',self.lid),('lesson_revisions','lesson',self.lid),('audit_log','actor',self.name),('premium_courses','course',self.cid)]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(value,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_current_public_word_update_withdraw_and_missing(self):
        self.assertEqual(self.post(self.path,{'content':self.content,'revision':1,'action':'publish'}).status_code,200)
        def word():return self.c.get('/api/platform/lessons/'+self.lid).json['lesson']['blocks'][0]['word']
        self.assertEqual(word()['ko'],self.word['ko']);self.assertEqual(word()['part_of_speech'],'noun')
        edited={**self.word,'id':self.wid,'ko':'Updated synthetic word'}
        self.post('/api/platform/admin/vocabulary',edited);self.assertEqual(word()['ko'],edited['ko'])
        self.post('/api/platform/admin/vocabulary',{**edited,'published':False,'example_ko':'Private draft text'})
        self.assertIsNone(word());self.assertEqual(self.c.get('/api/platform/vocabulary/'+self.wid).status_code,404)
        self.assertEqual(self.post(self.path,{'content':self.content,'revision':2,'action':'publish'}).status_code,400)
        self.assertEqual(self.post(self.path,{'content':self.content,'revision':2,'action':'save'}).status_code,200)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('DELETE FROM vocabulary WHERE id=?',(self.wid,))
        self.assertIsNone(word())

    def test_validation_premium_and_answer_privacy(self):
        for value in ('','../secret','<script>',123):
            bad={**self.content,'blocks':[{'type':'vocabulary','value':value}]}
            self.assertEqual(self.post(self.path,{'content':bad,'revision':1}).status_code,400)
        self.assertEqual(self.c.get('/api/platform/vocabulary/'+self.wid).json['word']['id'],self.wid)
        self.assertEqual(self.post(self.path,{'content':self.content,'revision':1,'action':'publish'}).status_code,200)
        self.post('/api/platform/admin/courses/'+self.cid+'/premium',{'premium':True})
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.lid).status_code,403)
        # Shared words stay public independently of course membership.
        self.assertEqual(self.c.get('/api/platform/vocabulary/'+self.wid).status_code,200)

    def test_revoked_image_reference_is_not_resolved(self):
        filename=secrets.token_hex(16)+'.png';url='/media/library/'+filename
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('UPDATE vocabulary_details SET image_url=? WHERE word=?',(url,self.wid))
        # Missing and withdrawn library images are omitted, even for staff preview.
        word=self.c.get('/api/platform/vocabulary/'+self.wid).json['word']
        self.assertEqual(word['image_url'],'');self.assertEqual(word['ko'],self.word['ko'])
