import json,os,secrets,sqlite3,unittest
from test_platform import legacy

class ReleaseWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='release_'+secrets.token_hex(4)
  legacy.users[self.name]={'username':self.name,'name':'Synthetic release user','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name
 def post(self,path,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=body,headers={'X-CSRF-Token':token})
 def test_admin_entry_roles(self):
  self.assertEqual(self.c.get('/admin').location,'/management')
  self.assertEqual(self.c.get('/legacy-admin').status_code,200)
  legacy.users[self.name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get('/admin').location,'/management');self.assertEqual(self.c.get('/legacy-admin').status_code,403)
  legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get('/admin').status_code,200);self.assertEqual(self.c.get('/legacy-admin').status_code,403)
 def test_retry_snapshot_and_ownership(self):
  attempt=self.post('/api/platform/practice',{'category':'blank'}).json;aid=attempt['id'];path='/api/platform/practice/'+aid
  self.assertEqual(self.post(path+'/retry',{}).status_code,409)
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
   original=json.loads(c.execute('SELECT questions FROM snapshots WHERE attempt=?',(aid,)).fetchone()[0])
  answers={str(q['id']):q['answer'] for q in original};wrong=original[0];answers[str(wrong['id'])]=1 if wrong['answer']!=1 else 2
  result=self.post(path,{'answers':answers}).json
  # Changing the editable bank cannot change the original retry snapshot.
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?)',(wrong['id'],answers[str(wrong['id'])],1,self.name,0))
  retry=self.post(path+'/retry',{}).json
  self.assertEqual([q['id'] for q in retry['questions']],[wrong['id']]);self.assertNotIn('answer',retry['questions'][0])
  self.assertNotEqual(retry['id'],aid)
  self.assertEqual(self.post('/api/platform/practice/'+retry['id'],{'answers':{str(wrong['id']):wrong['answer']}}).json['score'],1)
  self.assertEqual(self.post(path,{'answers':{}}).json,result)
  other='other_'+secrets.token_hex(4);legacy.users[other]={'username':other,'name':'Other','role':'student','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=other
  self.assertEqual(self.post(path+'/retry',{}).status_code,404)
  with self.c.session_transaction() as s:s.clear()
  self.assertEqual(self.post(path+'/retry',{}).status_code,401)
 def test_perfect_attempt_has_no_retry(self):
  aid=self.post('/api/platform/practice',{'category':'qa'}).json['id']
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:qs=json.loads(c.execute('SELECT questions FROM snapshots WHERE attempt=?',(aid,)).fetchone()[0])
  self.post('/api/platform/practice/'+aid,{'answers':{str(q['id']):q['answer'] for q in qs}})
  self.assertEqual(self.post('/api/platform/practice/'+aid+'/retry',{}).status_code,409)
 def test_reading_retry_preserves_passage_group(self):
  aid=self.post('/api/platform/practice',{'category':'reading'}).json['id']
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:qs=json.loads(c.execute('SELECT questions FROM snapshots WHERE attempt=?',(aid,)).fetchone()[0])
  answers={str(q['id']):q['answer'] for q in qs};q=qs[0];answers.pop(str(q['id']))
  self.post('/api/platform/practice/'+aid,{'answers':answers})
  retry=self.post('/api/platform/practice/'+aid+'/retry',{}).json
  expected=[x['id'] for x in qs if x['source'].split('-')[0]==q['source'].split('-')[0]]
  self.assertEqual([x['id'] for x in retry['questions']],expected)
 def test_publish_requires_public_library_asset(self):
  import io
  from PIL import Image
  raw=io.BytesIO();Image.new('RGB',(8,8),'red').save(raw,format='PNG');raw.seek(0)
  token=self.c.get('/api/csrf').json['token']
  asset=self.c.post('/api/platform/admin/media',data={'file':(raw,'sample.png'),'title':'Synthetic picture'},headers={'X-CSRF-Token':token}).json
  cid=self.post('/api/platform/admin/courses',{'title':'Media course','language':'lo'}).json['id']
  content={'title':'Picture','blocks':[{'type':'image','value':asset['url']}],'quiz':[]}
  lid=self.post('/api/platform/admin/courses/'+cid+'/lessons',content).json['id'];path='/api/platform/admin/lessons/'+lid
  self.assertEqual(self.post(path,{'content':content,'revision':1,'action':'publish'}).status_code,400)
  self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
  self.assertEqual(self.post(path,{'content':content,'revision':1,'action':'publish'}).status_code,200)
