import json,os,secrets,sqlite3,unittest
from test_platform import legacy
from site_settings_routes import DEFAULTS


class SiteSettingsTests(unittest.TestCase):
    def setUp(self):
        self.name='site_settings_'+secrets.token_hex(4);self.c=legacy.app.test_client()
        legacy.users[self.name]={'username':self.name,'name':'Synthetic site editor','role':'admin','status':'approved'};legacy._save(legacy.USERS_FILE,legacy.users)
        with self.c.session_transaction() as s:s['username']=self.name
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:self.original=c.execute('SELECT content,revision FROM site_home_settings WHERE id=1').fetchone()

    def tearDown(self):
        with sqlite3.connect(os.environ['THANA_PLATFORM_DB']) as c:
            c.execute('UPDATE site_home_settings SET content=?,revision=? WHERE id=1',self.original)
            c.execute('DELETE FROM audit_log WHERE actor=?',(self.name,))
        legacy.users.pop(self.name,None);legacy._save(legacy.USERS_FILE,legacy.users)

    def save(self,values,revision=None):
        if revision is None:revision=self.c.get('/api/platform/admin/site-settings').json['revision']
        token=self.c.get('/api/csrf').json['token'];return self.c.post('/api/platform/admin/site-settings',json={'settings':values,'revision':revision},headers={'X-CSRF-Token':token})

    def test_homepage_copy_is_plain_text_and_revision_guarded(self):
        d=self.c.get('/api/platform/admin/site-settings').json
        values={**DEFAULTS,'hero_lo':'<script>synthetic()</script>','hero_ko':'Synthetic Korean heading','help_url':'https://example.test/help?a=1&b=2'}
        r=self.save(values,d['revision']);self.assertEqual(r.status_code,200)
        self.assertEqual(self.c.get('/api/platform/admin/site-settings').json['settings'],values)
        public=legacy.app.test_client().get('/').get_data(as_text=True)
        self.assertIn('&lt;script&gt;synthetic()&lt;/script&gt;',public);self.assertNotIn('<script>synthetic()</script>',public)
        self.assertIn('Synthetic Korean heading',public);self.assertIn('https://example.test/help?a=1&amp;b=2',public)
        self.assertIn('THANA KOREAN',public)
        self.assertEqual(self.save(DEFAULTS,d['revision']).status_code,409)
        self.assertEqual(self.c.get('/api/platform/admin/site-settings').json['settings'],values)
        events=self.c.get('/api/platform/admin/audit?q='+self.name).json['events'];self.assertEqual(events[0]['action'],'site_settings_save');self.assertNotIn('synthetic()',json.dumps(events))

    def test_invalid_urls_and_fields_leave_settings_unchanged(self):
        before=self.c.get('/api/platform/admin/site-settings').json
        for url in ('javascript:alert(1)','http://example.test','//example.test','https://user:secret@example.test','https://example.test:999999','https://example.test/a\nb','/\\example.test','/path?next=//example.test'):
            self.assertEqual(self.save({**DEFAULTS,'help_url':url}).status_code,400,url)
        for values in ({**DEFAULTS,'hero_lo':''},{**DEFAULTS,'hero_ko':'x'*301},{**DEFAULTS,'subtitle_lo':True},{**DEFAULTS,'brand':'Other'}):
            self.assertEqual(self.save(values).status_code,400)
        self.assertEqual(self.c.get('/api/platform/admin/site-settings').json,before)
        self.assertEqual(self.save({**DEFAULTS,'help_url':'/account'}).status_code,200)
        self.assertIn('href="/account"',legacy.app.test_client().get('/').get_data(as_text=True))
        self.assertEqual(self.save(DEFAULTS).status_code,200)
        self.assertNotIn('도움말 / 문의',legacy.app.test_client().get('/').get_data(as_text=True))

    def test_admin_only(self):
        self.assertEqual(self.c.get('/site-settings').status_code,200)
        for role in ('teacher','student'):
            legacy.users[self.name]['role']=role;legacy._save(legacy.USERS_FILE,legacy.users)
            self.assertEqual(self.c.get('/site-settings').status_code,302)
            self.assertEqual(self.c.get('/api/platform/admin/site-settings').status_code,403)
            self.assertEqual(self.save(DEFAULTS,1).status_code,403)
        self.assertEqual(legacy.app.test_client().get('/api/platform/admin/site-settings').status_code,403)

    def test_hub_alias_uses_same_homepage_context(self):
        self.assertEqual(self.c.get('/hub').status_code,200)
        self.save({**DEFAULTS,'hero_lo':'Synthetic alias heading'})
        self.assertIn('Synthetic alias heading',self.c.get('/hub').get_data(as_text=True))
