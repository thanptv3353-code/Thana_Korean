import json,os,secrets,sqlite3,time,unittest
from test_platform import legacy


class LearningAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.name='analysis_'+secrets.token_hex(5);self.other=self.name+'_other'
        for name in (self.name,self.other):legacy.users[name]={'username':name,'name':'Synthetic analysis learner','role':'student','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as s:s['username']=self.name
        self.ids=[]

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for aid in self.ids:
                c.execute('DELETE FROM snapshots WHERE attempt=?',(aid,));c.execute('DELETE FROM attempts WHERE id=?',(aid,));c.execute('DELETE FROM mock_runs WHERE id=?',(aid,))
        for name in (self.name,self.other):legacy.users.pop(name,None)
        legacy._save(legacy.USERS_FILE,legacy.users)

    def practice(self,questions,answers,finished=None,owner=None,snapshot=True):
        aid='synthetic_'+secrets.token_hex(8);self.ids.append(aid)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',(aid,owner or self.name,'qa',json.dumps([q['id'] for q in questions]),json.dumps(answers),time.time(),finished,0))
            if snapshot:c.execute('INSERT INTO snapshots VALUES (?,?)',(aid,json.dumps(questions)))

    def mock(self,finished,owner=None):
        aid='synthetic_'+secrets.token_hex(8);self.ids.append(aid)
        detail=[{'category':'qa','correct':True,'given':1,'verified':True},{'category':'qa','correct':False,'given':None,'verified':False}]
        result={'skill':'listening','detail':detail,'points':100,'max_points':200}
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('INSERT INTO mock_runs VALUES (?,?,?,?,?,?,?,?)',(aid,owner or self.name,'[]','{}',time.time()+60,finished,json.dumps(result),time.time()))

    def test_exposure_aggregation_and_snapshot_privacy(self):
        now=time.time();q=[{'id':901,'category':'qa','skill':'reading','answer':1,'verified':True,'stem_ko':'private reference text'},{'id':902,'category':'qa','answer':2,'verified':False}]
        self.practice(q,{'901':1},now);self.practice(q[:1],{'901':1},now)
        self.practice(q,{},None);self.practice(q,{},now-366*86400)
        self.practice(q,{},now,snapshot=False);self.practice(q,{},now,owner=self.other)
        self.mock(now);self.mock(None);self.mock(now,self.other)
        r=self.c.get('/api/platform/learning-analysis');self.assertEqual(r.status_code,200);self.assertEqual(r.headers['Cache-Control'],'no-store')
        d=r.json;self.assertEqual(d['attempts'],{'practice':2,'mock':1});self.assertEqual(d['missing_snapshots'],1)
        self.assertEqual((d['correct'],d['total']),(3,5))
        self.assertEqual([g['skill'] for g in d['groups']],['listening','reading'])
        reading=next(g for g in d['groups'] if g['mode']=='practice');self.assertEqual((reading['correct'],reading['total'],reading['unanswered'],reading['unverified'],reading['percent']),(2,3,1,1,66.7))
        self.assertNotIn('private reference text',r.get_data(as_text=True));self.assertNotIn('answer',d['groups'][0])
        with self.c.session_transaction() as s:s['username']=self.other
        other=self.c.get('/api/platform/learning-analysis?owner='+self.name).json
        self.assertEqual(other['attempts'],{'practice':1,'mock':1});self.assertEqual((other['correct'],other['total']),(1,4))

    def test_period_empty_and_access(self):
        self.practice([{'id':903,'category':'blank','answer':1,'verified':True}],{'903':1},time.time()-20*86400)
        self.assertEqual(self.c.get('/api/platform/learning-analysis?days=7').json['total'],0)
        self.assertEqual(self.c.get('/api/platform/learning-analysis?days=30').json['total'],1)
        for days in ('0','x','-1','100000','8'):
            self.assertEqual(self.c.get('/api/platform/learning-analysis?days='+days).status_code,400)
        legacy.users[self.name]['status']='rejected';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.c.get('/api/platform/learning-analysis').status_code,401)
        self.assertEqual(legacy.app.test_client().get('/api/platform/learning-analysis').status_code,401)
