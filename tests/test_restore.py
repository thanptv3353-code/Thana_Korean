import io,json,tempfile,unittest,zipfile
from pathlib import Path
from scripts.restore_backup import restore
class RestoreTests(unittest.TestCase):
 def archive(self,extra=None):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:
   for name,content in [('users.json',{}),('lessons.json',[]),('progress.json',{})]:z.writestr(name,json.dumps(content))
   if extra:z.writestr(*extra)
  b.seek(0);return b
 def test_preview_and_isolated_restore(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'restore';self.assertFalse(restore(self.archive(),out)['applied']);self.assertFalse(out.exists())
   self.assertTrue(restore(self.archive(),out,True)['applied']);self.assertEqual(json.loads((out/'lessons.json').read_text()),[])
   with self.assertRaises(ValueError):restore(self.archive(),out,True)
 def test_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   with self.assertRaises(ValueError):restore(self.archive(('../escape','bad')),Path(tmp)/'out',True)
   self.assertFalse((Path(tmp)/'out').exists())
