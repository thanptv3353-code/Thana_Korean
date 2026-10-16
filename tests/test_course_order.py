import json,os,secrets,sqlite3,unittest
from test_platform import legacy

class CourseOrderTests(unittest.TestCase):
    def setUp(self):
        self.name='order_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'teacher','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.cid=self.post('/api/platform/admin/courses',{'title':'Synthetic order course','language':'ko'}).json['id'];self.ids=[]
        for i in range(1,4):
            content={'title':'Synthetic '+str(i),'order':i,'module':'Fixture','blocks':[{'type':'text','value':'Preserved text '+str(i)}],'quiz':[]}
            lid=self.post('/api/platform/admin/courses/'+self.cid+'/lessons',content).json['id'];self.ids.append(lid)
            self.post('/api/platform/admin/lessons/'+lid,{'revision':1,'action':'publish','content':content})
        self.path='/api/platform/admin/courses/'+self.cid+'/order'

    def post(self,path,body):
        return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def items(self,ids=None,revision=2):return {'lessons':[{'id':lid,'revision':revision} for lid in (ids if ids is not None else self.ids)]}

    def rows(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            return c.execute('SELECT id,draft,published,revision FROM course_lessons WHERE course=? ORDER BY id',(self.cid,)).fetchall()

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for lid in self.ids:
                c.execute('DELETE FROM course_lessons WHERE id=?',(lid,));c.execute('DELETE FROM lesson_revisions WHERE lesson=?',(lid,))
            c.execute('DELETE FROM courses WHERE id=?',(self.cid,))
            for table,key in [('teacher_course_scopes','username'),('teacher_course_assignments','username'),('audit_log','actor')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_draft_only_atomic_reorder_history_and_stale_guard(self):
        before=self.rows();r=self.post(self.path,self.items(list(reversed(self.ids))))
        self.assertEqual(r.status_code,200,r.json);self.assertEqual(r.json['changed'],2)
        rows=self.rows()
        for old,new in zip(before,rows):
            self.assertEqual(old[0],new[0]);self.assertEqual(old[2],new[2])
            old_draft=json.loads(old[1]);new_draft=json.loads(new[1]);expected=4-old_draft['order']
            self.assertEqual(new_draft['order'],expected)
            new_draft['order']=old_draft['order'];self.assertEqual(old_draft,new_draft)
            self.assertEqual(new[3],old[3]+(expected!=old_draft['order']))
            history=self.c.get('/api/platform/admin/lessons/'+new[0]+'/revisions').json['revisions']
            self.assertEqual(history[0]['revision'],new[3])
        self.assertEqual(self.post(self.path,self.items()).status_code,409);self.assertEqual(self.rows(),rows)
        catalog=next(c for c in self.c.get('/api/platform/courses').json['courses'] if c['id']==self.cid)
        self.assertEqual([l['id'] for l in catalog['lessons']],self.ids)
        current={'lessons':[{'id':r[0],'revision':r[3]} for r in sorted(rows,key=lambda r:json.loads(r[1])['order'])]}
        self.assertEqual(self.post(self.path,current).json['changed'],0)

    def test_malformed_missing_cross_course_and_role_denials(self):
        before=self.rows()
        for bad in ([],{}, {'lessons':[{}]},self.items([self.ids[0],self.ids[0]]),{'lessons':[{'id':self.ids[0],'revision':True}]}):
            self.assertEqual(self.post(self.path,bad).status_code,400)
        for bad in (self.items(self.ids[:-1]),self.items(['other-course-id',*self.ids[1:]]),self.items(revision=1)):
            self.assertEqual(self.post(self.path,bad).status_code,409)
        self.assertEqual(self.rows(),before)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO teacher_course_scopes VALUES (?,1)',(self.name,))
        self.assertEqual(self.post(self.path,self.items()).status_code,403)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO teacher_course_assignments VALUES (?,?)',(self.name,self.cid))
        self.assertEqual(self.post(self.path,self.items(list(reversed(self.ids)))) .status_code,200)
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post(self.path,self.items()).status_code,403)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.post(self.path,self.items()).status_code,403)
