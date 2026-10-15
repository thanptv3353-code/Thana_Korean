import os, tempfile, unittest
_tmp=tempfile.TemporaryDirectory();os.environ['THANA_PLATFORM_DB']=os.path.join(_tmp.name,'test.sqlite3')
import shutil
from pathlib import Path
_testdata=Path(_tmp.name)/'data';_testdata.mkdir()
shutil.copyfile(Path(__file__).resolve().parents[1]/'data/lessons.json',_testdata/'lessons.json')
for name in ('users.json','progress.json'):(_testdata/name).write_text('{}')
os.environ['THANA_DATA_DIR']=str(_testdata)
import app as legacy
class PlatformTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();legacy.users=legacy._load(legacy.USERS_FILE,{})
  legacy.users['test_student']={'username':'test_student','name':'Test','role':'student','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
 def tearDown(self): legacy.users.pop('test_student',None)
 def post(self,url,**kwargs):
  token=self.c.get('/api/csrf').json['token']
  return self.c.post(url,headers={'X-CSRF-Token':token},**kwargs)
 def auth(self):
  with self.c.session_transaction() as s:s['username']='test_student';s['role']='student'
 def test_public(self):
  self.assertEqual(self.c.get('/').status_code,200)
  self.assertEqual(self.c.get('/learn').status_code,200)
  d=self.c.get('/api/platform/sample').json
  self.assertTrue(d['questions']);self.assertNotIn('answer',d['questions'][0])
 def test_auth_revocation(self):
  self.auth();legacy.users['test_student']['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get('/api/lessons').status_code,401)
  self.assertEqual(self.post('/api/platform/practice',json={'category':'blank'}).status_code,401)
 def test_practice(self):
  self.auth();r=self.post('/api/platform/practice',json={'category':'blank'});self.assertEqual(r.status_code,200);d=r.json
  self.assertNotIn('answer',d['questions'][0]);aid=d['id']
  self.assertEqual(self.post('/api/platform/practice/'+aid,json={'answers':{'wrong':1}}).status_code,400)
  result=self.post('/api/platform/practice/'+aid,json={'answers':{}}).json
  self.assertEqual(result['total'],10);self.assertEqual(result['score'],0)
  again=self.post('/api/platform/practice/'+aid,json={'answers':{str(q['id']):1 for q in d['questions']}}).json
  self.assertEqual(again['score'],0)
  self.assertEqual(len(self.c.get('/api/platform/history').json['attempts']),1)
  with self.c.session_transaction() as s:s.clear()
  self.assertEqual(self.post('/api/platform/practice/'+aid,json={'answers':{}}).status_code,401)
 def test_csrf(self):
  self.auth()
  self.assertEqual(self.c.post('/api/platform/practice',json={'category':'blank'}).status_code,403)
 def test_review_permissions(self):
  self.auth()
  self.assertEqual(self.c.get('/api/platform/admin/questions').status_code,403)
  with self.c.session_transaction() as s:s['role']='admin'
  self.assertEqual(self.c.get('/api/platform/admin/questions').status_code,403)
 def test_malformed_legacy_answer(self):
  score,_=legacy._grade([{'id':'q','answer':0}],{'q':'bad'});self.assertEqual(score,0)
if __name__=='__main__':unittest.main()
