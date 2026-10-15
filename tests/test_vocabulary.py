import io,secrets,unittest,wave
from test_platform import legacy
class VocabularyTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='vocab_'+secrets.token_hex(4);legacy.users[self.name]={'username':self.name,'name':'Test','role':'admin','status':'approved'}
  legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name;s['role']='admin'
 def tearDown(self):legacy.users.pop(self.name,None)
 def post(self,url,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(url,json=body,headers={'X-CSRF-Token':token})
 def test_import_preview_duplicates_and_drafts(self):
  suffix=secrets.token_hex(4);csv='ko,lo,category\n한국'+suffix+',ລາວ'+suffix+',test\n한국'+suffix+',ລາວ'+suffix+',test\n'
  path='/api/platform/admin/vocabulary/import'
  preview=self.post(path,{'csv':csv}).json;self.assertEqual(preview['ready'],1);self.assertEqual(preview['duplicates'],[3]);self.assertEqual(preview['added'],0)
  self.assertEqual(self.c.get('/api/platform/vocabulary?q='+suffix).json['words'],[])
  self.assertEqual(self.post(path,{'csv':csv,'commit':True}).json['added'],1)
  self.assertEqual(self.post(path,{'csv':csv,'commit':True}).json['added'],0)
  self.assertEqual(self.c.get('/api/platform/vocabulary?q='+suffix).json['words'],[])
  self.assertEqual(self.post(path,{'csv':'ko,lo\nvalid,\n','commit':True}).status_code,400)
 def test_audio_visibility_and_validation(self):
  r=self.post('/api/platform/admin/vocabulary',{'ko':'test'+secrets.token_hex(4),'lo':'ທົດລອງ'});wid=r.json['id'];path='/api/platform/admin/vocabulary/'+wid+'/audio/lo';token=self.c.get('/api/csrf').json['token']
  self.assertEqual(self.c.post(path,data={'file':(io.BytesIO(b'not audio'),'test.wav')},headers={'X-CSRF-Token':token}).status_code,400)
  buf=io.BytesIO()
  with wave.open(buf,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*80)
  r=self.c.post(path,data={'file':(io.BytesIO(buf.getvalue()),'test.wav')},headers={'X-CSRF-Token':token});self.assertEqual(r.status_code,200)
  url=r.json['url'];anonymous=legacy.app.test_client();self.assertEqual(anonymous.get(url).status_code,404);response=self.c.get(url);self.assertEqual(response.status_code,200);response.close()
  word=next(w for w in self.c.get('/api/platform/admin/vocabulary').json['words'] if w['id']==wid);word['published']=True
  self.assertEqual(self.post('/api/platform/admin/vocabulary',word).status_code,200);response=anonymous.get(url);self.assertEqual(response.status_code,200);response.close()
 def test_admin_required(self):
  legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users);self.assertEqual(self.post('/api/platform/admin/vocabulary',{'ko':'test','lo':'test'}).status_code,403)
 def test_saved_words_private_and_review_scope(self):
  wid=self.post('/api/platform/admin/vocabulary',{'ko':'save'+secrets.token_hex(5),'lo':'ບັນທຶກ','published':True}).json['id']
  path='/api/platform/saved-words/'+wid
  self.assertEqual(self.post(path,{'saved':True}).status_code,200)
  self.assertEqual(self.post(path,{'saved':True}).status_code,200)
  self.assertEqual(self.c.get('/api/platform/saved-words').json['ids'],[wid])
  self.assertEqual([w['id'] for w in self.c.get('/api/platform/vocabulary?scope=saved').json['words']],[wid])
  self.assertEqual(legacy.app.test_client().get('/api/platform/vocabulary?scope=saved').status_code,401)
  self.assertEqual([w['id'] for w in self.c.get('/api/platform/review?scope=saved').json['words']],[wid])
  other=legacy.app.test_client()
  self.assertEqual(other.get('/api/platform/saved-words').status_code,401)
  with other.session_transaction() as s:s['username']='not_an_account'
  self.assertEqual(other.get('/api/platform/saved-words').status_code,401)
  self.assertEqual(self.post('/api/platform/review/'+wid,{'grade':'good'}).status_code,200)
  self.assertEqual(self.c.get('/api/platform/review?scope=saved').json['total'],0)
  self.assertEqual(self.post(path,{'saved':False}).status_code,200)
  self.assertEqual(self.c.get('/api/platform/saved-words').json['ids'],[])
  self.post(path,{'saved':True})
  self.assertEqual(self.c.get('/api/platform/review?scope=saved').json['total'],0)
  self.assertEqual(self.post(path,{'saved':'true'}).status_code,400)
  self.assertEqual(self.c.get('/api/platform/review?scope=invalid').status_code,400)
  draft=self.post('/api/platform/admin/vocabulary',{'ko':'draft'+secrets.token_hex(5),'lo':'ຮ່າງ'}).json['id']
  self.assertEqual(self.post('/api/platform/saved-words/'+draft,{'saved':True}).status_code,404)
