import secrets,sqlite3,os,unittest
from test_platform import legacy

class LessonObjectivesTests(unittest.TestCase):
    def setUp(self):
        self.name='objectives_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'teacher','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic objectives','language':'lo'}).json['id']
        self.content={'title':'Synthetic lesson','blocks':[{'type':'text','value':'Content'}],'quiz':[]};self.ids=[]

    def post(self,path,body):return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.ids:
                c.execute('DELETE FROM course_lessons WHERE id=?',(lid,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(lid,))
            c.execute('DELETE FROM courses WHERE id=?',(self.cid,));c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_published_snapshot_draft_history_and_old_content(self):
        content={**self.content,'objectives':'ທັກທາຍເປັນພາສາລາວ\n라오어로 인사하기 <b>plain text</b>'}
        lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',content).json['id'];self.ids.append(lid)
        path='/api/platform/admin/lessons/'+lid;public='/api/platform/lessons/'+lid
        self.assertEqual(self.c.get(public).status_code,404)
        self.assertEqual(self.post(path,{'content':content,'revision':1,'action':'publish'}).status_code,200)
        self.assertEqual(self.c.get(public).json['lesson']['objectives'],content['objectives'])
        self.post(path,{'content':{**content,'objectives':'Private draft goal'},'revision':2})
        self.assertEqual(self.c.get(public).json['lesson']['objectives'],content['objectives'])
        self.assertEqual(self.c.get(path+'/revisions/2').json['content']['objectives'],content['objectives'])
        self.assertEqual(self.post(path,{'content':self.content,'revision':3,'action':'publish'}).status_code,200)
        self.assertNotIn('objectives',self.c.get(public).json['lesson'])

    def test_type_and_length_validation(self):
        url='/api/platform/admin/courses/'+self.cid+'/lessons'
        for bad in (None,[],{},123,'a'*2001):
            self.assertEqual(self.post(url,{**self.content,'objectives':bad}).status_code,400)
        r=self.post(url,{**self.content,'objectives':'a'*2000});self.assertEqual(r.status_code,201);self.ids.append(r.json['id'])
