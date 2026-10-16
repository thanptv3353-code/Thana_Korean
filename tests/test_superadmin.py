import os,secrets,sqlite3,unittest
from test_platform import legacy
from scripts.activate_system_owner import activate

class SuperAdminTests(unittest.TestCase):
    def setUp(self):
        prefix=secrets.token_hex(4);self.owner='owner_'+prefix;self.admin='admin_'+prefix;self.student='student_'+prefix
        for name,role in ((self.owner,'superadmin'),(self.admin,'admin'),(self.student,'student')):
            legacy.users[name]={'username':name,'name':'Synthetic '+role,'role':role,'status':'approved','pw':legacy.hash_pw('SyntheticOwnerPass123')}
        legacy._save(legacy.USERS_FILE,legacy.users);self.c=legacy.app.test_client();self.sign(self.owner)
    def tearDown(self):
        for name in (self.owner,self.admin,self.student):legacy.users.pop(name,None)
        legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('DELETE FROM audit_log WHERE actor IN (?,?,?)',(self.owner,self.admin,self.student))
            c.execute('DELETE FROM recovery_tokens WHERE username IN (?,?,?)',(self.owner,self.admin,self.student))
    def sign(self,name):
        with self.c.session_transaction() as s:s.clear();s['username']=name
    def post(self,url,body):return self.c.post(url,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def test_owner_content_and_system_access_admin_denial(self):
        self.assertEqual(self.c.get('/api/platform/admin/courses').status_code,200)
        self.assertTrue(self.c.get('/api/platform/admin/courses').json['can_set_access'])
        self.assertEqual(self.c.get('/api/platform/admin/teacher-assignments').status_code,200)
        self.assertEqual(self.c.get('/api/platform/admin/site-settings').status_code,200)
        self.assertTrue(self.c.get('/api/platform/management').json['system_control'])
        self.assertEqual(self.c.get('/legacy-admin').status_code,200)
        self.assertEqual(self.c.get('/api/platform/admin/lesson-question-bank').status_code,200)
        self.sign(self.admin)
        self.assertEqual(self.c.get('/api/platform/admin/courses').status_code,200)
        self.assertEqual(self.c.get('/api/platform/admin/teacher-assignments').status_code,403)
        self.assertEqual(self.c.get('/api/platform/admin/site-settings').status_code,403)
        self.assertEqual(self.c.get('/api/admin/backup').status_code,403)
        self.assertFalse(self.c.get('/api/platform/admin/accounts').json['system_control'])
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.student,{'role':'teacher','status':'approved'}).status_code,403)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.student,{'role':'student','status':'rejected'}).status_code,200)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.owner+'/recovery',{}).status_code,403)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.owner,{'role':'superadmin','status':'approved'}).status_code,403)

    def test_owner_permission_changes_and_last_owner_guard(self):
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.student,{'role':'teacher','status':'approved'}).status_code,200)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.owner,{'role':'admin','status':'approved'}).status_code,400)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.admin,{'role':'superadmin','status':'approved'}).status_code,200)
        self.sign(self.admin)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.owner,{'role':'admin','status':'approved'}).status_code,200)
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.admin,{'role':'admin','status':'approved'}).status_code,400)
        self.sign(self.student)
        with self.c.session_transaction() as s:s['role']='superadmin'
        self.assertEqual(self.c.get('/api/platform/admin/accounts').status_code,403)
        # Disabled owner does not silently re-enable ordinary administrator powers.
        legacy.users[self.admin]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users);self.sign(self.owner)
        self.assertFalse(self.c.get('/api/platform/management').json['system_control'])

    def test_explicit_activation_dry_run_and_existing_owner_guard(self):
        with self.assertRaises(ValueError):activate(legacy,self.admin,False)
        legacy.users.pop(self.owner);legacy._save(legacy.USERS_FILE,legacy.users)
        self.sign(self.admin);self.assertTrue(self.c.get('/api/platform/management').json['system_control'])
        with self.assertRaises(ValueError):activate(legacy,self.student,False)
        self.assertEqual(activate(legacy,self.admin,False)['applied'],False);self.assertEqual(legacy.users[self.admin]['role'],'admin')
        self.assertEqual(self.post('/api/platform/admin/accounts/'+self.student,{'role':'superadmin','status':'approved'}).status_code,403)
        old_version=legacy.users[self.admin].get('auth_version',0)
        self.assertTrue(activate(legacy,self.admin,True)['applied']);self.assertEqual(legacy.users[self.admin]['auth_version'],old_version+1)
        self.assertEqual(self.c.get('/api/platform/admin/accounts').status_code,403)

    def test_fresh_bootstrap_flag_never_promotes_existing_accounts(self):
        import subprocess,sys,tempfile
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            runtime=Path(directory)/'ordinary';runtime.mkdir()
            env={**os.environ,'THANA_DATA_DIR':str(runtime),'THANA_PLATFORM_DB':str(runtime/'platform.sqlite3'),'THANA_BOOTSTRAP_PASSWORD':'SyntheticBootstrap123','THANA_BOOTSTRAP_SUPERADMIN':'0'}
            def role():return subprocess.check_output([sys.executable,'-c',"import app; print(app.users['admin']['role'])"],cwd=root,env=env,text=True,timeout=20).strip()
            self.assertEqual(role(),'admin');env['THANA_BOOTSTRAP_SUPERADMIN']='1';self.assertEqual(role(),'admin')
            fresh=Path(directory)/'owner';fresh.mkdir();env['THANA_DATA_DIR']=str(fresh);env['THANA_PLATFORM_DB']=str(fresh/'platform.sqlite3')
            self.assertEqual(role(),'superadmin')
