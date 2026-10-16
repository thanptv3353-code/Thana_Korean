import subprocess
import unittest
from pathlib import Path


class CourseModulesTests(unittest.TestCase):
    def test_grouping_preserves_curriculum_order_and_access(self):
        root = Path(__file__).resolve().parents[1]
        subprocess.run(['node', str(root / 'tests/course_modules_checks.js')],
                       cwd=root, check=True, capture_output=True, text=True, timeout=10)
