import secrets
import unittest
from test_platform import legacy


class UsernameRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.c=legacy.app.test_client()
        self.username='signup_'+secrets.token_hex(5)
        self.body=dict(name='Synthetic Korean learner',username=self.username,password='Synthetic-registration-2026')

    def tearDown(self):
        legacy.users.pop(self.username,None)
        legacy._save(legacy.USERS_FILE,legacy.users)

    def post(self,path,body):
        return self.c.post(path,json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def test_registration_cannot_grant_roles_or_skip_approval(self):
        self.assertEqual(self.c.post('/api/register',json=self.body).status_code,403)
        response=self.post('/api/register',dict(self.body,role='superadmin',status='approved'))
        self.assertEqual(response.status_code,200)
        user=legacy.users[self.username]
        self.assertEqual((user['role'],user['status']),('student','pending'))
        self.assertNotEqual(user['pw'],self.body['password'])
        self.assertTrue(legacy.check_pw(self.body['password'],user['pw']))
        self.assertEqual(self.c.get('/api/platform/account').status_code,401)
        denied=self.post('/api/login',self.body)
        self.assertEqual(denied.status_code,403);self.assertIn('승인',denied.json['error'])
        self.assertEqual(self.post('/api/register',self.body).status_code,400)
        legacy.users[self.username]['status']='approved';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post('/api/login',self.body).status_code,200)
        self.assertEqual(self.c.get('/api/platform/account').json['role'],'student')
        self.assertEqual(self.c.get('/api/platform/admin/accounts').status_code,403)

    def test_invalid_payloads_and_field_boundaries_do_not_create_accounts(self):
        for body in [[],{},'bad',dict(self.body,name=' '),dict(self.body,name='x'*101),dict(self.body,password='short'),dict(self.body,password='x'*129),dict(self.body,username='bad name'),dict(self.body,username='x'*51),dict(self.body,password=123)]:
            self.assertEqual(self.post('/api/register',body).status_code,400)
        self.assertNotIn(self.username,legacy.users)
        for body in [[],{},'bad',dict(username=self.username,password=[]),dict(username=self.username,password='x'*129)]:
            self.assertEqual(self.post('/api/login',body).status_code,400)
