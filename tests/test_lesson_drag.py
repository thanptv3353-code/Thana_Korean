import subprocess,unittest
from pathlib import Path

class LessonDragTests(unittest.TestCase):
    def test_pointer_lifecycle_and_cancel_guards(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/lesson_drag_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
