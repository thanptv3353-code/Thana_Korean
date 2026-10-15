"""Self-rated spaced vocabulary review, scoped to each approved learner."""
import time
from datetime import datetime,timezone,timedelta
from flask import jsonify,request,render_template

def install_review(app,legacy,db,owner):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS saved_words (owner TEXT, word TEXT, PRIMARY KEY(owner,word))')
        c.execute('CREATE TABLE IF NOT EXISTS word_reviews (owner TEXT, word TEXT, due REAL, days INTEGER, reviewed REAL, PRIMARY KEY(owner,word))')
    @app.get('/api/platform/saved-words')
    def saved_words():
        if not owner():return jsonify(error='Login required'),401
        with db() as c:rows=c.execute('SELECT s.word FROM saved_words s JOIN vocabulary v ON v.id=s.word WHERE s.owner=? AND v.published=1',(owner(),)).fetchall()
        return jsonify(ids=[r['word'] for r in rows])
    @app.post('/api/platform/saved-words/<wid>')
    def save_personal_word(wid):
        if not owner():return jsonify(error='Login required'),401
        saved=(request.get_json(silent=True) or {}).get('saved')
        if type(saved)!=bool:return jsonify(error='Invalid setting'),400
        with db() as c:
            if not c.execute('SELECT 1 FROM vocabulary WHERE id=? AND published=1',(wid,)).fetchone():return jsonify(error='Not found'),404
            if saved:c.execute('INSERT OR IGNORE INTO saved_words VALUES (?,?)',(owner(),wid))
            else:c.execute('DELETE FROM saved_words WHERE owner=? AND word=?',(owner(),wid))
        return jsonify(saved=saved)
    @app.get('/review')
    def review_page():return render_template('review.html')
    @app.get('/api/platform/review')
    def due_words():
        if not owner():return jsonify(error='ກະລຸນາເຂົ້າລະບົບ / 로그인해 주세요'),401
        scope=request.args.get('scope','all')
        if scope not in ('all','saved'):return jsonify(error='Invalid scope'),400
        saved_filter=" AND EXISTS(SELECT 1 FROM saved_words s WHERE s.word=v.id AND s.owner=?)" if scope=='saved' else ''
        params=(owner(),time.time())+((owner(),) if scope=='saved' else ())
        with db() as c:
            rows=c.execute('SELECT v.*,r.due FROM vocabulary v LEFT JOIN word_reviews r ON r.word=v.id AND r.owner=? WHERE v.published=1 AND (r.due IS NULL OR r.due<=?) '+saved_filter+' ORDER BY COALESCE(r.due,0),v.ko LIMIT 20',params).fetchall()
            total=c.execute('SELECT COUNT(*) FROM vocabulary v LEFT JOIN word_reviews r ON r.word=v.id AND r.owner=? WHERE v.published=1 AND (r.due IS NULL OR r.due<=?)'+saved_filter,params).fetchone()[0]
        return jsonify(words=[dict(r) for r in rows],total=total)
    @app.post('/api/platform/review/<wid>')
    def rate_word(wid):
        if not owner():return jsonify(error='Login required'),401
        grade=(request.get_json(silent=True) or {}).get('grade')
        if grade not in ('again','good','easy'):return jsonify(error='Invalid rating'),400
        now=time.time()
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT id FROM vocabulary WHERE id=? AND published=1',(wid,)).fetchone():return jsonify(error='Not found'),404
            r=c.execute('SELECT * FROM word_reviews WHERE owner=? AND word=?',(owner(),wid)).fetchone()
            if r and r['due']>now:return jsonify(error='Already reviewed; wait until the next due time'),409
            days=0 if grade=='again' else min(30,max(1,(r['days'] if r else 0)*2)+(1 if grade=='easy' else 0))
            due=now+(300 if grade=='again' else days*86400)
            c.execute('INSERT OR REPLACE INTO word_reviews VALUES (?,?,?,?,?)',(owner(),wid,due,days,now))
        return jsonify(due=due,days=days)
