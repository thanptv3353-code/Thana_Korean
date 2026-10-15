"""Verify an extracted source bundle using only temporary synthetic runtime data."""
import json,os,sqlite3,subprocess,sys,tempfile,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
def run(args,**kwargs):subprocess.run(args,check=True,**kwargs)
run([sys.executable,str(root/'scripts/package_source.py')],cwd=root)
with tempfile.TemporaryDirectory(prefix='thana-release-') as temporary:
    source=Path(temporary)/'source';source.mkdir()
    with zipfile.ZipFile(root/'SOURCE_REVIEW.zip') as archive:
        assert archive.testzip() is None
        names=archive.namelist()
        assert not any(Path(n).name in ('users.json','progress.json','secret_key','bootstrap_credentials.txt') or '.sqlite3' in n or n.startswith(('data/media/','data/receipts/','.git/')) for n in names)
        archive.extractall(source)
    runtime=Path(temporary)/'runtime';runtime.mkdir()
    env={**os.environ,'THANA_DATA_DIR':str(runtime),'THANA_PLATFORM_DB':str(runtime/'platform.sqlite3')}
    for _ in range(2):run([sys.executable,'scripts/init_content.py'],cwd=source,env=env)
    with sqlite3.connect(runtime/'platform.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM course_lessons').fetchone()[0]==3
        assert db.execute('SELECT COUNT(*) FROM vocabulary').fetchone()[0]==6
        assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert (runtime/'bootstrap_credentials.txt').stat().st_mode & 0o077==0
    smoke='''
from app import app
from pathlib import Path
import os
client=app.test_client()
for route in ('/','/courses','/dictionary','/my-learning','/review','/mock-exam','/account','/membership','/community','/tutor','/health'):
    assert client.get(route).status_code==200,route
assert client.get('/api/platform/learning-progress').status_code==401
assert client.get('/management').status_code==302
password=(Path(os.environ['THANA_DATA_DIR'])/'bootstrap_credentials.txt').read_text().split('password: ',1)[1].strip()
token=client.get('/api/csrf').json['token']
assert client.post('/api/login',json={'username':'admin','password':password},headers={'X-CSRF-Token':token}).status_code==200
assert client.get('/admin').location=='/management'
for route in ('/management','/legacy-admin','/editor','/media-studio','/question-editor','/vocabulary-studio'):
    assert client.get(route).status_code==200,route
assert client.get('/api/platform/management').json['counts']['courses']==1
print('Clean bootstrap, public/authorized HTTP and private-access smoke passed')
'''
    run([sys.executable,'-c',smoke],cwd=source,env=env)
    run([sys.executable,'-m','unittest','discover','-s','tests','-q'],cwd=source,env=env)
    for path in (source/'static').glob('*.js'):run(['node','--check',str(path)],cwd=source)
print('Release verification passed: clean extracted package, idempotent seeds, database integrity, HTTP, tests and JavaScript')
