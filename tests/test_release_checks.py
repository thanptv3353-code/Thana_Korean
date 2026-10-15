import unittest,hashlib,secrets
from test_platform import legacy
class ReleaseChecks(unittest.TestCase):
 def test_old_and_new_password_hashes(self):
  pw='synthetic-password';salt='synthetic-salt';old=salt+'$'+hashlib.pbkdf2_hmac('sha256',pw.encode(),salt.encode(),100000).hex()
  self.assertTrue(legacy.check_pw(pw,old));new=legacy.hash_pw(pw);self.assertTrue(new.startswith('pbkdf2_sha256$600000$'));self.assertTrue(legacy.check_pw(pw,new));self.assertFalse(legacy.check_pw('wrong',new))
 def test_login_rate_limit(self):
  c=legacy.app.test_client();username='not_present_'+secrets.token_hex(5)
  for i in range(11):
   token=c.get('/api/csrf').json['token'];r=c.post('/api/login',json={'username':username,'password':'bad'},headers={'X-CSRF-Token':token})
   self.assertEqual(r.status_code,401 if i<10 else 429)
 def test_health_and_installable_shell(self):
  c=legacy.app.test_client();self.assertEqual(c.get('/health').json['status'],'ok')
  response=c.get('/service-worker.js');self.assertEqual(response.status_code,200);response.close()
  response=c.get('/static/manifest.webmanifest');self.assertEqual(response.status_code,200);response.close()
