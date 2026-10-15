import io,os,secrets,sqlite3,time,unittest,wave
from unittest.mock import patch
from test_platform import legacy
class TtsTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.name='tts_'+secrets.token_hex(4)
  legacy.users[self.name]={'username':self.name,'name':'Synthetic teacher','role':'teacher','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.name
  self.env={'THANA_TTS_ENABLED':'1','AZURE_SPEECH_KEY':'synthetic-key','AZURE_SPEECH_REGION':'southeastasia'}
 def post(self,path,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=body,headers={'X-CSRF-Token':token})
 def wav(self):
  raw=io.BytesIO()
  with wave.open(raw,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\0\0'*2400)
  return raw.getvalue()
 def payload(self):return {'text':'안녕하세요 <break/> & '+secrets.token_hex(5),'voice':'ko-KR-SunHiNeural','title':'Synthetic AI','consent':True}
 def test_generated_draft_review_publish_cache_and_escaped_text(self):
  body=self.payload()
  with patch.dict(os.environ,self.env),patch('tts_routes.urllib.request.urlopen',return_value=io.BytesIO(self.wav())) as send:
   r=self.post('/api/platform/admin/tts',body);self.assertEqual(r.status_code,201);asset=r.json
   self.assertIn(b'&lt;break/&gt; &amp;',send.call_args[0][0].data)
   self.assertEqual(send.call_args[0][0].full_url,'https://southeastasia.tts.speech.microsoft.com/cognitiveservices/v1')
   cached=self.post('/api/platform/admin/tts',body);self.assertTrue(cached.json['cached']);self.assertEqual(cached.json['id'],asset['id']);self.assertEqual(send.call_count,1)
  anon=legacy.app.test_client();self.assertEqual(anon.get(asset['url']).status_code,404)
  self.assertEqual(self.post('/api/platform/admin/media/'+asset['id'],{'published':True}).status_code,400)
  self.assertEqual(self.post('/api/platform/admin/tts/'+asset['id']+'/review',{'reviewed':True}).status_code,200)
  self.assertEqual(self.post('/api/platform/admin/media/'+asset['id'],{'published':True}).status_code,200)
  response=anon.get(asset['url']);self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'audio/wav');response.close()
  cid=self.post('/api/platform/admin/courses',{'title':'AI voice lesson','language':'ko'}).json['id']
  content={'title':'Listen','blocks':[{'type':'audio','value':asset['url']}],'quiz':[]}
  lid=self.post('/api/platform/admin/courses/'+cid+'/lessons',content).json['id']
  self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'})
  self.assertTrue(anon.get('/api/platform/lessons/'+lid).json['lesson']['blocks'][0]['ai_generated'])
 def test_disabled_permissions_validation_and_bad_audio(self):
  body=self.payload()
  with patch.dict(os.environ,{'THANA_TTS_ENABLED':'0'}):self.assertEqual(self.post('/api/platform/admin/tts',body).status_code,503)
  with patch.dict(os.environ,self.env),patch('tts_routes.urllib.request.urlopen',return_value=io.BytesIO(b'not-wav')) as send:
   self.assertEqual(self.post('/api/platform/admin/tts',{**body,'consent':False}).status_code,400)
   self.assertEqual(self.post('/api/platform/admin/tts',{**body,'voice':'arbitrary'}).status_code,400)
   self.assertEqual(self.post('/api/platform/admin/tts',{**body,'text':'x'*1001}).status_code,400)
   self.assertEqual(self.post('/api/platform/admin/tts',{**body,'voice':{}}).status_code,400)
   self.assertEqual(send.call_count,0)
   self.assertEqual(self.post('/api/platform/admin/tts',body).status_code,502)
  legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get('/api/platform/admin/tts/status').status_code,403)
  self.assertEqual(self.post('/api/platform/admin/tts',body).status_code,403)
 def test_daily_limit(self):
  with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO tts_usage VALUES (?,?,?)',(self.name,time.strftime('%Y-%m-%d',time.gmtime()),20))
  with patch.dict(os.environ,self.env),patch('tts_routes.urllib.request.urlopen') as send:
   self.assertEqual(self.post('/api/platform/admin/tts',self.payload()).status_code,429);send.assert_not_called()
