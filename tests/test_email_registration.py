import hashlib,os,re,secrets,sqlite3,time,unittest
from unittest.mock import patch
from test_platform import legacy
from email_delivery import configuration,deliver_pending,send_message

ENV={'THANA_EMAIL_ENABLED':'1','THANA_PUBLIC_URL':'https://learning.example.test','THANA_SMTP_HOST':'smtp.example.test','THANA_SMTP_PORT':'587','THANA_SMTP_USERNAME':'synthetic-user','THANA_SMTP_PASSWORD':'synthetic-secret','THANA_EMAIL_FROM':'learning@example.test'}

class EmailRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,ENV);self.env.start();self.prefix='email_'+secrets.token_hex(4);self.c=legacy.app.test_client();self.c.environ_base['REMOTE_ADDR']=self.prefix
        self.path=os.environ['THANA_PLATFORM_DB'];self.started=time.time()
        with sqlite3.connect(self.path) as c:self.last=c.execute('SELECT COALESCE(MAX(id),0) FROM email_outbox').fetchone()[0]
    def tearDown(self):
        with sqlite3.connect(self.path) as c:
            for name in list(legacy.users):
                if name.startswith(self.prefix):
                    legacy.users.pop(name,None);c.execute('DELETE FROM email_accounts WHERE username=?',(name,));c.execute('DELETE FROM email_verifications WHERE username=?',(name,));c.execute('DELETE FROM audit_log WHERE actor=?',(name,))
            c.execute('DELETE FROM email_outbox WHERE id>?',(self.last,))
            for scope in ('register','resend','verify'):c.execute('DELETE FROM email_limits WHERE key=?',(hashlib.sha256((scope+'|'+self.prefix).encode()).hexdigest(),))
        legacy._save(legacy.USERS_FILE,legacy.users);self.env.stop()
    def post(self,path,body):
        if path=='verify' and 'password' not in body:body={**body,'password':'Synthetic-password-2026'}
        token=self.c.get('/api/csrf').json['token'];return self.c.post('/api/platform/email/'+path,json=body,headers={'X-CSRF-Token':token})
    def signup(self,suffix=''):
        name=self.prefix+suffix
        r=self.post('register',{'username':name,'name':'Synthetic email learner','email':name+'@example.test','password':'Synthetic-password-2026'})
        self.assertEqual(r.status_code,201,r.json);self.assertNotIn('token',r.json)
        return name,self.token()
    def token(self):
        with sqlite3.connect(self.path) as c:body=c.execute("SELECT body FROM email_outbox WHERE id>? AND state='pending' ORDER BY id DESC LIMIT 1",(self.last,)).fetchone()[0]
        return body.split('#verify=',1)[1].split()[0]
    def login(self,name,password='Synthetic-password-2026'):
        csrf=self.c.get('/api/csrf').json['token'];return self.c.post('/api/login',json={'username':name,'password':password},headers={'X-CSRF-Token':csrf})
    def test_verification_and_approval_are_separate(self):
        name,token=self.signup();self.assertEqual(legacy.users[name]['status'],'pending')
        with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT hash FROM email_verifications WHERE username=?',(name,)).fetchone()[0],hashlib.sha256(token.encode()).hexdigest())
        self.assertEqual(self.login(name,'wrong').status_code,401)
        self.assertEqual(self.login(name).status_code,403)
        verified=self.post('verify',{'token':token});self.assertEqual(verified.status_code,200);self.assertTrue(verified.json['approval_required'])
        self.assertEqual(legacy.users[name]['status'],'pending');self.assertEqual(self.login(name).status_code,403)
        self.assertEqual(self.post('verify',{'token':token}).status_code,400)
        legacy.users[name]['status']='approved';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.login(name).status_code,200)
        with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT body FROM email_outbox WHERE id>?',(self.last,)).fetchone()[0],'')
    def test_approval_cannot_bypass_verification(self):
        name,token=self.signup();legacy.users[name]['status']='approved';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.login(name).status_code,403)
        with sqlite3.connect(self.path) as c:
            row=c.execute('SELECT * FROM email_accounts WHERE username=?',(name,)).fetchone();c.execute('DELETE FROM email_accounts WHERE username=?',(name,))
        self.assertEqual(self.login(name).status_code,403)
        with sqlite3.connect(self.path) as c:c.execute('INSERT INTO email_accounts VALUES (?,?,?,?)',row)
        self.assertFalse(self.post('verify',{'token':token}).json['approval_required']);self.assertEqual(self.login(name).status_code,200)
    def test_resend_expiry_replay_and_rate_limit(self):
        name,old=self.signup()
        self.post('resend',{'username':name,'password':'wrong'});self.assertEqual(self.token(),old)
        self.post('resend',{'username':name,'password':'Synthetic-password-2026'});new=self.token();self.assertNotEqual(new,old)
        self.assertEqual(self.post('verify',{'token':old}).status_code,400)
        with sqlite3.connect(self.path) as c:c.execute('UPDATE email_verifications SET expires=0 WHERE username=?',(name,))
        self.assertEqual(self.post('verify',{'token':new}).status_code,400)
        for _ in range(3):self.post('resend',{'username':'missing','password':'unknown'})
        self.assertEqual(self.post('resend',{'username':name,'password':'wrong'}).status_code,429)
    def test_disabled_config_invalid_email_and_host_header(self):
        with patch.dict(os.environ,{'THANA_EMAIL_ENABLED':'0'}):
            self.assertFalse(self.c.get('/api/platform/email/status').json['enabled']);self.assertEqual(self.post('register',{}).status_code,503)
        for base in ('http://learning.example.test','https://user:secret@example.test','https://example.test/path','https://example.test?x=1','https://example.test:999999','https://example.test/a\nb'):
            self.assertIsNone(configuration({**ENV,'THANA_PUBLIC_URL':base}))
        for address in ('bad','a\nb@example.test','.abc@example.test','ab..cd@example.test'):
            self.assertEqual(self.post('register',{'username':self.prefix,'name':'Fixture','email':address,'password':'Synthetic-password-2026'}).status_code,400)
        name,token=self.signup()
        self.assertEqual(self.post('register',{'username':name+'_duplicate','name':'Fixture','email':name.upper()+'@EXAMPLE.TEST','password':'Synthetic-password-2026'}).status_code,400)
        with sqlite3.connect(self.path) as c:body=c.execute("SELECT body FROM email_outbox WHERE id>? AND state='pending'",(self.last,)).fetchone()[0]
        self.assertIn(ENV['THANA_PUBLIC_URL']+'/email-account#verify=',body)
        self.assertNotIn('localhost',body)
        csrf=self.c.get('/api/csrf',headers={'Host':'attacker.example.test'}).json['token']
        r=self.c.post('/api/platform/email/register',json={'username':self.prefix+'_host','name':'Synthetic host test','email':self.prefix+'_host@example.test','password':'Synthetic-password-2026'},headers={'Host':'attacker.example.test','X-CSRF-Token':csrf});self.assertEqual(r.status_code,201)
        with sqlite3.connect(self.path) as c:body=c.execute("SELECT body FROM email_outbox WHERE id>? ORDER BY id DESC LIMIT 1",(self.last,)).fetchone()[0]
        self.assertIn(ENV['THANA_PUBLIC_URL'],body);self.assertNotIn('attacker.example.test',body)
    def test_worker_mock_delivery_retries_and_scrubs(self):
        self.signup()
        with patch('email_delivery.send_message') as send:
            result=deliver_pending(self.path);self.assertEqual(result['sent'],1);send.assert_called_once()
        with sqlite3.connect(self.path) as c:self.assertEqual(c.execute('SELECT recipient,body,state FROM email_outbox WHERE id>?',(self.last,)).fetchone(),('','','sent'))
        self.signup('_retry')
        with patch('email_delivery.send_message',side_effect=OSError('synthetic failure')):
            self.assertEqual(deliver_pending(self.path)['failed'],1)
        with sqlite3.connect(self.path) as c:
            state,available=c.execute("SELECT state,available FROM email_outbox WHERE state='pending' AND id>?",(self.last,)).fetchone();self.assertEqual(state,'pending');self.assertGreater(available,time.time())
            c.execute("UPDATE email_outbox SET expires=0 WHERE id>? AND state='pending'",(self.last,))
        with patch('email_delivery.send_message') as send:
            self.assertEqual(deliver_pending(self.path)['expired'],1);send.assert_not_called()
    def test_smtp_adapter_requires_verified_tls(self):
        cfg=configuration()
        with patch('email_delivery.smtplib.SMTP') as constructor:
            send_message(cfg,'synthetic@example.test','Synthetic verification content')
            smtp=constructor.return_value.__enter__.return_value
            context=smtp.starttls.call_args.kwargs['context'];self.assertTrue(context.check_hostname)
            self.assertEqual(smtp.method_calls[0][0],'ehlo');self.assertEqual(smtp.method_calls[1][0],'starttls');smtp.login.assert_called_once();smtp.send_message.assert_called_once()
        with patch('email_delivery.smtplib.SMTP_SSL') as constructor:
            send_message({**cfg,'port':465},'synthetic@example.test','Synthetic content')
            self.assertTrue(constructor.call_args.kwargs['context'].check_hostname)
            constructor.return_value.__enter__.return_value.send_message.assert_called_once()

    def test_verification_requires_registered_password_and_current_version(self):
        name,token=self.signup()
        self.assertEqual(self.post('verify',{'token':token,'password':'Wrong-password-2026'}).status_code,400)
        staff=self.prefix+'_staff';legacy.users[staff]={'username':staff,'name':'Synthetic staff','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=staff
        csrf=self.c.get('/api/csrf').json['token'];issued=self.c.post('/api/platform/admin/accounts/'+name+'/recovery',json={},headers={'X-CSRF-Token':csrf}).json['link'].split('=')[1]
        csrf=self.c.get('/api/csrf').json['token'];r=self.c.post('/api/platform/account/recover',json={'token':issued,'password':'Replacement-password-2026'},headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200)
        self.assertEqual(self.post('verify',{'token':token,'password':'Replacement-password-2026'}).status_code,400)

    def test_deleted_account_clears_verification_and_pending_email(self):
        name,token=self.signup()
        staff=self.prefix+'_staff';legacy.users[staff]={'username':staff,'name':'Synthetic staff','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=staff
        csrf=self.c.get('/api/csrf').json['token'];r=self.c.delete('/api/admin/students/'+name,headers={'X-CSRF-Token':csrf});self.assertEqual(r.status_code,200)
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM email_accounts WHERE username=?',(name,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM email_verifications WHERE username=?',(name,)).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT body,recipient FROM email_outbox WHERE id>?',(self.last,)).fetchone(),('',''))
        self.assertEqual(self.post('verify',{'token':token}).status_code,400)
