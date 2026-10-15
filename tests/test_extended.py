import io,secrets,sqlite3,time,unittest
from test_platform import legacy
from PIL import Image
class ExtendedTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='extended_'+secrets.token_hex(5);legacy.users=legacy._load(legacy.USERS_FILE,{})
  legacy.users[self.name]={'username':self.name,'name':'Test','role':'admin','status':'approved','pw':legacy.hash_pw('test-password-123')};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name;s['role']='admin'
 def post(self,path,d):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=d,headers={'X-CSRF-Token':token})
 def role(self,role):
  legacy.users=legacy._load(legacy.USERS_FILE,{});legacy.users[self.name]['role']=role;legacy._save(legacy.USERS_FILE,legacy.users)
 def test_recovery_token_is_single_use(self):
  r=self.post('/api/platform/admin/accounts/'+self.name+'/recovery',{});self.assertEqual(r.status_code,200);token=r.json['link'].split('=')[1]
  r=self.post('/api/platform/account/recover',{'token':token,'password':'replacement-123'});self.assertEqual(r.status_code,200)
  self.assertEqual(self.post('/api/platform/account/recover',{'token':token,'password':'replacement-456'}).status_code,400)
  self.assertEqual(self.c.get('/api/platform/account').status_code,401)
 def test_password_change_invalidates_other_sessions(self):
  other=legacy.app.test_client()
  with other.session_transaction() as s:s['username']=self.name;s['role']='admin'
  self.assertEqual(self.post('/api/platform/account/password',{'current':'wrong','password':'replacement-123'}).status_code,400)
  self.assertEqual(self.post('/api/platform/account/password',{'current':'test-password-123','password':'replacement-123'}).status_code,200)
  self.assertEqual(other.get('/api/lessons').status_code,401)
 def test_teacher_has_content_only(self):
  self.role('teacher')
  self.assertEqual(self.c.get('/api/platform/management').status_code,200)
  self.assertEqual(self.post('/api/platform/admin/courses',{'title':'Teacher course','language':'lo'}).status_code,201)
  self.assertEqual(self.c.get('/api/platform/admin/accounts').status_code,403)
  self.assertEqual(self.c.get('/api/platform/admin/payments').status_code,403)
 def test_spaced_review_cannot_be_repeated_early(self):
  word=self.post('/api/platform/admin/vocabulary',{'ko':'word'+secrets.token_hex(3),'lo':'ຄຳ','published':True}).json['id']
  self.assertEqual(self.post('/api/platform/review/'+word,{'grade':'good'}).status_code,200)
  self.assertEqual(self.post('/api/platform/review/'+word,{'grade':'easy'}).status_code,409)
  self.assertNotIn(word,[w['id'] for w in self.c.get('/api/platform/review').json['words']])
 def test_payment_approval_grants_access_once(self):
  self.assertEqual(self.post('/api/platform/admin/membership',{'amount':1000,'currency':'LAK','days':30,'instructions':'Test only','enabled':True}).status_code,200)
  cid=self.post('/api/platform/admin/courses',{'title':'Premium test','language':'lo'}).json['id'];content={'title':'Test','blocks':[{'type':'text','value':'Test'}],'quiz':[]}
  lid=self.post('/api/platform/admin/courses/'+cid+'/lessons',content).json['id'];self.post('/api/platform/admin/lessons/'+lid,{'revision':1,'content':content,'action':'publish'});self.post('/api/platform/admin/courses/'+cid+'/premium',{'premium':True})
  self.role('student');self.assertEqual(self.c.get('/api/platform/lessons/'+lid).status_code,403)
  buf=io.BytesIO();Image.new('RGB',(2,2)).save(buf,format='PNG');token=self.c.get('/api/csrf').json['token']
  r=self.c.post('/api/platform/membership/request',data={'file':(io.BytesIO(buf.getvalue()),'proof.png')},headers={'X-CSRF-Token':token});self.assertEqual(r.status_code,201);aid=r.json['id']
  self.role('admin');self.assertEqual(self.post('/api/platform/admin/payments/'+aid,{'status':'approved','note':'Test'}).status_code,200)
  self.assertEqual(self.post('/api/platform/admin/payments/'+aid,{'status':'approved'}).status_code,409)
  self.role('student');self.assertEqual(self.c.get('/api/platform/lessons/'+lid).status_code,200)
