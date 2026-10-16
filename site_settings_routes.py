"""Public homepage copy, edited by administrators with revision protection."""
import json
import re
from urllib.parse import urlparse
from flask import jsonify,request,render_template,redirect

DEFAULTS={
    'hero_lo':'ຮຽນພາສາໃໝ່. ເປີດໂອກາດໃໝ່.',
    'hero_ko':'새로운 언어, 새로운 기회.',
    'subtitle_lo':'ຮຽນຕາມລຳດັບ · ຝຶກທຸກມື້ · ໃຊ້ໄດ້ຈິງ',
    'subtitle_ko':'단계별 학습 · 매일 연습 · 실생활 활용',
    'help_url':'',
}


def valid_help_url(value):
    if not value:return True
    if any(ch.isspace() or ord(ch)<32 or ord(ch)==127 or ch=='\\' for ch in value):return False
    if re.fullmatch(r'/[A-Za-z0-9/_-]*',value) and not value.startswith('//'):return True
    try:
        u=urlparse(value);host=(u.hostname or '').encode('idna').decode('ascii')
        return u.scheme=='https' and bool(host) and re.fullmatch(r'[A-Za-z0-9.-]+',host) is not None and u.username is None and u.password is None and (u.port is None or 1<=u.port<=65535)
    except (ValueError,UnicodeError):return False


def install_site_settings(app,legacy,db):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS site_home_settings (id INTEGER PRIMARY KEY,content TEXT,revision INTEGER)')
        c.execute('INSERT OR IGNORE INTO site_home_settings VALUES (1,?,1)',(json.dumps(DEFAULTS,ensure_ascii=False),))

    def read():
        with db() as c:row=c.execute('SELECT content,revision FROM site_home_settings WHERE id=1').fetchone()
        return {**DEFAULTS,**json.loads(row['content'])},row['revision']

    @app.context_processor
    def homepage_copy():
        return {'site_home':read()[0]} if request.endpoint in ('index','hub') else {}

    @app.get('/site-settings')
    def site_settings_page():
        u=legacy['current_user']()
        if not legacy['has_system_control']():return redirect('/admin')
        return render_template('site-settings.html')

    @app.get('/api/platform/admin/site-settings')
    @legacy['system_required']
    def site_settings_read():
        settings,revision=read();return jsonify(settings=settings,revision=revision,defaults=DEFAULTS)

    @app.post('/api/platform/admin/site-settings')
    @legacy['system_required']
    def site_settings_save():
        d=request.get_json(silent=True) or {};values=d.get('settings') if isinstance(d,dict) else None
        if not isinstance(values,dict) or set(values)!=set(DEFAULTS) or type(d.get('revision'))!=int:return jsonify(error='Invalid settings'),400
        for key,value in values.items():
            if not isinstance(value,str) or len(value)>(500 if key=='help_url' else 300):return jsonify(error='Invalid text'),400
            if key!='help_url' and not value.strip():return jsonify(error='Enter both language texts'),400
        values={key:value.strip() for key,value in values.items()}
        if not valid_help_url(values['help_url']):return jsonify(error='Use an HTTPS link or a local page path'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT revision FROM site_home_settings WHERE id=1').fetchone()
            if d['revision']!=row['revision']:return jsonify(error='Settings changed; reload before saving'),409
            revision=row['revision']+1
            c.execute('UPDATE site_home_settings SET content=?,revision=? WHERE id=1',(json.dumps(values,ensure_ascii=False),revision))
        return jsonify(id=1,revision=revision)
