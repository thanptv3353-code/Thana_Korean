import base64,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from flask import Flask,jsonify
from deployment_config import validate_deployment
from staging_access import install_staging_access

class StagingTests(unittest.TestCase):
 def gate(self,env):
  app=Flask('synthetic-staging')
  with patch.dict(os.environ,env):install_staging_access(app)
  app.add_url_rule('/',endpoint='home',view_func=lambda: 'Synthetic review')
  app.add_url_rule('/api/private',endpoint='private',view_func=lambda: jsonify(value='synthetic'))
  app.add_url_rule('/health',endpoint='health',view_func=lambda: jsonify(status='ok'))
  return app.test_client()
 def test_gate_and_headers(self):
  client=self.gate({'THANA_STAGING_ENABLED':'1','THANA_STAGING_USER':'reviewer','THANA_STAGING_PASSWORD':'synthetic-review-password'})
  for path in ('/','/api/private'):
   r=client.get(path);self.assertEqual(r.status_code,401);self.assertIn('Basic realm',r.headers['WWW-Authenticate']);self.assertEqual(r.headers['Cache-Control'],'no-store')
  self.assertEqual(client.get('/health').status_code,200)
  def header(value):return {'Authorization':'Basic '+base64.b64encode(value.encode()).decode()}
  self.assertEqual(client.get('/',headers=header('reviewer:wrong')).status_code,401)
  r=client.get('/',headers=header('reviewer:synthetic-review-password'))
  self.assertEqual(r.status_code,200);self.assertIn('noindex',r.headers['X-Robots-Tag'])
 def test_missing_configuration_fails_closed(self):
  with self.assertRaises(RuntimeError):self.gate({'THANA_STAGING_ENABLED':'1','THANA_STAGING_PASSWORD':''})
  self.assertEqual(self.gate({'THANA_STAGING_ENABLED':'0'}).get('/').status_code,200)
 def test_deployment_paths(self):
  with tempfile.TemporaryDirectory() as tmp:
   source=Path(tmp)/'source';data=Path(tmp)/'runtime'
   env={'THANA_ENV':'production','THANA_DATA_DIR':str(data),'THANA_PLATFORM_DB':str(data/'platform.sqlite3')}
   self.assertEqual(validate_deployment(env,source)['data'],str(data.resolve()))
   for updates in ({'THANA_ENV':'development'},{'THANA_DATA_DIR':''},{'THANA_PLATFORM_DB':str(source/'platform.sqlite3')},{'THANA_DATA_DIR':str(source/'data'),'THANA_PLATFORM_DB':str(source/'data/platform.sqlite3')},{'PORT':'invalid'},{'THANA_STAGING_ENABLED':'1','THANA_STAGING_PASSWORD':''}):
    with self.assertRaises(ValueError):validate_deployment({**env,**updates},source)

 def test_demo_notice_in_html_only(self):
  app=Flask('demo')
  with patch.dict(os.environ,{'THANA_STAGING_ENABLED':'1','THANA_STAGING_DEMO':'1','THANA_STAGING_PASSWORD':'synthetic-demo-password'}):install_staging_access(app)
  app.add_url_rule('/',endpoint='html',view_func=lambda:'<!doctype html><html><body><h1>Test</h1></body></html>')
  app.add_url_rule('/health',endpoint='health',view_func=lambda:jsonify(status='ok'))
  client=app.test_client();auth={'Authorization':'Basic '+base64.b64encode(b'reviewer:synthetic-demo-password').decode()}
  self.assertIn('STAGING DEMO',client.get('/',headers=auth).text)
  self.assertNotIn('STAGING DEMO',client.get('/health').text)
