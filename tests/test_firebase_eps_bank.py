import json
import os
import secrets
import sqlite3
import unittest
from firebase_curriculum import load_source
from firebase_eps_bank import import_bank,media_paths
from test_platform import legacy

class FirebaseEpsBankTests(unittest.TestCase):
    def setUp(self):
        self.name='eps_review_'+secrets.token_hex(4)
        legacy.users[self.name]=dict(username=self.name,name='Synthetic',role='admin',status='approved');legacy._save(legacy.USERS_FILE,legacy.users)
        self.client=legacy.app.test_client()
        with self.client.session_transaction() as s:s['username']=self.name
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('DELETE FROM firebase_eps_bank');db.execute('DELETE FROM firebase_eps_media_map')
    def tearDown(self):
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('DELETE FROM firebase_eps_bank');db.execute('DELETE FROM firebase_eps_media_map')
    def post(self,path,body):return self.client.post('/api/platform/admin/firebase-eps'+path,json=body,headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
    def test_complete_ids_originals_and_repeat_import_preserve_staff_edits(self):
        self.assertEqual(self.post('/import',{}).json['added'],531)
        data=self.client.get('/api/platform/admin/firebase-eps?state=text').json
        self.assertEqual(data['total'],149);self.assertEqual(data['published'],0);self.assertEqual(len(data['categories']),15)
        item=data['questions'][0];qid=item['id'];question=item['question']
        body=dict(revision=1,answer=question['correct_answer_index'],explanation='Synthetic review',reviewed=True)
        saved=self.post('/'+qid,body);self.assertEqual(saved.status_code,200);self.assertEqual(saved.json['revision'],2)
        self.assertEqual(self.post('/'+qid,body).status_code,409)
        self.assertEqual(self.post('/import',{}).json['added'],0)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            original,content,reviewed=db.execute('SELECT original,content,reviewed FROM firebase_eps_bank WHERE id=?',(qid,)).fetchone()
            self.assertEqual(json.loads(original),question);self.assertEqual(json.loads(content)['explanation_lao'],'Synthetic review');self.assertEqual(reviewed,1)
            self.assertEqual({r[0] for r in db.execute('SELECT id FROM firebase_eps_bank')},{q['id'] for c in load_source()['eps'] for q in c['questions']})
    def test_missing_media_never_marked_ready_and_access_is_staff_only(self):
        self.post('/import',{})
        data=self.client.get('/api/platform/admin/firebase-eps?state=media').json;self.assertEqual(data['total'],382)
        item=data['questions'][0];body=dict(revision=1,answer=item['question']['correct_answer_index'],explanation='',reviewed=True)
        self.assertEqual(self.post('/'+item['id'],body).status_code,409)
        self.assertEqual(self.client.post('/api/platform/admin/firebase-eps/import',json={}).status_code,403)
        legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.client.get('/api/platform/admin/firebase-eps').status_code,403)
        self.assertEqual(self.post('/import',{}).status_code,403)
        self.assertEqual(self.client.get('/firebase-eps-review').status_code,302)
        with self.client.session_transaction() as s:s.clear()
        self.assertEqual(self.client.get('/api/platform/admin/firebase-eps').status_code,403)
    def test_teacher_can_review_but_cannot_import_and_filters_are_validated(self):
        self.post('/import',{});legacy.users[self.name]['role']='teacher';legacy._save(legacy.USERS_FILE,legacy.users)
        self.assertEqual(self.client.get('/api/platform/admin/firebase-eps?state=text').status_code,200)
        self.assertEqual(self.post('/import',{}).status_code,403)
        for query in ('page=0','page=bad','state=published','category=unknown'):
            self.assertEqual(self.client.get('/api/platform/admin/firebase-eps?'+query).status_code,400)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            row=db.execute("SELECT content FROM firebase_eps_bank WHERE id='L401'").fetchone()
            self.assertEqual(len(media_paths(json.loads(row[0]))),5)

    def upload_media(self,kind):
        import io,wave
        from PIL import Image
        stream=io.BytesIO()
        if kind=='image':Image.new('RGB',(4,4),'blue').save(stream,format='PNG');name='synthetic.png'
        else:
            with wave.open(stream,'wb') as audio:audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0\0'*160)
            name='synthetic.wav'
        stream.seek(0)
        response=self.client.post('/api/platform/admin/media',data={'title':'Synthetic EPS media','file':(stream,name)},headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
        self.assertEqual(response.status_code,201)
        return response.json
    def remove_media(self,items):
        from pathlib import Path
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            for item in items:
                row=db.execute('SELECT filename FROM media_assets WHERE id=?',(item['id'],)).fetchone()
                if row:(Path(legacy.DATA)/'media'/row[0]).unlink(missing_ok=True)
                db.execute('DELETE FROM media_assets WHERE id=?',(item['id'],))
    def test_mapping_requires_matching_media_and_published_asset_before_review(self):
        self.post('/import',{});image=self.upload_media('image');audio=self.upload_media('audio')
        try:
            body=dict(path='images/q0001.png',asset=audio['id'],revision=0,question_revision=1)
            self.assertEqual(self.post('/1/media',body).status_code,400)
            body['asset']=image['id'];mapped=self.post('/1/media',body);self.assertEqual(mapped.status_code,200)
            self.assertEqual(self.post('/1/media',body).status_code,409)
            review=dict(revision=2,answer=0,explanation='',reviewed=True)
            self.assertEqual(self.post('/1',review).status_code,409)
            self.assertEqual(legacy.app.test_client().get(image['url']).status_code,404)
            response=self.client.post('/api/platform/admin/media/'+image['id'],json={'published':True},headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
            self.assertEqual(response.status_code,200);self.assertEqual(self.post('/1',review).status_code,200)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:self.assertEqual(json.loads(db.execute("SELECT original FROM firebase_eps_bank WHERE id='1'").fetchone()[0])['image_url'],'images/q0001.png')
            legacy.users[self.name]['role']='student';legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.post('/1/media',dict(path='images/q0001.png',asset=None,revision=1,question_revision=3)).status_code,403)
        finally:self.remove_media([image,audio])
    def test_shared_audio_remap_invalidates_every_affected_review(self):
        self.post('/import',{});first=self.upload_media('audio');second=self.upload_media('audio')
        try:
            for asset in (first,second):self.client.post('/api/platform/admin/media/'+asset['id'],json={'published':True},headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
            body=dict(path='audio/listening/q921.mp3',asset=first['id'],revision=0,question_revision=1)
            self.assertEqual(self.post('/L921-1/media',body).json['affected'],2)
            source={q['id']:q for c in load_source()['eps'] for q in c['questions']}
            for qid in ('L921-1','L921-2'):
                self.assertEqual(self.post('/'+qid,dict(revision=2,answer=source[qid]['correct_answer_index'],explanation='',reviewed=True)).status_code,200)
            body.update(asset=second['id'],revision=1,question_revision=3)
            self.assertEqual(self.post('/L921-1/media',body).json['affected'],2)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                self.assertEqual(db.execute("SELECT revision,reviewed FROM firebase_eps_bank WHERE id IN ('L921-1','L921-2')").fetchall(),[(4,0),(4,0)])
        finally:self.remove_media([first,second])
    def test_image_choice_question_requires_audio_and_all_four_choice_images(self):
        self.post('/import',{});assets=[self.upload_media('audio')]+[self.upload_media('image') for _ in range(4)]
        source=next(q for c in load_source()['eps'] for q in c['questions'] if q['id']=='L401')
        try:
            for asset in assets:self.client.post('/api/platform/admin/media/'+asset['id'],json={'published':True},headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
            paths=[source['audio_url']]+source['choices']
            for index,(path,asset) in enumerate(zip(paths,assets)):
                self.assertEqual(self.post('/L401/media',dict(path=path,asset=asset['id'],revision=0,question_revision=index+1)).status_code,200)
                if index<4:self.assertEqual(self.post('/L401',dict(revision=index+2,answer=source['correct_answer_index'],explanation='',reviewed=True)).status_code,409)
            self.assertEqual(self.post('/L401',dict(revision=6,answer=source['correct_answer_index'],explanation='',reviewed=True)).status_code,200)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                current=json.loads(db.execute("SELECT content FROM firebase_eps_bank WHERE id='L401'").fetchone()[0])
                self.assertEqual(current['choices'],source['choices']);self.assertEqual(current['correct_answer_index'],source['correct_answer_index'])
        finally:self.remove_media(assets)
