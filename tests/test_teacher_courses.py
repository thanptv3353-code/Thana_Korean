import os,secrets,sqlite3,unittest
from test_platform import legacy


class TeacherCourseTests(unittest.TestCase):
    def setUp(self):
        self.admin='scope_admin_'+secrets.token_hex(4);self.teacher='scope_teacher_'+secrets.token_hex(4)
        for name,role in ((self.admin,'admin'),(self.teacher,'teacher')):
            legacy.users[name]={'username':name,'name':'Synthetic '+role,'role':role,'status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client();self.sign(self.admin)
        self.content={'title':'Synthetic draft','module':'Fixture','order':1,'blocks':[{'type':'text','value':'Synthetic private text'}],'quiz':[]}
        self.courses=[];self.lessons=[]
        for title in ('Assigned fixture','Unassigned fixture'):
            cid=self.post('/api/platform/admin/courses',{'title':title,'language':'ko'}).json['id'];self.courses.append(cid)
            lid=self.post('/api/platform/admin/courses/'+cid+'/lessons',self.content).json['id'];self.lessons.append(lid)
            self.post('/api/platform/admin/lessons/'+lid,{'revision':1,'action':'publish','content':self.content})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for cid in self.courses:
                c.execute('DELETE FROM courses WHERE id=?',(cid,));c.execute('DELETE FROM course_rules WHERE course=?',(cid,));c.execute('DELETE FROM premium_courses WHERE course=?',(cid,))
            for lid in self.lessons:
                c.execute('DELETE FROM course_lessons WHERE id=?',(lid,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(lid,))
            c.execute('DELETE FROM teacher_course_scopes WHERE username=?',(self.teacher,));c.execute('DELETE FROM teacher_course_assignments WHERE username=?',(self.teacher,))
            c.execute('DELETE FROM audit_log WHERE actor IN (?,?)',(self.admin,self.teacher))
        for name in (self.admin,self.teacher):legacy.users.pop(name,None)
        legacy._save(legacy.USERS_FILE,legacy.users)

    def sign(self,name):
        with self.c.session_transaction() as s:s.clear();s['username']=name

    def post(self,path,body):
        token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=body,headers={'X-CSRF-Token':token})

    def assign(self,courses,restricted=True):
        self.sign(self.admin);r=self.post('/api/platform/admin/teacher-assignments/'+self.teacher,{'restricted':restricted,'courses':courses});self.assertEqual(r.status_code,200,r.json);self.sign(self.teacher)

    def test_scope_enforced_on_drafts_history_and_mutations(self):
        self.assign([self.courses[0]])
        data=self.c.get('/api/platform/admin/courses').json
        self.assertEqual([c['id'] for c in data['courses']],[self.courses[0]])
        self.assertEqual([l['id'] for l in data['lessons']],[self.lessons[0]]);self.assertFalse(data['can_create'])
        self.assertEqual(self.c.get('/api/platform/admin/lessons/'+self.lessons[1]+'/revisions').status_code,403)
        self.assertEqual(self.c.get('/api/platform/admin/lessons/'+self.lessons[1]+'/revisions/1').status_code,403)
        self.assertEqual(self.post('/api/platform/admin/courses/'+self.courses[1]+'/lessons',self.content).status_code,403)
        for action in ('save','publish','unpublish'):
            self.assertEqual(self.post('/api/platform/admin/lessons/'+self.lessons[1],{'revision':2,'action':action,'content':self.content}).status_code,403)
        self.assertEqual(self.post('/api/platform/admin/courses/'+self.courses[1]+'/sequence',{'sequential':True}).status_code,403)
        self.assertEqual(self.post('/api/platform/admin/courses',{'title':'Not allowed','language':'ko'}).status_code,403)
        self.assertEqual(self.c.get('/api/platform/admin/lessons/'+self.lessons[0]+'/revisions/1').status_code,200)
        self.assertEqual(self.post('/api/platform/admin/lessons/'+self.lessons[0],{'revision':2,'action':'save','content':self.content}).status_code,200)
        counts=self.c.get('/api/platform/management').json['counts'];self.assertEqual((counts['courses'],counts['lessons']),(1,1))

    def test_revocation_and_premium_no_bypass(self):
        self.assign([self.courses[0]])
        self.sign(self.admin);self.post('/api/platform/admin/courses/'+self.courses[1]+'/premium',{'premium':True});self.sign(self.teacher)
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.lessons[1]).status_code,403)
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.lessons[0]).status_code,200)
        self.assign([])
        self.assertEqual(self.c.get('/api/platform/admin/courses').json['courses'],[])
        self.assertEqual(self.c.get('/api/platform/admin/lessons/'+self.lessons[0]+'/revisions').status_code,403)
        self.assign([],False)
        ids={c['id'] for c in self.c.get('/api/platform/admin/courses').json['courses']};self.assertTrue(set(self.courses)<=ids)
        self.assertEqual(self.c.get('/api/platform/lessons/'+self.lessons[1]).status_code,200)

    def test_admin_only_atomic_validation_and_legacy_default(self):
        self.sign(self.teacher)
        self.assertTrue(self.c.get('/api/platform/admin/courses').json['can_create'])
        self.assertEqual(self.c.get('/api/platform/admin/teacher-assignments').status_code,403)
        self.assertEqual(self.post('/api/platform/admin/teacher-assignments/'+self.teacher,{'restricted':False,'courses':[]}).status_code,403)
        self.assign([self.courses[0]]);self.sign(self.admin)
        for bad in ({'restricted':1,'courses':[]},{'restricted':True,'courses':['missing']},{'restricted':True,'courses':[{}]}):
            self.assertEqual(self.post('/api/platform/admin/teacher-assignments/'+self.teacher,bad).status_code,400)
        data=self.c.get('/api/platform/admin/teacher-assignments');self.assertEqual(data.headers['Cache-Control'],'no-store')
        teacher=next(t for t in data.json['teachers'] if t['username']==self.teacher);self.assertEqual(teacher['courses'],[self.courses[0]])
        self.assertEqual(self.post('/api/platform/admin/teacher-assignments/'+self.admin,{'restricted':True,'courses':[]}).status_code,404)
        self.sign(self.teacher);legacy.users[self.teacher]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.c.get('/api/platform/admin/courses').status_code,403)
