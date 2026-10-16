import os,secrets,sqlite3,time,unittest
from test_platform import legacy

class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.name='resume_'+secrets.token_hex(4);self.other='other_'+secrets.token_hex(4)
        legacy.users[self.other]={'username':self.other,'name':'Synthetic other learner','role':'student','status':'approved'}
        legacy.users[self.name]={'username':self.name,'name':'Synthetic learner','role':'admin','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic resume','language':'ko'}).json['id'];self.ids=[]
        for i in (1,2):
            content={'title':'Synthetic lesson '+str(i),'order':i,'blocks':[{'type':'text','value':'Fixture'}],'quiz':[]}
            lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',content).json['id'];self.ids.append(lid)
            self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'})
        self.post('/api/platform/admin/courses/'+self.cid+'/sequence',{'sequential':True})
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)

    def post(self,path,body):return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})
    def visit(self,lid,kind='structured'):return self.post('/api/platform/lesson-visits',{'kind':kind,'lesson':lid})
    def resume(self,lang='ko'):return self.c.get('/api/platform/resume?language='+lang)
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.ids:
                for table,key in [('course_lessons','id'),('lesson_revisions','lesson'),('course_progress','lesson')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(lid,))
            for table,key,value in [('courses','id',self.cid),('premium_courses','course',self.cid),('course_rules','course',self.cid),('lesson_visits','owner',self.name),('audit_log','actor',self.name)]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(value,))
        legacy.users.pop(self.other,None);legacy.users.pop(self.name,None);legacy.progress.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users);legacy._save(legacy.PROGRESS_FILE,legacy.progress)

    def test_visit_completion_next_and_review(self):
        self.assertIsNone(self.resume().json['resume'])
        self.assertEqual(self.visit(self.ids[1]).status_code,403)
        self.assertEqual(self.visit(self.ids[0]).status_code,200)
        r=self.resume();self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.json['resume']['lesson'],self.ids[0]);self.assertEqual(r.json['resume']['action'],'resume')
        self.assertNotIn('quiz',r.json['resume']);self.assertIsNone(self.resume('lo').json['resume'])
        self.post('/api/platform/lessons/'+self.ids[0]+'/complete',{'answers':{}})
        self.assertEqual(self.resume().json['resume']['lesson'],self.ids[1]);self.assertEqual(self.resume().json['resume']['action'],'next')
        self.visit(self.ids[1]);self.post('/api/platform/lessons/'+self.ids[1]+'/complete',{'answers':{}})
        self.assertEqual(self.resume().json['resume']['action'],'review')

    def test_owner_privacy_revocation_drafts_and_validation(self):
        self.visit(self.ids[0])
        with self.c.session_transaction() as s:s['username']=self.other
        self.assertIsNone(self.resume().json['resume'])
        with self.c.session_transaction() as s:s['username']=self.name
        for bad in ([],{'kind':'structured','lesson':self.ids[0],'owner':'other'},{'kind':'bad','lesson':self.ids[0]}):self.assertEqual(self.post('/api/platform/lesson-visits',bad).status_code,400)
        self.assertEqual(self.resume('bad').status_code,400)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO premium_courses VALUES (?)',(self.cid,))
        self.assertIsNone(self.resume().json['resume']);self.assertEqual(self.visit(self.ids[0]).status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('DELETE FROM premium_courses WHERE course=?',(self.cid,));c.execute('UPDATE course_lessons SET published=NULL WHERE id=?',(self.ids[0],))
        self.assertIsNone(self.resume().json['resume']);self.assertEqual(self.visit(self.ids[0]).status_code,404)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.resume().status_code,401);self.assertEqual(self.visit(self.ids[0]).status_code,401)

    def test_legacy_visit_and_completion_compete_with_structured(self):
        old=legacy.sorted_lessons();first=old[0]['id'];second=old[1]['id']
        self.assertEqual(self.visit(second,'legacy').status_code,403)
        self.assertEqual(self.visit(first,'legacy').status_code,200)
        r=self.resume().json['resume'];self.assertEqual(r['kind'],'legacy');self.assertIn('/learn?lesson=',r['url'])
        legacy.progress[self.name]={first:{'exam_passed':True,'completed_at':time.time()}};legacy._save(legacy.PROGRESS_FILE,legacy.progress)
        self.assertEqual(self.resume().json['resume']['lesson'],second)
        self.visit(self.ids[0]);self.assertEqual(self.resume().json['resume']['kind'],'structured')

    def test_deleted_account_resume_history_removed(self):
        with self.c.session_transaction() as s:s['username']=self.other
        self.visit(self.ids[0]);self.post('/api/platform/lessons/'+self.ids[0]+'/complete',{'answers':{}})
        legacy.users[self.name]['role']='admin';legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=self.name
        token=self.c.get('/api/csrf').json['token']
        self.assertEqual(self.c.delete('/api/admin/students/'+self.other,headers={'X-CSRF-Token':token}).status_code,200)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM lesson_visits WHERE owner=?',(self.other,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM course_progress WHERE owner=?',(self.other,)).fetchone()[0],0)
