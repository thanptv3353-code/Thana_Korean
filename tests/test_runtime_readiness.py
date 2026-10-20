import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from runtime_readiness import inspect_runtime, modern_hash


class RuntimeReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.user = dict(username='synthetic', role='admin', status='approved', pw=None,
                         auth_method='firebase_only', firebase_uid='synthetic-uid')

    def seed(self, enabled=0):
        with sqlite3.connect(self.root/'legacy.sqlite3') as c:
            c.execute('CREATE TABLE documents(name TEXT PRIMARY KEY,content TEXT)')
            c.execute('INSERT INTO documents VALUES (?,?)', ('users.json', json.dumps({'synthetic':self.user})))
        with sqlite3.connect(self.root/'platform.sqlite3') as c:
            c.execute('CREATE TABLE firebase_account_bindings(uid TEXT PRIMARY KEY,username TEXT UNIQUE,enabled INTEGER)')
            c.execute('INSERT INTO firebase_account_bindings VALUES (?,?,?)', ('synthetic-uid','synthetic',enabled))

    def test_missing_files_are_not_created(self):
        report = inspect_runtime(self.root)
        self.assertFalse(report['production_ready'])
        self.assertEqual(set(report['blockers']), {'legacy_database','platform_database'})
        self.assertEqual(list(self.root.iterdir()), [])

    def test_disabled_binding_is_blocker(self):
        self.seed()
        self.assertIn('administrator_authentication_structure', inspect_runtime(self.root)['blockers'])

    def test_enabled_binding_is_only_structural_and_never_mutates(self):
        self.seed(1)
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()}
        report = inspect_runtime(self.root)
        self.assertEqual(report['blockers'], [])
        self.assertFalse(report['production_ready'])
        self.assertTrue(report['required_external_checks'])
        self.assertNotIn('synthetic', json.dumps(report))
        self.assertEqual(before, {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir()})

    def test_wrong_uid_fails(self):
        self.user['firebase_uid'] = 'other'
        self.seed(1)
        report = inspect_runtime(self.root)
        self.assertIn('enabled_bindings_match_approved_accounts', report['blockers'])
        self.assertIn('administrator_authentication_structure', report['blockers'])

    def test_local_admin_and_rejected_binding(self):
        self.user['pw'] = 'pbkdf2_sha256$600000$' + 'a'*32 + '$' + 'b'*64
        self.seed()
        self.assertEqual(inspect_runtime(self.root)['blockers'], [])
        self.user['status'] = 'rejected'
        with sqlite3.connect(self.root/'legacy.sqlite3') as c:
            c.execute('UPDATE documents SET content=?', (json.dumps({'synthetic':self.user}),))
        with sqlite3.connect(self.root/'platform.sqlite3') as c:
            c.execute('UPDATE firebase_account_bindings SET enabled=1')
        report = inspect_runtime(self.root)
        self.assertIn('approved_administrator_exists', report['blockers'])
        self.assertIn('enabled_bindings_match_approved_accounts', report['blockers'])

    def test_malformed_database_is_blocker(self):
        (self.root/'legacy.sqlite3').write_bytes(b'not sqlite')
        report = inspect_runtime(self.root)
        self.assertIn('legacy_database', report['blockers'])

    def test_hash_validation(self):
        valid = 'pbkdf2_sha256$600000$' + 'a'*32 + '$' + 'b'*64
        self.assertTrue(modern_hash(valid))
        for value in (None, 'pbkdf2_sha256$garbage', valid.replace('600000','9999999'), valid+'x'):
            self.assertFalse(modern_hash(value))

    def test_no_admin_and_bad_schema_are_reported(self):
        self.user['role'] = 'student'
        self.seed()
        self.assertIn('approved_administrator_exists', inspect_runtime(self.root)['blockers'])
        with sqlite3.connect(self.root/'legacy.sqlite3') as c:
            c.execute("UPDATE documents SET content='[]'")
        self.assertIn('account_schema', inspect_runtime(self.root)['blockers'])
