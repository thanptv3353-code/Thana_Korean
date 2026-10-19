import copy
import json
import os
import secrets
import sqlite3
import unittest
from firebase_curriculum import COURSES,apply_source_overrides,build_drafts,import_static_drafts,load_source
from test_platform import legacy

class FirebaseCurriculumTests(unittest.TestCase):
    def setUp(self):
        self.name='firebase_content_'+secrets.token_hex(4)
        legacy.users[self.name]=dict(username=self.name,name='Synthetic migration author',role='admin',status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users);self.client=legacy.app.test_client()
        with self.client.session_transaction() as s:s['username']=self.name
    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            for d in build_drafts():
                db.execute('DELETE FROM lesson_revisions WHERE lesson=?',(d['id'],));db.execute('DELETE FROM course_lessons WHERE id=?',(d['id'],))
            for cid in COURSES:
                db.execute('DELETE FROM course_rules WHERE course=?',(cid,));db.execute('DELETE FROM courses WHERE id=?',(cid,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)
    def test_complete_public_source_and_every_adapted_exercise_through_actual_preview(self):
        source=load_source();drafts=build_drafts(source)
        self.assertEqual(len(source['constants']['DEFAULT_LESSONS']),12)
        self.assertEqual(sum(len(c['questions']) for c in source['eps']),531)
        self.assertEqual(len(drafts),81);self.assertEqual(sum(len(d['content']['quiz']) for d in drafts),378)
        original={l['id'] for l in source['constants']['DEFAULT_LESSONS']}
        self.assertTrue(original<={d['id'] for d in drafts})
        seasonal={s['id'] for c in source['constants']['SEASONAL_WORKER_CATEGORIES'] for s in c['subLessons']}
        self.assertEqual(len(seasonal),68);self.assertTrue(seasonal<={d['id'] for d in drafts})
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:db.execute('BEGIN IMMEDIATE');self.assertEqual(import_static_drafts(db,self.name),81)
        for d in drafts:
            content=d['content'];answers={str(i):q['answer'] for i,q in enumerate(content['quiz'])}
            r=self.client.post('/api/platform/admin/courses/'+d['course']+'/preview-grade',json={'content':content,'answers':answers},headers={'X-CSRF-Token':self.client.get('/api/csrf').json['token']})
            self.assertEqual(r.status_code,200,d['id']);self.assertEqual(r.json['score'],100,d['id'])
            self.assertEqual(self.client.get('/api/platform/lessons/'+d['id']).status_code,404)
        q=next(q for d in drafts for q in d['content']['quiz'] if q['id']=='firebase-l1_fill_ieyo-1')
        self.assertEqual(q['options'][q['answer']],'예요');self.assertEqual(q['question'],'이 사람은 제 친구____')
    def test_additive_reimport_preserves_edits_and_cross_course_collision_rolls_back(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('BEGIN IMMEDIATE');import_static_drafts(db,self.name)
            edited=json.dumps({'title':'Owner edit'});db.execute('UPDATE course_lessons SET draft=?,revision=7 WHERE id=?',(edited,'lesson-0'))
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('BEGIN IMMEDIATE');self.assertEqual(import_static_drafts(db,self.name),0)
            self.assertEqual(db.execute("SELECT draft,revision FROM course_lessons WHERE id='lesson-0'").fetchone(),(edited,7))
            self.assertEqual(db.execute('SELECT count(*) FROM course_lessons WHERE course IN (?,?) AND published IS NOT NULL',COURSES).fetchone()[0],0)
            db.execute("UPDATE course_lessons SET course='foreign' WHERE id='exp-7'")
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError):import_static_drafts(db,self.name)
    def test_content_overrides_preserve_ids_ignore_access_and_report_unknown_fields(self):
        source=load_source();original=copy.deepcopy(source)
        patched,report=apply_source_overrides(source,{'thana_lesson_meta':[{'id':'lesson-1','data':{'title':'Owner revised title','paid':False}},{'id':'missing','data':{'title':'Unknown'}}], 'thana_phrases':[{'id':'l1-jeo','data':{'lao':'Owner revised meaning'}}]})
        self.assertEqual(source,original)
        lesson=next(d for d in build_drafts(patched) if d['id']=='lesson-1')
        self.assertEqual(lesson['content']['title'],'Owner revised title')
        self.assertIn('Owner revised meaning','\n'.join(b['value'] for b in lesson['content']['blocks']))
        self.assertEqual(report['thana_lesson_meta'],dict(applied_fields=1,unmatched_documents=1,unsupported_fields=1))
        self.assertEqual(patched['constants']['L1_CORE_VOCAB'][0]['id'],'l1-jeo')
        guarded,report=apply_source_overrides(source,{'thana_lesson_meta':[{'id':'gr-1','data':{'title':'Wrong collection'}}]})
        self.assertEqual(guarded,source)
        self.assertEqual(report['thana_lesson_meta']['unmatched_documents'],1)

        item=source['constants']['BATCHIM_EXAMPLES'][0]
        key='hangul-batchim-'+item['syllable']
        patched,report=apply_source_overrides(source,{'thana_phrases':[{'id':key,'data':{'lao':'Revised batchim sound'}}]})
        self.assertEqual(patched['constants']['BATCHIM_EXAMPLES'][0]['lao'],'Revised batchim sound')
        self.assertEqual(report['thana_phrases']['unmatched_documents'],0)
