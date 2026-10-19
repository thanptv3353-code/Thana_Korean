import subprocess
import unittest
from pathlib import Path

class FirebaseLoginUITests(unittest.TestCase):
    def test_legacy_username_login_without_real_provider_or_persistence(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/firebase_login_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
