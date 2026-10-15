import unittest, secrets
from test_platform import legacy
class CoursesTests(unittest.TestCase):
 def setUp(self):
  self.c=legacy.app.test_client();self.username='teacher_'+secrets.token_hex(4)
  legacy.users[self.username]={'username':self.username,'name':'Test','role':'admin','status':'approved'}
  legacy._save(legacy.USERS_FILE,legacy.users)
  with self.c.session_transaction() as s:s['username']=self.username;s['role']='admin'
 def tearDown(self):legacy.users.pop(self.username,None)
 def post(self,path,body):
  token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=body,headers={'X-CSRF-Token':token})
 def test_draft_publish_revision_progress(self):
  course=self.post('/api/platform/admin/courses',{'title':'Test Lao','language':'lo'}).json['id']
  content={'title':'Greetings','order':1,'module':'Basics','blocks':[{'type':'text','value':'ສະບາຍດີ — 안녕하세요'}],'quiz':[{'question':'Hello?','options':['ສະບາຍດີ','ຂອບໃຈ'],'answer':0}]}
  r=self.post('/api/platform/admin/courses/'+course+'/lessons',content);self.assertEqual(r.status_code,201);lid=r.json['id']
  public='/api/platform/lessons/'+lid;save='/api/platform/admin/lessons/'+lid
  self.assertEqual(self.c.get(public).status_code,404)
  r=self.post(save,{'content':content,'revision':1,'action':'publish'});self.assertEqual(r.status_code,200)
  self.assertNotIn('answer',self.c.get(public).json['lesson']['quiz'][0])
  changed={**content,'title':'Draft changed'}
  self.assertEqual(self.post(save,{'content':changed,'revision':2}).status_code,200)
  self.assertEqual(self.c.get(public).json['lesson']['title'],'Greetings')
  self.assertEqual(self.post(save,{'content':changed,'revision':2}).status_code,409)
  r=self.post(public+'/complete',{'answers':{}});self.assertEqual(r.json['passed'],False)
  self.assertEqual(self.post(public+'/complete',{'answers':{'0':'bad'}}).status_code,400)
  for _ in range(2):self.assertTrue(self.post(public+'/complete',{'answers':{'0':0}}).json['passed'])
  p=self.c.get('/api/platform/learning-progress').json;self.assertEqual(p['xp'],20);self.assertEqual(p['streak'],1)
  self.assertEqual(self.post(save,{'content':changed,'revision':3,'action':'unpublish'}).status_code,200)
  self.assertEqual(self.c.get(public).status_code,404)
 def test_non_object_json(self):
  self.assertEqual(self.post('/api/platform/admin/courses',[]).status_code,400)
 def test_validation_and_permissions(self):
  c=self.post('/api/platform/admin/courses',{'title':'Test','language':'ko'}).json['id']
  bad={'title':'Unsafe','blocks':[{'type':'audio','value':'javascript:alert(1)'}]}
  self.assertEqual(self.post('/api/platform/admin/courses/'+c+'/lessons',bad).status_code,400)
  legacy.users[self.username]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.post('/api/platform/admin/courses',{'title':'Test','language':'lo'}).status_code,403)

 def test_sequential_access_enforced_server_side(self):
  course=self.post('/api/platform/admin/courses',{'title':'Sequential','language':'ko'}).json['id'];ids=[]
  for i in range(1,3):
   content={'title':'Lesson '+str(i),'order':i,'blocks':[{'type':'text','value':'Test'}],'quiz':[]}
   lid=self.post('/api/platform/admin/courses/'+course+'/lessons',content).json['id'];ids.append(lid)
   self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'})
  self.assertEqual(self.post('/api/platform/admin/courses/'+course+'/sequence',{'sequential':True}).status_code,200)
  legacy.users[self.username]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get('/api/platform/lessons/'+ids[1]).status_code,403)
  catalog=next(c for c in self.c.get('/api/platform/courses').json['courses'] if c['id']==course)
  self.assertEqual([l['unlocked'] for l in catalog['lessons']],[True,False])
  self.assertEqual(self.post('/api/platform/lessons/'+ids[1]+'/complete',{'answers':{}}).status_code,403)
  self.assertTrue(self.post('/api/platform/lessons/'+ids[0]+'/complete',{'answers':{}}).json['passed'])
  self.assertEqual(self.c.get('/api/platform/lessons/'+ids[1]).status_code,200)
  catalog=next(c for c in self.c.get('/api/platform/courses').json['courses'] if c['id']==course)
  self.assertEqual([l['unlocked'] for l in catalog['lessons']],[True,True])
 def test_mixed_quiz_types_through_api(self):
  course=self.post('/api/platform/admin/courses',{'title':'Mixed','language':'lo'}).json['id']
  content={'title':'Mixed','blocks':[{'type':'text','value':'Test'}],'quiz':[{'type':'blank','question':'Hello','accepted':['ສະບາຍດີ']},{'type':'ordering','question':'Order','options':['b','a'],'answer':[1,0]},{'type':'matching','question':'Match','pairs':[{'left':'a','right':'A'},{'left':'b','right':'B'}]}]}
  lid=self.post('/api/platform/admin/courses/'+course+'/lessons',content).json['id'];self.post('/api/platform/admin/lessons/'+lid,{'content':content,'revision':1,'action':'publish'})
  data=self.c.get('/api/platform/lessons/'+lid).json['lesson']['quiz'];self.assertNotIn('accepted',data[0]);self.assertNotIn('pairs',data[2])
  r=self.post('/api/platform/lessons/'+lid+'/complete',{'answers':{'0':'ສະບາຍດີ','1':[1,0],'2':['A','B']}})
  self.assertEqual(r.status_code,200);self.assertEqual(r.json['score'],100)
 def test_admin_course_settings_reflect_saved_values(self):
  course=self.post('/api/platform/admin/courses',{'title':'Settings','language':'lo'}).json['id']
  def settings():return next(c for c in self.c.get('/api/platform/admin/courses').json['courses'] if c['id']==course)
  self.assertFalse(settings()['premium']);self.assertFalse(settings()['sequential'])
  self.assertEqual(self.post('/api/platform/admin/courses/'+course+'/premium',{'premium':True}).status_code,200)
  self.assertEqual(self.post('/api/platform/admin/courses/'+course+'/sequence',{'sequential':True}).status_code,200)
  self.assertTrue(settings()['premium']);self.assertTrue(settings()['sequential'])
  self.post('/api/platform/admin/courses/'+course+'/premium',{'premium':False})
  self.post('/api/platform/admin/courses/'+course+'/sequence',{'sequential':False})
  self.assertFalse(settings()['premium']);self.assertFalse(settings()['sequential'])
 def test_history_private_and_restore_as_new_draft(self):
  course=self.post('/api/platform/admin/courses',{'title':'History','language':'lo'}).json['id']
  original={'title':'Original','blocks':[{'type':'text','value':'Original content'}],'quiz':[]}
  lid=self.post('/api/platform/admin/courses/'+course+'/lessons',original).json['id']
  endpoint='/api/platform/admin/lessons/'+lid
  self.post(endpoint,{'content':original,'revision':1,'action':'publish'})
  changed={**original,'title':'Changed'}
  self.post(endpoint,{'content':changed,'revision':2,'action':'publish'})
  rows=self.c.get(endpoint+'/revisions').json['revisions'];self.assertEqual([r['revision'] for r in rows],[3,2,1])
  restored=self.c.get(endpoint+'/revisions/1').json['content'];self.assertEqual(restored,original)
  self.assertEqual(self.post(endpoint,{'content':restored,'revision':3,'action':'save'}).status_code,200)
  self.assertEqual(self.c.get('/api/platform/lessons/'+lid).json['lesson']['title'],'Changed')
  self.assertEqual(self.c.get(endpoint+'/revisions/999').status_code,404)
  legacy.users[self.username]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
  self.assertEqual(self.c.get(endpoint+'/revisions').status_code,403)
  self.assertEqual(self.c.get(endpoint+'/revisions/1').status_code,403)
