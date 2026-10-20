import copy
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from firebase_missed_words import import_missed_words,phrase_index
from firebase_runtime_candidate import build_candidate
from firebase_curriculum import load_source
from firebase_learning_migration import apply_learning


class FirebaseMissedWordTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.addCleanup(self.db.close)
        self.source={'constants':{'WORDS':[dict(id='original-word',ko='학교',lao='ໂຮງຮຽນ')]}}
        self.index=phrase_index(self.source)

    def test_original_id_count_private_save_unpublished_and_idempotent(self):
        data={'words':{'original-word':3}}
        report=import_missed_words(self.db,'learner-a',data,self.index)
        self.assertEqual(report['added'],1)
        self.assertEqual(self.db.execute('SELECT id,published FROM vocabulary').fetchall(),[('original-word',0)])
        self.assertEqual(self.db.execute('SELECT owner,source_id,miss_count FROM firebase_missed_words').fetchall(),[('learner-a','original-word',3)])
        self.assertEqual(import_missed_words(self.db,'learner-a',data,self.index)['added'],0)
        self.assertEqual(import_missed_words(self.db,'learner-b',data,self.index)['added'],1)
        self.assertEqual(self.db.execute('SELECT owner FROM saved_words ORDER BY owner').fetchall(),[('learner-a',),('learner-b',)])

    def test_preserves_learner_removal_staff_edits_and_review_schedule(self):
        data={'words':{'original-word':2}}
        import_missed_words(self.db,'learner-a',data,self.index)
        self.db.execute('DELETE FROM saved_words')
        self.db.execute("UPDATE vocabulary SET lo='staff correction',published=1")
        self.db.execute('CREATE TABLE word_reviews(owner TEXT,word TEXT,due REAL)')
        self.db.execute("INSERT INTO word_reviews VALUES ('learner-a','original-word',9999999999)")
        import_missed_words(self.db,'learner-a',{'words':{'original-word':5}},self.index)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM saved_words').fetchone()[0],0)
        self.assertEqual(self.db.execute('SELECT lo,published FROM vocabulary').fetchone(),('staff correction',1))
        self.assertEqual(self.db.execute('SELECT due FROM word_reviews').fetchone()[0],9999999999)
        self.assertEqual(self.db.execute('SELECT miss_count FROM firebase_missed_words').fetchone()[0],5)

    def test_unknown_ambiguous_malformed_values_stay_unresolved(self):
        source=copy.deepcopy(self.source)
        source['constants']['OTHER']=[dict(id='original-word',ko='다른',lao='ອື່ນ')]
        self.assertNotIn('original-word',phrase_index(source))
        for words in (None,[],True):
            self.assertEqual(import_missed_words(self.db,'a',{'words':words},self.index)['status'],'invalid-missed-words')
        words={'original-word':True,'bad':-1,'zero':0,'fraction':1.5,'unknown':2}
        report=import_missed_words(self.db,'a',{'words':words},self.index)
        self.assertEqual(report['unresolved'],5)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM vocabulary').fetchone()[0],0)
        self.assertEqual(import_missed_words(self.db,'a',{'words':{'unknown':2}},self.index)['unresolved'],1)

    def test_existing_vocabulary_collision_is_not_silently_linked(self):
        import_missed_words(self.db,'a',{'words':{}},self.index)
        self.db.execute("INSERT INTO vocabulary VALUES ('other','학교','ໂຮງຮຽນ','','','','','',1)")
        report=import_missed_words(self.db,'a',{'words':{'original-word':1}},self.index)
        self.assertEqual(report['unresolved'],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM saved_words').fetchone()[0],0)

    def test_runtime_candidate_applies_overrides_and_never_guesses_owner(self):
        source=load_source()
        source['constants']['SYNTHETIC_WORDS']=[dict(id='synthetic-word',ko='학교',lao='original')]
        payload={'project':'korean-lao-exam','collections':{
            'thana_users':[{'id':'uid','data':dict(username='synthetic',role='student',approved=True)}],
            'thana_phrases':[{'id':'synthetic-word','data':{'lao':'corrected'}}],
            'thana_progress':[{'id':'private-review','data':{'uid':'uid','words':{'synthetic-word':4}}},
                              {'id':'orphan','data':{'uid':'unknown','words':{'synthetic-word':2}}}]}}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'candidate';report=build_candidate(payload,root,source)
            self.assertEqual(report['learning_import']['missed_word_saves_added'],1)
            with sqlite3.connect(root/'platform.sqlite3') as db:
                self.assertEqual(db.execute('SELECT id,lo,published FROM vocabulary').fetchone(),('synthetic-word','corrected',0))
                self.assertEqual(db.execute('SELECT * FROM saved_words').fetchall(),[('synthetic','synthetic-word')])
                db.execute("INSERT INTO firebase_account_bindings VALUES ('unknown','intruder',0)")
                self.assertEqual(apply_learning(db,payload,source)['missed_word_saves_added'],0)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM saved_words WHERE owner='intruder'").fetchone()[0],0)
                changed=copy.deepcopy(payload);changed['collections']['thana_progress'][0]['data']['words']['synthetic-word']=9
                with self.assertRaises(ValueError):apply_learning(db,changed,source)

    def test_imported_saves_follow_existing_http_publication_and_owner_checks(self):
        import os
        import secrets
        from test_platform import legacy
        owner='missed_'+secrets.token_hex(5);other=owner+'_other';wid='original-'+secrets.token_hex(5)
        for name in (owner,other):
            legacy.users[name]=dict(username=name,name='Synthetic',role='student',status='approved')
        legacy._save(legacy.USERS_FILE,legacy.users)
        client=legacy.app.test_client();second=legacy.app.test_client();anonymous=legacy.app.test_client()
        with client.session_transaction() as session:session.update(username=owner,role='student')
        with second.session_transaction() as session:session.update(username=other,role='student')
        try:
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                import_missed_words(db,owner,{'words':{wid:2}},{wid:('학교'+wid,'ໂຮງຮຽນ','','')})
            self.assertNotIn(wid,client.get('/api/platform/saved-words').json['ids'])
            self.assertEqual(anonymous.get('/api/platform/vocabulary/'+wid).status_code,404)
            self.assertEqual(anonymous.get('/api/platform/saved-words').status_code,401)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('UPDATE vocabulary SET published=1 WHERE id=?',(wid,))
            self.assertIn(wid,client.get('/api/platform/saved-words').json['ids'])
            self.assertNotIn(wid,second.get('/api/platform/saved-words').json['ids'])
            self.assertIn(wid,[w['id'] for w in client.get('/api/platform/review?scope=saved').json['words']])
            self.assertNotIn(wid,[w['id'] for w in second.get('/api/platform/review?scope=saved').json['words']])
            self.assertEqual(client.post('/api/platform/saved-words/'+wid,json={'saved':False}).status_code,403)
        finally:
            for name in (owner,other):legacy.users.pop(name,None)
            legacy._save(legacy.USERS_FILE,legacy.users)
            with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as db:
                db.execute('DELETE FROM saved_words WHERE word=?',(wid,))
                db.execute('DELETE FROM firebase_missed_words WHERE owner=?',(owner,))
                db.execute('DELETE FROM firebase_vocabulary_sources WHERE word=?',(wid,))
                db.execute('DELETE FROM vocabulary WHERE id=?',(wid,))
