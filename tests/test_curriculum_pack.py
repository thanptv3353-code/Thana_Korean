import json
import os
import secrets
import sqlite3
import unittest
from pathlib import Path
import quiz_engine
from curriculum_pack import COURSES, MODULES, import_drafts, lessons
from test_platform import legacy


class CurriculumPackTests(unittest.TestCase):
    def setUp(self):
        self.name='curriculum_'+secrets.token_hex(4)
        legacy.users[self.name]=dict(username=self.name,name='Synthetic curriculum author',role='admin',status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users)
        self.c=legacy.app.test_client()
        with self.c.session_transaction() as session:session['username']=self.name
        self.path='/api/platform/admin/curriculum-pack'

    def post(self,body=None):
        return self.c.post(self.path,json=body if body is not None else dict(pack='foundation-v1',language='all'),headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            for language,(cid,_,_) in COURSES.items():
                for item in lessons(language):
                    for table,key in [('lesson_revisions','lesson'),('course_progress','lesson'),('course_lessons','id')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(item['id'],))
                for table,key in [('courses','id'),('course_rules','course'),('course_levels','course')]:c.execute('DELETE FROM '+table+' WHERE '+key+'=?',(cid,))
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def test_curriculum_quality_structure_and_preserved_source_questions(self):
        source_path=Path(__file__).resolve().parents[1]/'data/lessons.json'
        original={q['id']:q for l in json.loads(source_path.read_text()) for q in l['quiz']}
        ids=[];question_ids=[];reused=[]
        for language in ('ko','lo'):
            items=lessons(language);self.assertEqual(len(items),24)
            self.assertEqual([l['content']['order'] for l in items],list(range(1,25)))
            self.assertEqual(set(l['content']['module'] for l in items),set(MODULES[language]))
            for item in items:
                ids.append(item['id']);d=item['content']
                self.assertTrue(d['objectives']);self.assertEqual(len(d['blocks']),5)
                self.assertGreater(len(d['blocks'][1]['value']),140)
                self.assertEqual({q['type'] for q in d['quiz']},{'choice','blank','matching','ordering'})
                self.assertTrue(all(b['type']=='text' for b in d['blocks']))
                for q in d['quiz']:
                    self.assertTrue(quiz_engine.valid(q),(item['id'],q['id']))
                    question_ids.append(q['id'])
                    if q['id'] in original:
                        reused.append(q['id'])
                        for key in ('question','options','answer'):self.assertEqual(q[key],original[q['id']][key])
        self.assertEqual(len(set(ids)),48);self.assertEqual(len(question_ids),206)
        self.assertEqual(len(set(question_ids)),206);self.assertEqual(len(reused),14)
        # Golden curriculum checks catch semantic regression beyond schema validity.
        self.assertEqual(lessons('lo')[9]['content']['quiz'][0]['options'][lessons('lo')[9]['content']['quiz'][0]['answer']],'ຊາວ')
        self.assertIn('물 한 잔 주세요.',lessons('ko')[20]['content']['quiz'][0]['options'])

    def test_import_draft_privacy_idempotency_and_preserves_owner_edits(self):
        before=self.c.get('/api/platform/courses').json
        r=self.post();self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['counts'],dict(ko=24,lo=24));self.assertEqual(r.json['published_new'],0)
        self.assertEqual(self.c.get('/api/platform/courses').json,before)
        item=lessons('ko')[4];cid=item['course']
        self.assertEqual(self.c.get('/api/platform/lessons/'+item['id']).status_code,404)
        staff=self.c.get('/api/platform/admin/courses').json
        drafts=[l for l in staff['lessons'] if l['course'] in {v[0] for v in COURSES.values()}]
        self.assertEqual(len(drafts),48);self.assertFalse(any(l['published'] for l in drafts))
        # Author can preview every generated content with the actual validator/grader.
        for language in ('ko','lo'):
            for lesson in lessons(language):
                content=lesson['content'];answers={}
                for n,q in enumerate(content['quiz']):
                    answers[str(n)]=q.get('answer') if q['type'] in ('choice','ordering') else q['accepted'][0] if q['type']=='blank' else [p['right'] for p in q['pairs']]
                response=self.c.post('/api/platform/admin/courses/'+lesson['course']+'/preview-grade',json=dict(content=content,answers=answers),headers={'X-CSRF-Token':self.c.get('/api/csrf').json['token']})
                self.assertEqual(response.status_code,200,lesson['id']);self.assertEqual(response.json['score'],100)
        edited=dict(item['content'],title='Owner reviewed title')
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            payload=json.dumps(edited)
            c.execute('UPDATE course_lessons SET draft=?,published=?,revision=7 WHERE id=?',(payload,payload,item['id']))
            c.execute('INSERT INTO course_progress VALUES (?,?,?,?)',('synthetic-owner',item['id'],100,123))
            c.execute('UPDATE courses SET title=? WHERE id=?',('Owner course title',cid))
            c.execute('UPDATE course_levels SET level=?,revision=4 WHERE course=?',('intermediate',cid))
        self.assertEqual(self.post().json['added'],0)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            row=c.execute('SELECT draft,published,revision FROM course_lessons WHERE id=?',(item['id'],)).fetchone()
            self.assertEqual(row,(payload,payload,7))
            self.assertEqual(c.execute('SELECT COUNT(*) FROM lesson_revisions WHERE lesson=?',(item['id'],)).fetchone()[0],1)
            self.assertEqual(c.execute('SELECT title FROM courses WHERE id=?',(cid,)).fetchone()[0],'Owner course title')
            self.assertEqual(c.execute('SELECT level,revision FROM course_levels WHERE course=?',(cid,)).fetchone(),('intermediate',4))
            self.assertEqual(c.execute('SELECT score FROM course_progress WHERE lesson=?',(item['id'],)).fetchone()[0],100)
            self.assertTrue(c.execute("SELECT 1 FROM audit_log WHERE actor=? AND action='curriculum_pack_import'",(self.name,)).fetchone())

    def test_scope_validation_and_all_track_collision_rollback(self):
        self.assertEqual(self.c.post(self.path,json=dict(pack='foundation-v1',language='all')).status_code,403)
        for role,status in [('teacher','approved'),('student','approved'),('admin','pending')]:
            legacy.users[self.name].update(role=role,status=status);legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.post().status_code,403)
        legacy.users[self.name].update(role='superadmin',status='approved');legacy._save(legacy.USERS_FILE,legacy.users)
        for body in [[],{},dict(pack='foundation-v1',language=[]),dict(pack='other',language='all'),dict(pack='foundation-v1',language='en'),dict(pack='foundation-v1',language='all',publish=True)]:self.assertEqual(self.post(body).status_code,400)
        last=lessons('lo')[-1]
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('INSERT INTO course_lessons VALUES (?,?,?,?,?,?)',(last['id'],'foreign','{}',None,1,0))
        self.assertEqual(self.post().status_code,409)
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM courses WHERE id IN (?,?)',tuple(v[0] for v in COURSES.values())).fetchone()[0],0)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM course_lessons WHERE course=?',(COURSES['ko'][0],)).fetchone()[0],0)
            c.execute('DELETE FROM course_lessons WHERE id=?',(last['id'],))
        self.assertEqual(self.post(dict(pack='foundation-v1',language='lo')).json['counts'],dict(lo=24))
        self.assertEqual(self.post(dict(pack='foundation-v1',language='ko')).json['counts'],dict(ko=24))
