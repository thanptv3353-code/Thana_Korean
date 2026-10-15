"""Moderated local learning discussions; new posts require staff review."""
import time,secrets
from flask import jsonify,request,render_template

def install_community(app,legacy,db,owner):
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS community_posts (id TEXT PRIMARY KEY, owner TEXT, name TEXT, language TEXT, text TEXT, status TEXT, created REAL)')
    @app.get('/community')
    def community_page():return render_template('community.html')
    @app.get('/api/platform/community')
    def community_list():
        with db() as c:rows=c.execute("SELECT * FROM community_posts WHERE status='approved' OR owner=? ORDER BY created DESC LIMIT 100",(owner(),)).fetchall()
        return jsonify(posts=[{k:r[k] for k in ('id','name','language','text','status','created')} for r in rows])
    @app.post('/api/platform/community')
    def community_post():
        if not owner():return jsonify(error='Login required'),401
        d=request.get_json(silent=True) or {};text=d.get('text');language=d.get('language')
        if not isinstance(text,str) or not 1<=len(text.strip())<=2000 or language not in ('ko','lo'):return jsonify(error='Write 1–2000 characters'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute('SELECT COUNT(*) FROM community_posts WHERE owner=? AND created>?',(owner(),time.time()-60)).fetchone()[0]>=3:return jsonify(error='Please wait before posting again'),429
            pid=secrets.token_urlsafe(12);c.execute('INSERT INTO community_posts VALUES (?,?,?,?,?,?,?)',(pid,owner(),legacy['current_user']()['name'],language,text.strip(),'pending',time.time()))
        return jsonify(id=pid,status='pending'),201
    @app.get('/api/platform/admin/community')
    @legacy['content_required']
    def community_pending():
        with db() as c:rows=c.execute("SELECT * FROM community_posts WHERE status='pending' ORDER BY created").fetchall()
        return jsonify(posts=[dict(r) for r in rows])
    @app.post('/api/platform/admin/community/<pid>')
    @legacy['content_required']
    def moderate_post(pid):
        status=(request.get_json(silent=True) or {}).get('status')
        if status not in ('approved','rejected'):return jsonify(error='Invalid moderation'),400
        with db() as c:
            if not c.execute('SELECT 1 FROM community_posts WHERE id=?',(pid,)).fetchone():return jsonify(error='Not found'),404
            c.execute('UPDATE community_posts SET status=? WHERE id=?',(status,pid))
        return jsonify(ok=True)
