import subprocess
import unittest
from pathlib import Path


class AccountUITests(unittest.TestCase):
    def test_signin_logout_roles_errors_and_recovery_isolation(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/account_ui_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
