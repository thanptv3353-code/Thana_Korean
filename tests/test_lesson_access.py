import os,secrets,sqlite3,time,unittest
from test_platform import legacy

class LessonAccessTests(unittest.TestCase):
    def setUp(self):
        self.name='access_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic account','role':'admin','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic lesson access','language':'ko'}).json['id'];self.ids=[]
        for i in (1,2):
            content={'title':'Synthetic '+str(i),'order':i,'blocks':[{'type':'text','value':'Private course text'}],'quiz':[]}
            lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',content).json['id'];self.ids.append(lid)
            self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'})

    def post(self,path,body):return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})
    def access(self,lid,mode,revision=0):return self.post('/api/platform/admin/lessons/'+lid+'/access',{'mode':mode,'revision':revision})
    def role(self,role):legacy.users[self.name]['role']=role;legacy._save(legacy.USERS_FILE,legacy.users)
    def catalog(self):return next(c for c in self.c.get('/api/platform/courses').json['courses'] if c['id']==self.cid)
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.ids:
                for table,key in [('course_lessons','id'),('lesson_revisions','lesson'),('lesson_access','lesson'),('course_progress','lesson')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(lid,))
            for table,key,value in [('courses','id',self.cid),('premium_courses','course',self.cid),('course_rules','course',self.cid),('entitlements','owner',self.name),('audit_log','actor',self.name)]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(value,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_inherit_free_override_and_sequence_remains_enforced(self):
        self.post('/api/platform/admin/courses/'+self.cid+'/premium',{'premium':True})
        self.post('/api/platform/admin/courses/'+self.cid+'/sequence',{'sequential':True})
        self.assertEqual(self.access(self.ids[0],'free').status_code,200)
        self.assertEqual(self.access(self.ids[1],'free').status_code,200)
        self.role('student')
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[0]).status_code,200)
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[1]).status_code,403)
        self.assertTrue(self.catalog()['premium']);self.assertFalse(self.catalog()['lessons'][0]['premium'])
        self.post('/api/platform/lessons/'+self.ids[0]+'/complete',{'answers':{}})
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[1]).status_code,200)
        self.role('admin');self.access(self.ids[1],'inherit',1);self.role('student')
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[1]).status_code,403)
        self.assertEqual(self.post('/api/platform/lessons/'+self.ids[1]+'/complete',{'answers':{}}).status_code,403)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[0]).status_code,200)

    def test_premium_override_entitlement_expiry_and_catalog(self):
        self.assertEqual(self.access(self.ids[0],'premium').status_code,200);self.role('student')
        self.assertFalse(self.catalog()['premium']);self.assertTrue(self.catalog()['lessons'][0]['premium'])
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[0]).status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO entitlements VALUES (?,?)',(self.name,time.time()+3600))
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[0]).status_code,200)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('UPDATE entitlements SET expires=0 WHERE owner=?',(self.name,))
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.ids[0]).status_code,403)
        self.assertEqual(self.post('/api/platform/lesson-visits',{'kind':'structured','lesson':self.ids[0]}).status_code,403)

    def test_admin_only_validation_stale_guard_and_audit(self):
        path='/api/platform/admin/lessons/'+self.ids[0]+'/access'
        for bad in ([],{'mode':True,'revision':0},{'mode':'public','revision':0},{'mode':'free','revision':True},{'mode':'free','revision':-1}):self.assertEqual(self.post(path,bad).status_code,400)
        self.assertEqual(self.access(self.ids[0],'premium').status_code,200)
        self.assertEqual(self.access(self.ids[0],'free').status_code,409)
        lesson=next(l for l in self.c.get('/api/platform/admin/courses').json['lessons'] if l['id']==self.ids[0]);self.assertEqual(lesson['access_mode'],'premium');self.assertEqual(lesson['access_revision'],1)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM audit_log WHERE actor=? AND action=?',(self.name,'lesson_access_save')).fetchone()[0],1)
        for role in ('teacher','student'):
            self.role(role);self.assertEqual(self.access(self.ids[0],'free',1).status_code,403)
        self.role('teacher');self.assertFalse(self.c.get('/api/platform/admin/courses').json['can_set_access'])
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.access(self.ids[0],'free',1).status_code,403)
