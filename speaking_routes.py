"""Teacher-authored speaking prompts and private self-reported practice progress."""
import secrets
import time
from flask import jsonify, request, render_template, redirect
from eps_content import DIFFICULTIES


def install_speaking(app, legacy, db, owner):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS speaking_exercises (id TEXT PRIMARY KEY,title TEXT,language TEXT,level TEXT,reference TEXT,translation TEXT,audio TEXT,published INTEGER,revision INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS speaking_progress (owner TEXT,exercise TEXT,revision INTEGER,practiced REAL,PRIMARY KEY(owner,exercise))')

    def staff():
        u=legacy['current_user']()
        return u and u.get('status')=='approved' and u.get('role') in ('admin','superadmin','teacher')

    def audio_asset(c,url):
        if not isinstance(url,str) or not url.startswith('/media/library/'):return None
        return c.execute("SELECT m.*,g.asset AS generated FROM media_assets m LEFT JOIN generated_audio g ON g.asset=m.id WHERE m.filename=? AND m.kind='audio'",(url[len('/media/library/'):],)).fetchone()

    def payload(c,row):
        d=dict(row);asset=audio_asset(c,d['audio'])
        d['audio_ai_generated']=bool(asset and asset['generated'])
        return d

    @app.get('/speaking-studio')
    def speaking_studio():
        return render_template('speaking-studio.html') if staff() else redirect('/admin')

    @app.get('/api/platform/admin/speaking')
    @legacy['content_required']
    def speaking_admin_list():
        with db() as c:items=[payload(c,r) for r in c.execute('SELECT * FROM speaking_exercises ORDER BY title,id')]
        return jsonify(exercises=items)

    @app.post('/api/platform/admin/speaking')
    @legacy['content_required']
    def speaking_save():
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict):return jsonify(error='Invalid exercise'),400
        for key,limit in (('title',200),('reference',500),('translation',1000)):
            if not isinstance(d.get(key,''),str) or len(d.get(key,''))>limit:return jsonify(error='Invalid text'),400
        if not d.get('title','').strip() or not d.get('reference','').strip() or d.get('language') not in ('ko','lo') or d.get('level') not in DIFFICULTIES or type(d.get('published'))!=bool:return jsonify(error='Invalid exercise'),400
        eid=d.get('id');audio=d.get('audio','')
        if not isinstance(audio,str):return jsonify(error='Invalid audio'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            asset=audio_asset(c,audio)
            if audio and not asset:return jsonify(error='Choose library audio'),400
            if d['published'] and (not asset or not asset['published']):return jsonify(error='Publish sample audio before the exercise'),400
            if eid is not None:
                if not isinstance(eid,str):return jsonify(error='Invalid ID'),400
                old=c.execute('SELECT revision FROM speaking_exercises WHERE id=?',(eid,)).fetchone()
                if not old:return jsonify(error='Not found'),404
                if type(d.get('revision'))!=int or d['revision']!=old['revision']:return jsonify(error='Exercise changed; reload before saving'),409
                revision=old['revision']+1
            else:eid=secrets.token_urlsafe(12);revision=1
            c.execute('INSERT OR REPLACE INTO speaking_exercises VALUES (?,?,?,?,?,?,?,?,?)',(eid,d['title'].strip(),d['language'],d['level'],d['reference'].strip(),d.get('translation','').strip(),audio,int(d['published']),revision))
        return jsonify(id=eid,revision=revision)

    @app.get('/api/platform/speaking')
    def speaking_list():
        language=request.args.get('language','ko');level=request.args.get('level','')
        if language not in ('ko','lo') or level not in ('',)+DIFFICULTIES:return jsonify(error='Invalid filter'),400
        username=owner()
        with db() as c:
            rows=c.execute('SELECT e.*,p.practiced,p.revision AS practiced_revision FROM speaking_exercises e LEFT JOIN speaking_progress p ON p.exercise=e.id AND p.owner=? WHERE e.published=1 AND e.language=? ORDER BY e.level,e.title,e.id',(username,language)).fetchall()
            items=[]
            for row in rows:
                asset=audio_asset(c,row['audio'])
                if (level and row['level']!=level) or not asset or not asset['published']:continue
                item=payload(c,row);item['practiced_current']=row['revision']==row['practiced_revision'];items.append(item)
        response=jsonify(exercises=items);response.headers['Cache-Control']='no-store';return response

    @app.post('/api/platform/speaking/<eid>/practice')
    def speaking_practiced(eid):
        if not owner():return jsonify(error='Login required'),401
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict) or d.get('practiced') is not True or type(d.get('revision'))!=int:return jsonify(error='Confirm self-reported practice'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM speaking_exercises WHERE id=? AND published=1',(eid,)).fetchone()
            asset=audio_asset(c,row['audio']) if row else None
            if not row or not asset or not asset['published']:return jsonify(error='Not found'),404
            if row['revision']!=d['revision']:return jsonify(error='Exercise changed; reload'),409
            old=c.execute('SELECT revision,practiced FROM speaking_progress WHERE owner=? AND exercise=?',(owner(),eid)).fetchone()
            practiced=old['practiced'] if old and old['revision']==row['revision'] else time.time()
            c.execute('INSERT OR REPLACE INTO speaking_progress VALUES (?,?,?,?)',(owner(),eid,row['revision'],practiced))
        return jsonify(practiced=practiced,self_reported=True)
