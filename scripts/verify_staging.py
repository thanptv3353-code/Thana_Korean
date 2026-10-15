"""Verify staging bootstrap and restarts in isolated processes; no real host calls."""
import os,secrets,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='thana-stage-') as tmp:
    runtime=Path(tmp)/'runtime'
    env={**os.environ,'THANA_ENV':'production','THANA_DATA_DIR':str(runtime),'THANA_PLATFORM_DB':str(runtime/'platform.sqlite3'),'THANA_STAGING_ENABLED':'1','THANA_STAGING_USER':'reviewer','THANA_STAGING_PASSWORD':secrets.token_urlsafe(24),'THANA_AI_ENABLED':'0','THANA_SPEECH_ENABLED':'0','THANA_TTS_ENABLED':'0'}
    # Do not inherit bootstrap credentials or provider switches for this test.
    env.pop('THANA_BOOTSTRAP_PASSWORD',None)
    subprocess.run([sys.executable,'scripts/start_server.py','--check'],cwd=root,env=env,check=True)
    subprocess.run([sys.executable,'scripts/start_server.py','--init-only'],cwd=root,env=env,check=True)
    before={name:(runtime/name).read_bytes() for name in ('secret_key','bootstrap_credentials.txt')}
    subprocess.run([sys.executable,'scripts/start_server.py','--init-only'],cwd=root,env=env,check=True)
    assert all((runtime/name).read_bytes()==value for name,value in before.items())
    for name in before:assert (runtime/name).stat().st_mode & 0o077==0
    smoke='''
import base64,os,sqlite3
from pathlib import Path
from app import app
client=app.test_client()
assert client.get('/').status_code==401
assert client.get('/health').status_code==200
headers={'Authorization':'Basic '+base64.b64encode(('reviewer:'+os.environ['THANA_STAGING_PASSWORD']).encode()).decode()}
response=client.get('/',headers=headers,base_url='https://staging.invalid')
assert response.status_code==200 and 'noindex' in response.headers['X-Robots-Tag']
token=client.get('/api/csrf',headers=headers,base_url='https://staging.invalid').json['token']
password=(Path(os.environ['THANA_DATA_DIR'])/'bootstrap_credentials.txt').read_text().split('password: ',1)[1].strip()
response=client.post('/api/login',headers={**headers,'X-CSRF-Token':token},json={'username':'admin','password':password},base_url='https://staging.invalid')
assert response.status_code==200 and 'Secure' in response.headers['Set-Cookie']
assert client.get('/management',headers=headers,base_url='https://staging.invalid').status_code==200
with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
 assert c.execute('SELECT COUNT(*) FROM course_lessons').fetchone()[0]==3
 assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
print('Staging gate, HTTPS cookie, staff login, restart identity and seed checks passed')
'''
    subprocess.run([sys.executable,'-c',smoke],cwd=root,env=env,check=True)
print('Staging rehearsal passed. No online deployment or paid service was created.')
