import io,json,os,tempfile,unittest,zipfile
from pathlib import Path
from legacy_storage import LegacyStorage
from test_platform import legacy
class StorageTests(unittest.TestCase):
 def test_import_is_once_and_source_is_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'users.json';path.write_text('{"original": {"name": "Test"}}');source=path.read_bytes();a=LegacyStorage(tmp)
   self.assertIn('original',a.load(str(path),{}));a.save(str(path),{'new':{'name':'New'}})
   b=LegacyStorage(tmp);self.assertEqual(b.load(str(path),{}),{'new':{'name':'New'}});self.assertEqual(source,path.read_bytes())
 def test_backup_contains_current_database_and_platform(self):
  c=legacy.app.test_client();legacy.users=legacy._load(legacy.USERS_FILE,{})
  legacy.users['backup_test']={'username':'backup_test','name':'Private fixture','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
  with c.session_transaction() as s:s['username']='backup_test';s['role']='admin'
  r=c.get('/api/admin/backup');self.assertEqual(r.status_code,200)
  with zipfile.ZipFile(io.BytesIO(r.data)) as z:
   self.assertIn('backup_test',json.loads(z.read('users.json')))
   self.assertIn('platform.sqlite3',z.namelist());self.assertIn('manifest.json',z.namelist());self.assertNotIn('secret_key',z.namelist())
  r.close()
