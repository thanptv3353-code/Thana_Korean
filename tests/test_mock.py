import json,os,secrets,sqlite3,unittest
from unittest.mock import patch
from test_platform import legacy
class MockTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='mock_'+secrets.token_hex(4)
  legacy.users[self.name]={'username':self.name,'name':'Test','role':'student','status':'approved'}
  legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name;s['role']='student'
 def tearDown(self):
  legacy.users.pop(self.name,None)
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('UPDATE mock_settings SET count=20,seconds=1200,verified_only=0 WHERE id=1')
 def post(self,url,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(url,json=body,headers={'X-CSRF-Token':token})
 def test_deadline_saved_answers_and_idempotency(self):
  with patch('mock_routes.now',return_value=1000):
   r=self.post('/api/platform/mock',{});self.assertEqual(r.status_code,201);aid=r.json['id'];base='/api/platform/mock/'+aid
   self.assertEqual(self.post('/api/platform/mock',{}).json['id'],aid)
   d=self.c.get(base).json;self.assertEqual(len(d['questions']),20);self.assertNotIn('answer',d['questions'][0])
   with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:bank=json.loads(c.execute('SELECT questions FROM mock_runs WHERE id=?',(aid,)).fetchone()[0])
   q=bank[0]
   self.assertEqual(self.post(base+'/answer',{'id':q['id'],'choice':q['answer']}).status_code,200)
   self.assertEqual(self.c.get(base).json['answers'][str(q['id'])],q['answer'])
  with patch('mock_routes.now',return_value=2201):
   r=self.post(base+'/answer',{'id':bank[1]['id'],'choice':bank[1]['answer']});self.assertEqual(r.status_code,409)
   result=r.json['result'];self.assertEqual(result['score'],1);self.assertEqual(result['total'],20)
   self.assertEqual(self.post(base+'/finish',{}).json['result'],result)
   self.assertEqual(self.c.get(base).json['result'],result)
 def test_ownership_and_permissions(self):
  aid=self.post('/api/platform/mock',{}).json['id']
  token=self.c.get('/api/csrf').json['token']
  other=legacy.app.test_client()
  self.assertEqual(other.get('/api/platform/mock/'+aid).status_code,401)
  other_name='mock_other_'+secrets.token_hex(4)
  legacy.users[other_name]={'username':other_name,'name':'Synthetic other user','role':'student','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=other_name;s['role']='student'
  self.assertEqual(self.c.get('/api/platform/mock/'+aid).status_code,404)
  with self.c.session_transaction() as s:s['username']=self.name;s['role']='student'
  self.assertEqual(self.post('/api/platform/admin/mock/settings',{'count':10,'seconds':60,'verified_only':False}).status_code,403)
 def test_verified_only_and_settings_validation(self):
  legacy.users[self.name]['role']='admin';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.post('/api/platform/admin/mock/settings',{'count':5,'seconds':60,'verified_only':True}).status_code,200)
  self.assertEqual(self.post('/api/platform/mock',{}).status_code,409)
  self.assertEqual(self.post('/api/platform/admin/mock/settings',{'count':-1,'seconds':60,'verified_only':True}).status_code,400)
