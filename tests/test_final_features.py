import io,json,secrets,unittest,wave,os
from unittest.mock import patch
from PIL import Image
from test_platform import legacy
class FinalFeatureTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='final_'+secrets.token_hex(4);legacy.users=legacy._load(legacy.USERS_FILE,{})
  legacy.users[self.name]={'username':self.name,'name':'Test','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name;s['role']='admin'
 def post(self,url,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(url,json=body,headers={'X-CSRF-Token':token})
 def test_moderation_keeps_pending_private(self):
  r=self.post('/api/platform/community',{'text':'Test '+secrets.token_hex(8),'language':'lo'});self.assertEqual(r.status_code,201);pid=r.json['id']
  anon=legacy.app.test_client();self.assertNotIn(pid,[p['id'] for p in anon.get('/api/platform/community').json['posts']])
  self.assertEqual(self.post('/api/platform/admin/community/'+pid,{'status':'approved'}).status_code,200)
  self.assertIn(pid,[p['id'] for p in anon.get('/api/platform/community').json['posts']])
 def test_media_draft_and_publish(self):
  b=io.BytesIO();Image.new('RGB',(3,3)).save(b,format='PNG');token=self.c.get('/api/csrf').json['token']
  r=self.c.post('/api/platform/admin/media',data={'file':(io.BytesIO(b.getvalue()),'test.png'),'title':'Test'},headers={'X-CSRF-Token':token});self.assertEqual(r.status_code,201)
  anon=legacy.app.test_client();self.assertEqual(anon.get(r.json['url']).status_code,404)
  self.assertEqual(self.post('/api/platform/admin/media/'+r.json['id'],{'published':True}).status_code,200)
  response=anon.get(r.json['url']);self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'image/jpeg');response.close()
 def test_question_archiving_preserves_source(self):
  q={'category':'blank','type':'text','stem_ko':'Test?','stem_lo':'ທົດລອງ','choices_ko':['A','B'],'choices_lo':['ກ','ຂ'],'answer':1,'verified':True,'active':True}
  r=self.post('/api/platform/admin/bank',q);self.assertEqual(r.status_code,200);qid=r.json['id']
  self.assertIn(qid,[q['id'] for q in self.c.get('/api/platform/admin/questions').json['questions']])
  self.assertEqual(self.post('/api/platform/admin/bank',{**q,'id':qid,'active':False}).status_code,200)
  self.assertNotIn(qid,[q['id'] for q in self.c.get('/api/platform/admin/questions').json['questions']])
 def test_tutor_optional_and_mocked_response(self):
  with patch.dict(os.environ,{'THANA_AI_ENABLED':'0'}):
   self.assertEqual(self.post('/api/platform/tutor',{'question':'안녕하세요','language':'lo','use_ai':True}).status_code,503)
   self.assertEqual(self.post('/api/platform/tutor',{'question':'안녕하세요','language':'lo','use_ai':False}).json['mode'],'dictionary')
  response={'output':[{'type':'message','content':[{'type':'output_text','text':'Test explanation'}]}]}
  with patch.dict(os.environ,{'THANA_AI_ENABLED':'1','OPENAI_API_KEY':'test-key','THANA_AI_MODEL':'test-model'}),patch('tutor_routes.urllib.request.urlopen',return_value=io.BytesIO(json.dumps(response).encode())) as send:
   r=self.post('/api/platform/tutor',{'question':'Test','language':'ko','use_ai':True});self.assertEqual(r.json['text'],'Test explanation');self.assertFalse(json.loads(send.call_args[0][0].data)['store'])
 def test_speech_does_not_invent_lao_scores(self):
  b=io.BytesIO()
  with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*1600)
  token=self.c.get('/api/csrf').json['token']
  with patch.dict(os.environ,{'THANA_SPEECH_ENABLED':'1','AZURE_SPEECH_KEY':'test-key','AZURE_SPEECH_RESOURCE':'test-resource'}),patch('speech_routes.urllib.request.urlopen',return_value=io.BytesIO(json.dumps({'NBest':[{'Display':'ສະບາຍດີ','AccuracyScore':99}]}).encode())):
   r=self.c.post('/api/platform/speech',data={'file':(io.BytesIO(b.getvalue()),'speech.wav'),'language':'lo-LA','reference':'ສະບາຍດີ','consent':'true'},headers={'X-CSRF-Token':token});self.assertEqual(r.status_code,200);self.assertEqual(r.json['scores'],{});self.assertFalse(r.json['assessment_available'])
