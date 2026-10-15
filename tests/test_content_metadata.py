import io,json,os,secrets,sqlite3,time,unittest
from PIL import Image
from test_platform import legacy


class ContentMetadataTests(unittest.TestCase):
    def setUp(self):
        self.c=legacy.app.test_client();self.name='metadata_'+secrets.token_hex(4)
        legacy.users[self.name]={'username':self.name,'name':'Synthetic metadata author','role':'admin','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=self.name
        self.ids=[]
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for qid in self.ids:
                c.execute('DELETE FROM eps_bank WHERE id=?',(qid,));c.execute('DELETE FROM reviews WHERE qid=?',(qid,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)
    def post(self,path,body):
        token=self.c.get('/api/csrf').json['token']
        return self.c.post(path,json=body,headers={'X-CSRF-Token':token})
    def question(self,**extra):
        d={'category':'qa','type':'text','stem_ko':'Synthetic EPS item','stem_lo':'ຄຳຖາມ','choices_ko':['A','B'],'choices_lo':['A','B'],'answer':1,'verified':True,'difficulty':'advanced','explanation_ko':'Synthetic answer explanation','explanation_lo':'ຄຳອະທິບາຍ','source':'metadata-'+secrets.token_hex(6)}
        d.update(extra);r=self.post('/api/platform/admin/bank',d);self.assertEqual(r.status_code,200,r.json)
        self.ids.append(r.json['id']);return {**d,'id':r.json['id']}
    def test_practice_metadata_private_until_finish_and_snapshot_stable(self):
        q=self.question()
        self.assertEqual(self.post('/api/platform/practice',{'category':'qa','difficulty':'nonsense'}).status_code,400)
        self.assertEqual(self.post('/api/platform/practice',{'category':'qa','difficulty':'beginner'}).status_code,409)
        started=self.post('/api/platform/practice',{'category':'qa','difficulty':'advanced'}).json
        self.assertTrue(any(x['id']==q['id'] for x in started['questions']))
        for public in started['questions']:
            self.assertNotIn('explanation_ko',public);self.assertNotIn('explanation_lo',public);self.assertNotIn('answer',public)
            self.assertEqual(public['difficulty'],'advanced')
        self.assertEqual(self.c.get('/api/platform/practice/'+started['id']+'/result').status_code,409)
        changed={**q,'explanation_ko':'Changed after start','answer':2}
        self.assertEqual(self.post('/api/platform/admin/bank',changed).status_code,200)
        result=self.post('/api/platform/practice/'+started['id'],{'answers':{}}).json
        detail=next(x for x in result['detail'] if x['id']==q['id'])
        self.assertEqual(detail['explanation_ko'],q['explanation_ko']);self.assertEqual(detail['answer'],1)
        reviewed=self.c.get('/api/platform/practice/'+started['id']+'/result')
        self.assertEqual(reviewed.status_code,200);self.assertEqual(reviewed.headers['Cache-Control'],'no-store')
        self.assertEqual(reviewed.json['detail'],result['detail'])
        self.assertTrue(all('explanation_ko' not in item for item in reviewed.json['questions']))
        with self.c.session_transaction() as session:session.clear()
        self.assertEqual(self.c.get('/api/platform/practice/'+started['id']+'/result').status_code,401)
        with self.c.session_transaction() as session:session['username']=self.name
        other='other_'+self.name
        legacy.users[other]={'username':other,'name':'Other synthetic learner','role':'student','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as session:session['username']=other
        self.assertEqual(self.c.get('/api/platform/practice/'+started['id']+'/result').status_code,404)
        with self.c.session_transaction() as session:session['username']=self.name
        legacy.users.pop(other);legacy._save(legacy.USERS_FILE,legacy.users)
        retry=self.post('/api/platform/practice/'+started['id']+'/retry',{}).json
        self.assertTrue(all('explanation_ko' not in x and 'answer' not in x for x in retry['questions']))
    def test_mock_explanations_only_after_finish(self):
        q=self.question();aid='metadata_'+secrets.token_hex(5)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO mock_runs VALUES (?,?,?,?,?,?,?,?)',(aid,self.name,json.dumps([q]),'{}',time.time()+300,None,None,time.time()))
        state=self.c.get('/api/platform/mock/'+aid).json
        self.assertNotIn('explanation_ko',state['questions'][0]);self.assertNotIn('answer',state['questions'][0])
        result=self.post('/api/platform/mock/'+aid+'/finish',{}).json['result']
        self.assertEqual(result['detail'][0]['explanation_lo'],q['explanation_lo'])
        self.assertEqual(result['detail'][0]['question']['stem_ko'],q['stem_ko'])
    def test_reading_difficulty_keeps_whole_groups(self):
        group='metadata-group-'+secrets.token_hex(5)
        self.question(category='reading',source=group+'-1')
        self.question(category='reading',source=group+'-2',difficulty='intermediate')
        # A group with mixed assigned levels must not be split by a difficulty filter.
        r=self.post('/api/platform/practice',{'category':'reading','difficulty':'advanced'})
        self.assertEqual(r.status_code,409)
    def test_invalid_question_metadata(self):
        q=self.question();q['image']='/media/library/missing.jpg'
        self.assertEqual(self.post('/api/platform/admin/bank',q).status_code,400)
        q.pop('image');q['difficulty']=['advanced']
        self.assertEqual(self.post('/api/platform/admin/bank',q).status_code,400)
        q['difficulty']='';q['explanation_ko']=7
        self.assertEqual(self.post('/api/platform/admin/bank',q).status_code,400)
    def test_word_picture_publication_guard_and_csv_metadata(self):
        raw=io.BytesIO();Image.new('RGB',(8,8),'green').save(raw,format='PNG');raw.seek(0)
        token=self.c.get('/api/csrf').json['token']
        asset=self.c.post('/api/platform/admin/media',data={'file':(raw,'sample.png'),'title':'Synthetic word image'},headers={'X-CSRF-Token':token}).json
        question=self.question(image=asset['url'],active=False)
        self.assertEqual(self.post('/api/platform/admin/bank',{**question,'active':True}).status_code,400)
        word={'ko':'metadata-'+secrets.token_hex(5),'lo':'ທົດລອງ','part_of_speech':'명사','image_url':asset['url'],'published':False}
        r=self.post('/api/platform/admin/vocabulary',word);self.assertEqual(r.status_code,200,r.json)
        word['id']=r.json['id'];word['published']=True
        self.assertEqual(self.post('/api/platform/admin/vocabulary',word).status_code,400)
        self.post('/api/platform/admin/media/'+asset['id'],{'published':True})
        self.assertEqual(self.post('/api/platform/admin/vocabulary',word).status_code,200)
        public=self.c.get('/api/platform/vocabulary?q='+word['ko']).json['words'][0]
        self.assertEqual(public['image_url'],asset['url']);self.assertEqual(public['part_of_speech'],'명사')
        # Older clients updating text must not erase metadata they do not send.
        word.pop('image_url');word.pop('part_of_speech')
        self.assertEqual(self.post('/api/platform/admin/vocabulary',word).status_code,200)
        self.assertEqual(self.c.get('/api/platform/vocabulary?q='+word['ko']).json['words'][0]['image_url'],asset['url'])
        word['image_url']='https://example.com/untrusted.svg'
        self.assertEqual(self.post('/api/platform/admin/vocabulary',word).status_code,400)
        csv='ko,lo,part_of_speech\nCSV-'+secrets.token_hex(4)+',ຄຳ,명사\n'
        preview=self.post('/api/platform/admin/vocabulary/import',{'csv':csv}).json
        self.assertEqual(preview['preview'][0]['part_of_speech'],'명사')
        self.assertEqual(self.post('/api/platform/admin/vocabulary/import',{'csv':csv,'commit':True}).json['added'],1)
        rows=self.c.get('/api/platform/admin/vocabulary').json['words']
        imported=next(x for x in rows if x['ko']==preview['preview'][0]['ko'])
        self.assertEqual(imported['part_of_speech'],'명사');self.assertFalse(imported['published'])
