import json, os, secrets, sqlite3, unittest
from test_platform import legacy
from readiness_routes import collect_issues


class ReadinessTests(unittest.TestCase):
    def test_effective_reviews_exclusions_and_translation_gaps(self):
        c = sqlite3.connect(':memory:'); c.row_factory = sqlite3.Row
        c.executescript('CREATE TABLE reviews(qid INTEGER, verified INTEGER); CREATE TABLE eps_bank(id INTEGER,content TEXT,active INTEGER); CREATE TABLE vocabulary(id TEXT,ko TEXT,lo TEXT,audio_ko TEXT,audio_lo TEXT,published INTEGER);')
        q = {'stem_ko':'질문', 'stem_lo':'', 'choices_ko':['하나','둘'], 'choices_lo':['ໜຶ່ງ',''], 'verified':True}
        c.execute('INSERT INTO eps_bank VALUES (1,?,1)',(json.dumps(q),))
        c.execute('INSERT INTO reviews VALUES (1,0)')
        c.execute('INSERT INTO eps_bank VALUES (2,?,0)',(json.dumps(q),))
        c.execute('INSERT INTO eps_bank VALUES (3,?,1)',(json.dumps({'verified':False}),))
        c.execute('INSERT INTO reviews VALUES (3,1)')
        c.execute("INSERT INTO vocabulary VALUES ('public','단어','ຄຳ','/audio.wav','',1)")
        c.execute("INSERT INTO vocabulary VALUES ('draft','초안','ຮ່າງ','','',0)")
        rows = collect_issues(c)
        self.assertEqual([(i['kind'], i['id']) for i in rows],[('eps','1'),('vocabulary','public')])
        self.assertEqual(rows[0]['issues'],['unverified','stem_lo','choices_lo'])
        self.assertEqual(rows[1]['issues'],['audio_lo'])
        self.assertNotIn('answer',rows[0]); self.assertEqual(rows[0]['url'],'/question-editor?id=1')
        c.close()

    def test_staff_only_and_pagination(self):
        client = legacy.app.test_client()
        self.assertEqual(client.get('/api/platform/admin/content-readiness').status_code,403)
        name='readiness_'+secrets.token_hex(4)
        legacy.users[name]={'username':name,'name':'Synthetic reviewer','role':'student','status':'approved'}
        legacy._save(legacy.USERS_FILE,legacy.users)
        with client.session_transaction() as s:s['username']=name
        self.assertEqual(client.get('/api/platform/admin/content-readiness').status_code,403)
        legacy.users[name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(client.get('/content-readiness').status_code,200)
        self.assertEqual(client.get('/api/platform/admin/content-readiness?page=bad').status_code,400)
        self.assertEqual(client.get('/api/platform/admin/content-readiness?kind=invalid').status_code,400)
        r=client.get('/api/platform/admin/content-readiness?kind=eps&page=100000')
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['Cache-Control'],'no-store')
        self.assertLessEqual(len(r.json['items']),30);self.assertEqual(r.json['page'],r.json['pages'])
        self.assertTrue(all(i['kind']=='eps' and 'answer' not in i for i in r.json['items']))
        d=client.get('/api/platform/admin/content-readiness?q=nonexistent_'+secrets.token_hex(6)).json
        self.assertEqual(d['total'],0);self.assertEqual(d['items'],[])
        legacy.users.pop(name);legacy._save(legacy.USERS_FILE,legacy.users)
