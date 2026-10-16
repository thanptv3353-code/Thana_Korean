import io,json,os,secrets,sqlite3,time,unittest,wave
from unittest.mock import patch
from test_platform import legacy


class ListeningTests(unittest.TestCase):
    def setUp(self):
        self.c=legacy.app.test_client();self.name='listening_'+secrets.token_hex(4);self.ids=[];self.assets=[]
        legacy.users[self.name]={'username':self.name,'name':'Synthetic listening author','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=self.name
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.weights=c.execute("SELECT weights FROM mock_score_settings WHERE skill='listening'").fetchone()
            self.cfg=c.execute("SELECT count,seconds,verified_only FROM mock_skill_settings WHERE skill='listening'").fetchone()
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for qid in self.ids:c.execute('DELETE FROM eps_bank WHERE id=?',(qid,));c.execute('DELETE FROM reviews WHERE qid=?',(qid,))
            for asset in self.assets:c.execute('DELETE FROM generated_audio WHERE asset=?',(asset,));c.execute('DELETE FROM media_assets WHERE id=?',(asset,))
            c.execute("UPDATE mock_skill_settings SET count=?,seconds=?,verified_only=? WHERE skill='listening'",self.cfg)
            c.execute("DELETE FROM mock_score_settings WHERE skill='listening'")
            if self.weights:c.execute("INSERT INTO mock_score_settings VALUES ('listening',?)",self.weights)
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)
    def post(self,path,body):
        token=self.c.get('/api/csrf').json['token'];return self.c.post(path,json=body,headers={'X-CSRF-Token':token})
    def audio(self,published=True):
        raw=io.BytesIO()
        with wave.open(raw,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(b'\0\0'*1600)
        raw.seek(0);token=self.c.get('/api/csrf').json['token']
        r=self.c.post('/api/platform/admin/media',data={'file':(raw,'synthetic.wav'),'title':'Synthetic silence fixture'},headers={'X-CSRF-Token':token});self.assertEqual(r.status_code,201,r.json)
        asset=r.json;self.assets.append(asset['id'])
        if published:self.assertEqual(self.post('/api/platform/admin/media/'+asset['id'],{'published':True}).status_code,200)
        return asset
    def question(self,audio,**extra):
        q={'skill':'listening','audio':audio,'category':'qa','type':'text','stem_ko':'Synthetic listening prompt','stem_lo':'ຄຳຖາມທົດລອງ','choices_ko':['A','B'],'choices_lo':['A','B'],'answer':1,'verified':True,'source':secrets.token_hex(6),'explanation_ko':'Fixture explanation','difficulty':'beginner'};q.update(extra)
        r=self.post('/api/platform/admin/bank',q);self.assertEqual(r.status_code,200,r.json);q['id']=r.json['id'];self.ids.append(q['id']);return q
    def configure(self,count=5):
        r=self.post('/api/platform/admin/mock/settings',{'skill':'listening','count':count,'seconds':60,'verified_only':True});self.assertEqual(r.status_code,200,r.json)
    def test_activation_requires_public_audio(self):
        asset=self.audio(False);self.assertEqual(legacy.app.test_client().get(asset['url']).status_code,404);q=self.question(asset['url'],active=False)
        self.assertEqual(self.post('/api/platform/admin/bank',{**q,'active':True}).status_code,400)
        self.assertEqual(self.post('/api/platform/admin/bank',{**q,'active':True,'audio':''}).status_code,400)
        self.assertEqual(self.post('/api/platform/admin/bank',{**q,'audio':'https://example.com/sound.mp3'}).status_code,400)
        self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
        self.assertEqual(self.post('/api/platform/admin/bank',{**q,'active':True}).status_code,200)
        with legacy.app.test_client().get(asset['url']) as response:self.assertEqual(response.status_code,200)
        self.assertEqual(self.post('/api/platform/admin/bank',{**q,'skill':'invalid'}).status_code,400)
    def test_catalog_practice_retry_and_unpublished_audio(self):
        asset=self.audio();q=self.question(asset['url'])
        catalog=self.c.get('/api/platform/catalog?skill=listening').json
        self.assertEqual(catalog['skill'],'listening');self.assertEqual(sum(x['count'] for x in catalog['categories']),1)
        started=self.post('/api/platform/practice',{'category':'qa','skill':'listening'}).json
        self.assertEqual(started['skill'],'listening');self.assertEqual([x['id'] for x in started['questions']],[q['id']])
        public=started['questions'][0];self.assertEqual(public['audio'],asset['url']);self.assertNotIn('answer',public);self.assertNotIn('explanation_ko',public)
        reading=self.post('/api/platform/practice',{'category':'qa'}).json
        self.assertNotIn(q['id'],[x['id'] for x in reading['questions']])
        self.post('/api/platform/practice/'+started['id'],{'answers':{}})
        retry=self.post('/api/platform/practice/'+started['id']+'/retry',{}).json
        self.assertEqual(retry['skill'],'listening');self.assertEqual(retry['questions'][0]['audio'],asset['url'])
        history=self.c.get('/api/platform/history').json['attempts'];self.assertEqual(next(x for x in history if x['id']==started['id'])['skill'],'listening')
        self.post('/api/platform/admin/media/'+asset['id'],{'published':False})
        self.assertEqual(self.c.get('/api/platform/catalog?skill=listening').json['categories'],[])
        # Search directly because the full report is paginated.
        report=self.c.get('/api/platform/admin/content-readiness?q='+str(q['id'])).json['items']
        self.assertIn('listening_audio',next(x for x in report if x['id']==str(q['id']))['issues'])
        self.assertEqual(self.post('/api/platform/practice',{'category':'qa','skill':'listening'}).status_code,409)
        self.assertEqual(self.c.get('/api/platform/catalog?skill=invalid').status_code,400)
    def test_mock_modes_resume_snapshot_and_deadline(self):
        asset=self.audio();qs=[self.question(asset['url']) for _ in range(5)];self.configure()
        reading_cfg=self.c.get('/api/platform/mock/settings').json['settings']
        self.assertEqual(reading_cfg['count'],20)
        with patch('mock_routes.now',return_value=1000):
            started=self.post('/api/platform/mock',{'skill':'listening'});self.assertEqual(started.status_code,201,started.json)
            aid=started.json['id'];base='/api/platform/mock/'+aid
            state=self.c.get(base).json;self.assertEqual(state['skill'],'listening');self.assertEqual(state['remaining'],60)
            self.assertEqual(len(state['questions']),5);self.assertTrue(all('answer' not in q and 'explanation_ko' not in q for q in state['questions']))
            q=state['questions'][0];self.assertEqual(self.post(base+'/answer',{'id':q['id'],'choice':1}).status_code,200)
            self.assertEqual(self.c.get(base).json['answers'][str(q['id'])],1)
            reading=self.post('/api/platform/mock',{}).json;self.assertNotEqual(reading['id'],aid)
            self.assertEqual(self.c.get('/api/platform/mock/'+reading['id']).json['skill'],'reading')
            self.post('/api/platform/admin/media/'+asset['id'],{'published':False})
            # Resume must work from the stored run even if no new listening pool is available.
            resumed=self.post('/api/platform/mock',{'skill':'listening'}).json;self.assertEqual(resumed['id'],aid);self.assertTrue(resumed['resumed'])
        with patch('mock_routes.now',return_value=1061):
            expired=self.post(base+'/answer',{'id':q['id'],'choice':2});self.assertEqual(expired.status_code,409)
            result=expired.json['result'];self.assertEqual(result['skill'],'listening');self.assertEqual(result['score'],1)
            self.assertEqual(result['detail'][0]['question']['audio'],asset['url'])
            self.assertEqual(self.post(base+'/finish',{}).json['result'],result)
        with self.c.session_transaction() as s:s.clear()
        self.assertEqual(self.c.get(base).status_code,401)
    def test_complete_passage_selection_backtracks(self):
        asset=self.audio();prefix=secrets.token_hex(4)
        for group,size in enumerate((4,3,3)):
            for i in range(size):self.question(asset['url'],category='reading',source=prefix+str(group)+'-'+str(i))
        self.configure(count=6)
        with patch('mock_routes.random.shuffle',lambda chunks:None):
            r=self.post('/api/platform/mock',{'skill':'listening'})
        self.assertEqual(r.status_code,201,r.json)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:chosen=json.loads(c.execute('SELECT questions FROM mock_runs WHERE id=?',(r.json['id'],)).fetchone()[0])
        self.assertEqual(len(chosen),6);self.assertEqual({q['source'].split('-')[0] for q in chosen},{prefix+'1',prefix+'2'})
    def test_verified_only_never_splits_passage(self):
        asset=self.audio();group=secrets.token_hex(6)
        for i in range(6):self.question(asset['url'],category='reading',source=group+'-'+str(i),verified=i!=0)
        self.configure(count=5)
        self.assertEqual(self.c.get('/api/platform/mock/settings?skill=listening').json['available'],0)
        self.assertEqual(self.post('/api/platform/mock',{'skill':'listening'}).status_code,409)
    def test_unavailable_audio_never_splits_passage(self):
        first=self.audio();second=self.audio();group=secrets.token_hex(6)
        for i in range(6):self.question(first['url'] if i<5 else second['url'],category='reading',source=group+'-'+str(i))
        self.configure(count=5)
        self.post('/api/platform/admin/media/'+second['id'],{'published':False})
        self.assertEqual(self.c.get('/api/platform/mock/settings?skill=listening').json['available'],0)
        self.assertEqual(self.post('/api/platform/mock',{'skill':'listening'}).status_code,409)
        self.assertEqual(self.post('/api/platform/practice',{'category':'reading','skill':'listening'}).status_code,409)
    def test_generated_audio_provenance_and_staff_permissions(self):
        asset=self.audio();self.question(asset['url'])
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO generated_audio VALUES (?,?,?,?,?,?,?)',(asset['id'],'synthetic cache','Synthetic input','ko-KR-SunHiNeural','ko',time.time(),1))
        d=self.post('/api/platform/practice',{'category':'qa','skill':'listening'}).json
        self.assertTrue(d['questions'][0]['audio_ai_generated'])
        legacy.users[self.name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.post('/api/platform/admin/mock/settings',{'skill':'listening','count':5,'seconds':60,'verified_only':False}).status_code,403)
        self.assertEqual(self.c.get('/api/platform/mock/settings?skill=invalid').status_code,400)

    def test_weighted_scoring_snapshot_and_history(self):
        asset=self.audio();qs=[self.question(asset['url'],category='qa' if i<3 else 'blank') for i in range(5)]
        cfg={'skill':'listening','count':5,'seconds':60,'verified_only':True,'weights':{'qa':4,'blank':2}}
        self.assertEqual(self.post('/api/platform/admin/mock/settings',cfg).status_code,200)
        reading=self.c.get('/api/platform/mock/settings').json['settings']['weights']
        aid=self.post('/api/platform/mock',{'skill':'listening'}).json['id'];base='/api/platform/mock/'+aid
        self.assertEqual(self.c.get(base).json['weights'],cfg['weights'])
        # Edits after starting must not change the saved scoring rubric.
        self.post('/api/platform/admin/mock/settings',{**cfg,'weights':{'qa':100}})
        for q in qs[:4]:self.assertEqual(self.post(base+'/answer',{'id':q['id'],'choice':1}).status_code,200)
        result=self.post(base+'/finish',{}).json['result']
        self.assertEqual((result['score'],result['total'],result['points'],result['max_points']),(4,5,14,16))
        self.assertEqual(result['categories']['qa']['points'],12)
        self.assertEqual(result['categories']['blank']['max_points'],4)
        self.assertEqual(self.post(base+'/finish',{}).json['result'],result)
        self.assertEqual(self.c.get(base).json['result'],result)
        self.assertEqual(next(a['result'] for a in self.c.get('/api/platform/mock/history').json['attempts'] if a['id']==aid),result)
        self.assertEqual(self.c.get('/api/platform/mock/settings').json['settings']['weights'],reading)
        # Old clients omitting weights preserve the saved configuration.
        self.configure();self.assertEqual(self.c.get('/api/platform/mock/settings?skill=listening').json['settings']['weights'],{'qa':100})

    def test_invalid_weights_and_legacy_run_defaults(self):
        cfg={'skill':'listening','count':5,'seconds':60,'verified_only':True}
        for weights in ([],{'qa':0},{'qa':101},{'qa':True},{'qa':1.5},{'':2},{'x'*81:1},{str(i):1 for i in range(51)}):
            self.assertEqual(self.post('/api/platform/admin/mock/settings',{**cfg,'weights':weights}).status_code,400)
        asset=self.audio();[self.question(asset['url']) for _ in range(5)];self.configure()
        aid=self.post('/api/platform/mock',{'skill':'listening'}).json['id'];base='/api/platform/mock/'+aid
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:c.execute('DELETE FROM mock_run_scoring WHERE run=?',(aid,))
        self.assertEqual(self.c.get(base).json['weights'],{})
        result=self.post(base+'/finish',{}).json['result']
        self.assertEqual((result['points'],result['max_points']),(0,5))
