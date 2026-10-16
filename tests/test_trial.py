import copy,secrets,unittest
from test_platform import legacy

class TrialTests(unittest.TestCase):
    def setUp(self):
        self.old=copy.deepcopy(legacy.lessons);self.name='trial_'+secrets.token_hex(4)
        self.first={'id':'synthetic_trial_first','order':1,'title_lo':'ທົດລອງ','title_ko':'체험','description':'Synthetic lesson','videos':[{'id':'public_video','title':'Public video','locked':False,'youtube_id':'abcdefghijk'},{'id':'locked_video','title':'Locked video','locked':True,'youtube_id':'12345678901'}],'homework':[{'id':'writing','question':'Write something','answer':'Do not disclose'}],'quiz':[{'id':'first_q','question':'Pick first','options':['first','second'],'answer':0}],'exam':[{'id':'first_exam','question':'Pick second','options':['first','second'],'answer':1}]}
        self.second={**copy.deepcopy(self.first),'id':'synthetic_trial_second','order':2,'quiz':[{'id':'second_secret','question':'Later question','options':['a','b'],'answer':1}]}
        legacy.lessons=[self.first,self.second];legacy._save(legacy.LESSONS_FILE,legacy.lessons)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic student','role':'student','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client();self.progress=copy.deepcopy(legacy.progress)
    def tearDown(self):
        legacy.lessons=self.old;legacy._save(legacy.LESSONS_FILE,legacy.lessons);legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)
    def post(self,body):return self.c.post('/api/platform/trial/grade',json=body,headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})
    def payload(self,**overrides):return {'lesson':self.first['id'],'section':'quiz','answers':{'first_q':0},**overrides}

    def test_full_first_lesson_public_and_locked_media_preserved(self):
        self.assertEqual(self.c.get('/try-lesson').status_code,200)
        response=self.c.get('/api/platform/trial?lesson='+self.second['id']);self.assertEqual(response.status_code,200)
        data=response.json['lesson'];self.assertEqual(data['id'],self.first['id']);self.assertEqual(len(data['quiz']),1);self.assertEqual(len(data['exam']),1);self.assertEqual(len(data['homework']),1)
        for section in ('quiz','exam','homework'):
            for q in data[section]:self.assertNotIn('answer',q)
        self.assertTrue(data['videos'][0]['playable']);self.assertFalse(data['videos'][1]['playable']);self.assertNotIn('embed_url',data['videos'][1]);self.assertNotIn('youtube_id',data['videos'][1])
        self.assertNotIn('second_secret',response.get_data(as_text=True));self.assertEqual(legacy.progress,self.progress)

    def test_guest_and_signed_in_grading_never_save_progress(self):
        r=self.post(self.payload());self.assertEqual(r.status_code,200);self.assertEqual(r.json['score'],100);self.assertFalse(r.json['saved'])
        self.assertEqual(self.post(self.payload(section='exam',answers={'first_exam':1})).json['score'],100)
        with self.c.session_transaction() as s:s['username']=self.name
        self.assertEqual(self.post(self.payload()).json['score'],100)
        self.assertEqual(legacy.progress,self.progress)
        self.assertEqual(self.c.get('/api/platform/learning-progress').json['xp'],0)

    def test_other_lesson_questions_and_malformed_choices_rejected(self):
        self.assertEqual(self.post(self.payload(lesson=self.second['id'])).status_code,409)
        for bad in ([],self.payload(section='homework'),self.payload(answers=[]),self.payload(answers={'second_secret':1}),self.payload(answers={'first_q':True}),self.payload(answers={'first_q':2}),{**self.payload(),'owner':'spoof'}):self.assertEqual(self.post(bad).status_code,400)
        self.assertEqual(self.post(self.payload(answers={})).json['score'],0)
        self.assertEqual(legacy.progress,self.progress)

    def test_empty_runtime_and_first_lesson_change(self):
        legacy.lessons=[self.second];legacy._save(legacy.LESSONS_FILE,legacy.lessons)
        self.assertEqual(self.post(self.payload()).status_code,409)
        legacy.lessons=[];legacy._save(legacy.LESSONS_FILE,legacy.lessons)
        self.assertEqual(self.c.get('/api/platform/trial').status_code,404);self.assertEqual(self.post(self.payload()).status_code,404)
