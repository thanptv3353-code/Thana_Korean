import os,secrets,sqlite3,unittest
from test_platform import legacy

class CourseLevelTests(unittest.TestCase):
    def setUp(self):
        self.name='level_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic level teacher','role':'teacher','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic level course','language':'ko'}).json['id']
        content={'title':'Synthetic lesson','blocks':[{'type':'text','value':'Fixture'}],'quiz':[]}
        self.lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',content).json['id']
        self.post('/api/platform/admin/lessons/'+self.lid,{'content':content,'revision':1,'action':'publish'})
        self.path='/api/platform/admin/courses/'+self.cid+'/level'

    def post(self,path,body):
        return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for table,key,value in [('courses','id',self.cid),('course_levels','course',self.cid),('course_lessons','id',self.lid),('lesson_revisions','lesson',self.lid),('teacher_course_scopes','username',self.name),('teacher_course_assignments','username',self.name),('audit_log','actor',self.name)]:
                c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(value,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def catalog(self,admin=False):
        return next(c for c in self.c.get('/api/platform/'+('admin/' if admin else '')+'courses').json['courses'] if c['id']==self.cid)

    def test_preserved_defaults_public_metadata_and_stale_rejection(self):
        self.assertEqual(self.catalog()['level'],'');self.assertEqual(self.catalog(True)['level_revision'],0)
        for revision,level in enumerate(('beginner','intermediate','advanced','eps-topik','')):
            r=self.post(self.path,{'level':level,'revision':revision});self.assertEqual(r.status_code,200,r.json)
            self.assertEqual(self.catalog()['level'],level)
            self.assertEqual(self.catalog(True)['level_revision'],revision+1)
            self.assertEqual(self.post(self.path,{'level':'beginner','revision':revision}).status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM audit_log WHERE actor=? AND action=?',(self.name,'course_level_save')).fetchone()[0],5)
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.lid).status_code,200)

    def test_validation_and_server_roles_scope(self):
        for bad in ([],{'level':[],'revision':0},{'level':'expert','revision':0},{'level':'beginner','revision':True},{'level':'beginner','revision':-1},{'level':'beginner','revision':0,'role':'admin'}):
            self.assertEqual(self.post(self.path,bad).status_code,400)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_scopes VALUES (?,1)',(self.name,))
        self.assertEqual(self.post(self.path,{'level':'beginner','revision':0}).status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO teacher_course_assignments VALUES (?,?)',(self.name,self.cid))
        self.assertEqual(self.post(self.path,{'level':'beginner','revision':0}).status_code,200)
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post(self.path,{'level':'advanced','revision':1}).status_code,403)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.post(self.path,{'level':'advanced','revision':1}).status_code,403)
        self.assertEqual(self.catalog()['level'],'beginner')
