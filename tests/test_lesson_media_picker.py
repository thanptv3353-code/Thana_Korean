import subprocess
import unittest
from pathlib import Path
class LessonMediaPickerTests(unittest.TestCase):
    def test_staff_picker_search_preview_and_draft_guard(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/lesson_media_picker_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
