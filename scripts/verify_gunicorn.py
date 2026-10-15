"""Run a real temporary Gunicorn staging process twice on synthetic data."""
import base64,json,os,secrets,signal,socket,subprocess,sys,tempfile,time,urllib.request,urllib.error
from pathlib import Path
root=Path(__file__).resolve().parents[1]
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
with tempfile.TemporaryDirectory(prefix='thana-gunicorn-') as temporary:
 data=Path(temporary)/'data';password=secrets.token_urlsafe(24)
 env={**os.environ,'PATH':str(Path(sys.executable).parent)+os.pathsep+os.environ['PATH'],'PORT':str(port),'THANA_ENV':'production','THANA_DATA_DIR':str(data),'THANA_PLATFORM_DB':str(data/'platform.sqlite3'),'THANA_STAGING_ENABLED':'1','THANA_STAGING_USER':'reviewer','THANA_STAGING_PASSWORD':password,'THANA_AI_ENABLED':'0','THANA_TTS_ENABLED':'0','THANA_SPEECH_ENABLED':'0'}
 env.pop('THANA_BOOTSTRAP_PASSWORD',None)
 for cycle in range(2):
  with tempfile.TemporaryFile() as logs:
   server=subprocess.Popen([sys.executable,'scripts/start_server.py'],cwd=root,env=env,stdout=logs,stderr=subprocess.STDOUT,start_new_session=True)
   try:
    for _ in range(100):
     if server.poll() is not None:raise RuntimeError('Staging process exited before ready')
     try:
      with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/health',timeout=1) as response:
       assert json.load(response)['status']=='ok'
      break
     except (urllib.error.URLError,TimeoutError):time.sleep(.2)
    else:raise RuntimeError('Health readiness timeout')
    url='http://127.0.0.1:'+str(port)+'/'
    try:urllib.request.urlopen(url,timeout=5);raise AssertionError('Ungated staging')
    except urllib.error.HTTPError as exc:assert exc.code==401
    auth='Basic '+base64.b64encode(('reviewer:'+password).encode()).decode()
    with urllib.request.urlopen(urllib.request.Request(url,headers={'Authorization':auth}),timeout=5) as response:
     assert response.status==200 and 'noindex' in response.headers['X-Robots-Tag']
    identity={name:(data/name).read_bytes() for name in ('secret_key','bootstrap_credentials.txt')}
    if cycle:assert identity==before
    else:before=identity
   finally:
    os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
 print('Real Gunicorn staging health, access gate and restart identity verified twice')
