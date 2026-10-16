"""Exercise async microphone lifecycle using synthetic Node media objects."""
import subprocess
import unittest
from pathlib import Path

class SpeakingRecorderTests(unittest.TestCase):
    def test_recording_context_cancellation_and_cleanup(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/speaking_recorder_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=15)
