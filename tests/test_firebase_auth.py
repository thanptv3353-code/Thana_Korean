import os
import secrets
import sqlite3
import time
import unittest
from unittest.mock import patch,Mock
from test_platform import legacy
from firebase_auth_routes import COOKIE,PROJECT

class FirebaseAuthTests(unittest.TestCase):
    def setUp(self):
        self.username='firebase_'+secrets.token_hex(5);self.uid='uid_'+secrets.token_hex(5)
        legacy.users[self.username]=dict(username=self.username,name='Synthetic',role='student',status='approved',auth_version=1)
        legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('INSERT INTO firebase_account_bindings VALUES (?,?,1)',(self.uid,self.username));db.execute('DELETE FROM firebase_login_attempts')
        self.client=legacy.app.test_client();self.environment=patch.dict(os.environ,THANA_FIREBASE_AUTH_ENABLED='1');self.environment.start()
    def tearDown(self):
        self.environment.stop();legacy.users.pop(self.username,None);legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('DELETE FROM firebase_account_bindings WHERE uid=?',(self.uid,));db.execute('DELETE FROM firebase_login_attempts')
    def post(self,data,csrf=True,secure=True):
        base='https://localhost' if secure else 'http://localhost'
        headers={'X-CSRF-Token':self.client.get('/api/csrf',base_url=base).json['token']} if csrf else {}
        return self.client.post('/api/platform/auth/firebase',base_url=base,json=data,headers=headers)
    def claims(self):return dict(uid=self.uid,auth_time=time.time(),role='superadmin',email='untrusted@example.test')
    def test_bound_uid_session_uses_local_permissions_and_checks_revocation_each_request(self):
        with patch('firebase_auth_routes.verify_token',return_value=self.claims()),patch('firebase_auth_routes.issue_cookie',return_value='synthetic-cookie'),patch('firebase_auth_routes.verify_cookie',return_value=self.claims()) as verify:
            response=self.post({'id_token':'synthetic-token'});self.assertEqual(response.status_code,200);self.assertEqual(response.json['user']['role'],'student')
            header=next(h for h in response.headers.getlist('Set-Cookie') if COOKIE in h)
            for flag in ('Secure','HttpOnly','SameSite=Strict','Max-Age=300'):self.assertIn(flag,header)
            self.assertEqual(self.client.get('/api/me',base_url='https://localhost').json['user']['username'],self.username)
            self.assertEqual(verify.call_count,1)
            legacy.users[self.username]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.client.get('/api/me',base_url='https://localhost').json['user']['role'],'teacher')
            verify.side_effect=ValueError('revoked')
            self.assertEqual(self.client.get('/api/me',base_url='https://localhost').status_code,401)
            self.assertIsNone(self.client.get('/api/me',base_url='https://localhost').json['user'])
    def test_no_auto_link_or_provision_and_recent_auth_required(self):
        for claims in (dict(uid='unknown',email=self.username,auth_time=time.time()),dict(uid=self.uid,auth_time=time.time()-1000)):
            with patch('firebase_auth_routes.verify_token',return_value=claims),patch('firebase_auth_routes.issue_cookie') as issue:
                self.assertEqual(self.post({'id_token':'synthetic'}).status_code,401);issue.assert_not_called()
        legacy.users[self.username]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
        with patch('firebase_auth_routes.verify_token',return_value=self.claims()),patch('firebase_auth_routes.issue_cookie') as issue:
            self.assertEqual(self.post({'id_token':'synthetic'}).status_code,401);issue.assert_not_called()
    def test_disabled_https_csrf_shape_and_rate_limit(self):
        with patch.dict(os.environ,THANA_FIREBASE_AUTH_ENABLED='0'),patch('firebase_auth_routes.verify_token') as verify:
            self.assertEqual(self.post({'id_token':'x'}).status_code,503);verify.assert_not_called()
        self.assertEqual(self.post({'id_token':'x'},secure=False).status_code,400)
        self.assertEqual(self.post({'id_token':'x'},csrf=False).status_code,403)
        with patch('firebase_auth_routes.verify_token') as verify:
            for _ in range(10):self.assertEqual(self.post({'id_token':'x','role':'admin'}).status_code,400)
            self.assertEqual(self.post({'id_token':'x'}).status_code,429);verify.assert_not_called()
    def test_binding_removal_auth_version_and_feature_disable_invalidate_session(self):
        for change in ('binding','version','disabled'):
            self.client=legacy.app.test_client();legacy.users[self.username]['auth_version']=1;legacy._save(legacy.USERS_FILE,legacy.users)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('UPDATE firebase_account_bindings SET enabled=1 WHERE uid=?',(self.uid,));db.execute('DELETE FROM firebase_login_attempts')
            with patch('firebase_auth_routes.verify_token',return_value=self.claims()),patch('firebase_auth_routes.issue_cookie',return_value='synthetic-cookie'),patch('firebase_auth_routes.verify_cookie',return_value=self.claims()):
                self.assertEqual(self.post({'id_token':'x'}).status_code,200)
                if change=='binding':
                    with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('UPDATE firebase_account_bindings SET enabled=0 WHERE uid=?',(self.uid,))
                elif change=='version':legacy.users[self.username]['auth_version']=2;legacy._save(legacy.USERS_FILE,legacy.users)
                else:os.environ['THANA_FIREBASE_AUTH_ENABLED']='0'
                self.assertEqual(self.client.get('/api/me',base_url='https://localhost').status_code,401)
                os.environ['THANA_FIREBASE_AUTH_ENABLED']='1'
    def test_sdk_wrappers_use_expected_app_and_revocation_checks(self):
        from firebase_auth_routes import verify_token,verify_cookie,issue_cookie
        auth=Mock();app=object()
        with patch('firebase_auth_routes.sdk',return_value=(auth,app)):
            verify_token('id');verify_cookie('cookie');issue_cookie('id')
        auth.verify_id_token.assert_called_once_with('id',app=app,check_revoked=True)
        auth.verify_session_cookie.assert_called_once_with('cookie',app=app,check_revoked=True)
        self.assertEqual(auth.create_session_cookie.call_args.kwargs['expires_in'].total_seconds(),300)

    def test_public_config_never_exposes_unconfigured_or_secret_values(self):
        with patch.dict(os.environ,THANA_FIREBASE_WEB_API_KEY='private-not-a-web-key'):
            self.assertEqual(self.client.get('/api/platform/auth/firebase/config').json,dict(enabled=False,project=PROJECT))
        key='AIza'+'x'*35
        with patch.dict(os.environ,THANA_FIREBASE_WEB_API_KEY=key):
            self.assertEqual(self.client.get('/api/platform/auth/firebase/config').json,dict(enabled=True,project=PROJECT,api_key=key))
            with patch.dict(os.environ,THANA_FIREBASE_AUTH_ENABLED='0'):
                self.assertNotIn('api_key',self.client.get('/api/platform/auth/firebase/config').json)
