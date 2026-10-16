import subprocess
import unittest
from pathlib import Path


class SpeakingNavigationTests(unittest.TestCase):
    def test_prompt_queue_bounds_and_recording_guard(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['node', str(root / 'tests/speaking_navigation_checks.js')],
                       cwd=root, check=True, capture_output=True, text=True, timeout=10)
