"""Editable EPS bank layered over the preserved imported source."""
import json
from eps_content import DIFFICULTIES
from flask import jsonify,request,render_template,redirect

def install_questions(app,legacy,db,questions,by_id):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS eps_bank (id INTEGER PRIMARY KEY, content TEXT, active INTEGER)')
        for q in questions:c.execute('INSERT OR IGNORE INTO eps_bank VALUES (?,?,1)',(q['id'],json.dumps(q,ensure_ascii=False)))
    @app.before_request
    def refresh_bank():
        with db() as c:rows=c.execute('SELECT content FROM eps_bank WHERE active=1 ORDER BY id').fetchall()
        questions[:]=[json.loads(r['content']) for r in rows];by_id.clear();by_id.update({q['id']:q for q in questions})
    def validate(d):
        if not isinstance(d,dict) or d.get('category') not in ('img_word','blank','sign','qa','reading'):return False
        if d.get('type') not in ('text','image_stem','image_choices'):return False
        for k in ('stem_ko','stem_lo','passage_ko','passage_lo','source','subcategory','number_label','image'):
            if not isinstance(d.get(k,''),str) or len(d.get(k,''))>10000:return False
        for k in ('choices_ko','choices_lo'):
            if not isinstance(d.get(k),list) or not 2<=len(d[k])<=6 or not all(isinstance(v,str) and len(v)<=2000 for v in d[k]):return False
        if len(d['choices_ko'])!=len(d['choices_lo']) or type(d.get('answer'))!=int or not 1<=d['answer']<=len(d['choices_ko']) or type(d.get('verified'))!=bool:return False
        if d.get('difficulty', '') not in ('', *DIFFICULTIES):return False
        if any(not isinstance(d.get(k,''),str) or len(d.get(k,''))>10000 for k in ('explanation_ko','explanation_lo')):return False
        image=d.get('image','')
        if image and not (image.startswith('/media/library/') or legacy['re'].fullmatch(r'[A-Za-z0-9_-]+\.png',image)):return False
        return bool(d.get('stem_ko') or image or d.get('passage_ko'))
    @app.get('/question-editor')
    def question_page():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role') not in ('admin','teacher'):return redirect('/admin')
        return render_template('question-editor.html')
    @app.get('/api/platform/admin/bank')
    @legacy['content_required']
    def bank_list():
        with db() as c:
            rows=c.execute('SELECT * FROM eps_bank ORDER BY id').fetchall();reviews={r['qid']:r for r in c.execute('SELECT * FROM reviews')}
        result=[]
        for row in rows:
            q=json.loads(row['content']);q['active']=bool(row['active'])
            if q['id'] in reviews:q['answer']=reviews[q['id']]['answer'];q['verified']=bool(reviews[q['id']]['verified'])
            result.append(q)
        return jsonify(questions=result)
    @app.post('/api/platform/admin/bank')
    @legacy['content_required']
    def bank_save():
        d=request.get_json(silent=True) or {};active=d.pop('active',True);qid=d.pop('id',None)
        if not validate(d) or type(active)!=bool:return jsonify(error='Check fields, choices and answer'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            image=d.get('image','')
            if image.startswith('/media/library/'):
                asset=c.execute('SELECT kind,published FROM media_assets WHERE filename=?',(image[len('/media/library/'):],)).fetchone()
                if not asset or asset['kind']!='image' or (active and not asset['published']):return jsonify(error='Publish a valid library image before activating the question'),400
            if qid is None:qid=c.execute('SELECT COALESCE(MAX(id),0)+1 FROM eps_bank').fetchone()[0]
            elif type(qid)!=int or not c.execute('SELECT 1 FROM eps_bank WHERE id=?',(qid,)).fetchone():return jsonify(error='Not found'),404
            d['id']=qid
            if not d.get('source','').strip():d['source']='custom_'+str(qid)
            c.execute('INSERT OR REPLACE INTO eps_bank VALUES (?,?,?)',(qid,json.dumps(d,ensure_ascii=False),int(active)))
            c.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?)',(qid,d['answer'],int(d['verified']),legacy['current_user']()['username'],legacy['time'].time()))
        return jsonify(id=qid)
