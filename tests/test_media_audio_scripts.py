import subprocess
import unittest
from pathlib import Path

class AudioScriptUITests(unittest.TestCase):
    def test_script_selection_never_synthesizes_and_resets_consent(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/media_audio_script_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
