import subprocess,unittest
from pathlib import Path
class LearningDirectionTests(unittest.TestCase):
    def test_direction_selection_and_safe_navigation(self):
        root=Path(__file__).resolve().parents[1]
        subprocess.run(['node',str(root/'tests/learning_direction_checks.js')],cwd=root,check=True,capture_output=True,text=True,timeout=10)
