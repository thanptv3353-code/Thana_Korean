import subprocess
import unittest
from pathlib import Path


class SpeakingLifecycleTests(unittest.TestCase):
    def test_hidden_and_navigation_cancel_pending_or_active_capture(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['node', str(root / 'tests/speaking_lifecycle_checks.js')],
                       cwd=root, check=True, capture_output=True, text=True, timeout=10)
