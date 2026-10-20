from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from admin_auth_preflight import validate_admin_authentication


class AdminAuthPreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'platform.sqlite3'
        self.user = dict(username='synthetic', role='admin', status='approved', pw=None,
                         auth_method='firebase_only', firebase_uid='synthetic-uid')
        self.env = {'THANA_FIREBASE_AUTH_ENABLED':'1'}
        self.verify = Mock(return_value=SimpleNamespace(uid='synthetic-uid', disabled=False))

    def seed(self, enabled=1, username='synthetic'):
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE firebase_account_bindings(uid TEXT PRIMARY KEY,username TEXT UNIQUE,enabled INTEGER)')
            c.execute('INSERT INTO firebase_account_bindings VALUES (?,?,?)', ('synthetic-uid',username,enabled))

    def check(self):
        validate_admin_authentication({'synthetic':self.user}, self.path, self.env, self.verify)

    def test_explicit_binding_and_live_identity_required_without_password_creation(self):
        self.seed(); before = self.path.read_bytes()
        self.check(); self.verify.assert_called_once_with('synthetic-uid')
        self.assertIsNone(self.user['pw']); self.assertEqual(before, self.path.read_bytes())

    def test_disabled_bridge_emulator_legacy_hash_and_unapproved_fail_before_provider(self):
        self.seed()
        for change in ({'pw':'salt$oldhash'}, {'pw':'pbkdf2_sha256$invalid'}, {'status':'pending'}, {'auth_method':'other'}, {'username':'other'}, {'firebase_uid':''}):
            original = dict(self.user); self.user.update(change)
            with self.assertRaises(RuntimeError): self.check()
            self.user = original
        for environment in ({}, {**self.env,'FIREBASE_AUTH_EMULATOR_HOST':'localhost:9099'}):
            self.env = environment
            with self.assertRaises(RuntimeError): self.check()
        self.verify.assert_not_called()

    def test_missing_database_not_created(self):
        with self.assertRaises(RuntimeError): self.check()
        self.assertFalse(self.path.exists()); self.verify.assert_not_called()

    def test_disabled_wrong_and_missing_bindings_fail(self):
        self.seed(0)
        for update in ("UPDATE firebase_account_bindings SET enabled=0", "UPDATE firebase_account_bindings SET enabled=1,username='other'", 'DELETE FROM firebase_account_bindings'):
            with sqlite3.connect(self.path) as c: c.execute(update)
            with self.assertRaises(RuntimeError): self.check()
        self.verify.assert_not_called()

    def test_provider_failures_are_generic_and_no_claim_role_trusted(self):
        self.seed()
        for identity in (SimpleNamespace(uid='wrong', disabled=False), SimpleNamespace(uid='synthetic-uid', disabled=True), SimpleNamespace(uid='synthetic-uid', disabled=None)):
            self.verify.return_value = identity
            with self.assertRaises(RuntimeError): self.check()
        self.verify.side_effect = ValueError('private-provider-detail')
        with self.assertRaises(RuntimeError) as error: self.check()
        self.assertNotIn('private-provider-detail', str(error.exception))
        self.assertNotIn('synthetic', str(error.exception))

    def test_modern_local_admin_works_without_database_or_provider(self):
        self.user['pw'] = 'pbkdf2_sha256$600000$'+'a'*32+'$'+'b'*64
        self.check(); self.verify.assert_not_called(); self.assertFalse(self.path.exists())

    def test_lookup_wrapper_uses_fixed_sdk_app(self):
        from unittest.mock import patch
        from admin_auth_preflight import verify_firebase_identity
        auth = Mock(); app = object()
        with patch('firebase_auth_routes.sdk', return_value=(auth,app)):
            verify_firebase_identity('synthetic-uid')
        auth.get_user.assert_called_once_with('synthetic-uid', app=app)

    def test_real_production_import_enforces_gate(self):
        import os
        import subprocess
        import sys
        from legacy_storage import LegacyStorage
        source = Path(__file__).resolve().parents[1]
        for local in (False, True):
            runtime = Path(self.tmp.name)/('local' if local else 'firebase')
            runtime.mkdir()
            user = dict(self.user)
            if local:
                user['pw'] = 'pbkdf2_sha256$600000$'+'a'*32+'$'+'b'*64
            storage = LegacyStorage(str(runtime))
            storage.save(str(runtime/'users.json'), {'synthetic':user})
            env = {**os.environ, 'THANA_ENV':'production', 'THANA_DATA_DIR':str(runtime),
                   'THANA_PLATFORM_DB':str(runtime/'platform.sqlite3'),
                   'THANA_FIREBASE_AUTH_ENABLED':'0', 'THANA_STAGING_ENABLED':'0',
                   'PYTHONDONTWRITEBYTECODE':'1'}
            result = subprocess.run([sys.executable, '-c', 'import app; assert app.app.config["SESSION_COOKIE_SECURE"]'],
                                    cwd=source, env=env, capture_output=True, timeout=60)
            self.assertEqual(result.returncode == 0, local)
            self.assertFalse((runtime/'bootstrap_credentials.txt').exists())
            if not local:
                self.assertIn(b'Configure secure administrator authentication', result.stderr)
