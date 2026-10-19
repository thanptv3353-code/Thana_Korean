"""Staff publication and owned, snapshot-based original EPS practice."""
import json
import random
import secrets
import time
from flask import jsonify,request,render_template
from firebase_curriculum import load_source
from firebase_eps_bank import media_mapping,media_state
from firebase_eps_practice import initialize,available,public_question,unlimited


def install_firebase_practice(app,legacy,db,owner):
    with db() as c:initialize(c)
    labels={c['id']:c.get('title_lao',c['id'])+' / '+c.get('title_korean','') for c in load_source()['eps']}
    @app.post('/api/platform/admin/firebase-eps/<qid>/publication')
    @legacy['content_required']
    def original_eps_publication(qid):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'revision','published'} or type(data['revision']) is not int or type(data['published']) is not bool:return jsonify(error='Invalid publication'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM firebase_eps_bank WHERE id=?',(qid,)).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['revision']!=data['revision']:return jsonify(error='Question changed; reload'),409
            if data['published']:
                if not row['reviewed'] or any(not m['published'] for m in media_state(json.loads(row['content']),media_mapping(c))):return jsonify(error='Review question and publish all required media first'),409
                c.execute('INSERT OR REPLACE INTO firebase_eps_publications VALUES (?,?)',(qid,row['revision']))
            else:c.execute('DELETE FROM firebase_eps_publications WHERE question=?',(qid,))
        return jsonify(published=data['published'])
    @app.get('/original-eps')
    def original_eps_page():return render_template('original-eps.html')
    @app.get('/api/platform/original-eps')
    def original_eps_catalog():
        if not owner():return jsonify(error='Login required'),401
        with db() as c:
            questions=available(c,legacy['current_user']());categories={q['category'] for q in questions}
            history=[dict(row) for row in c.execute('SELECT id,category,created,finished,result FROM firebase_eps_attempts WHERE owner=? AND finished IS NOT NULL ORDER BY finished DESC LIMIT 20',(owner(),))]
            active=c.execute('SELECT id FROM firebase_eps_attempts WHERE owner=? AND finished IS NULL',(owner(),)).fetchone()
            entitled=unlimited(c,legacy['current_user']())
        for row in history:row['result']=json.loads(row['result'])
        return jsonify(categories=[dict(id=cid,label=labels[cid],count=sum(q['category']==cid for q in questions)) for cid in sorted(categories)],unlimited=entitled,active=active['id'] if active else None,history=history)
    def attempt_payload(row):return dict(id=row['id'],category=row['category'],questions=[public_question(q) for q in json.loads(row['snapshot'])],created=row['created'])
    @app.post('/api/platform/original-eps')
    def original_eps_start():
        if not owner():return jsonify(error='Login required'),401
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'category','count'} or not isinstance(data['category'],str) or data['category'] not in labels or type(data['count']) is not int or not 1<=data['count']<=20:return jsonify(error='Invalid practice request'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');active=c.execute('SELECT * FROM firebase_eps_attempts WHERE owner=? AND finished IS NULL',(owner(),)).fetchone()
            if active:return jsonify(**attempt_payload(active),resumed=True)
            pool=[q for q in available(c,legacy['current_user']()) if q['category']==data['category']]
            groups={}
            for q in pool:
                key=q['id'].rsplit('-',1)[0] if q['category']=='listen_story_pair' else q['id'];groups.setdefault(key,[]).append(q)
            groups=list(groups.values());random.shuffle(groups);chosen=[]
            for group in groups:
                if len(chosen)+len(group)<=data['count']:chosen.extend(group)
            if not chosen:return jsonify(error='No available questions; choose another category'),409
            aid=secrets.token_urlsafe(24);created=time.time()
            c.execute('INSERT INTO firebase_eps_attempts VALUES (?,?,?,?,?,NULL,NULL)',(aid,owner(),data['category'],json.dumps(chosen,ensure_ascii=False),created))
        return jsonify(id=aid,category=data['category'],questions=[public_question(q) for q in chosen],created=created,resumed=False)
    @app.get('/api/platform/original-eps/<aid>')
    def original_eps_resume(aid):
        if not owner():return jsonify(error='Login required'),401
        with db() as c:row=c.execute('SELECT * FROM firebase_eps_attempts WHERE id=? AND owner=?',(aid,owner())).fetchone()
        if not row:return jsonify(error='Not found'),404
        if row['finished'] is not None:return jsonify(**attempt_payload(row),result=json.loads(row['result']))
        return jsonify(**attempt_payload(row))
    @app.post('/api/platform/original-eps/<aid>')
    def original_eps_finish(aid):
        if not owner():return jsonify(error='Login required'),401
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'answers'} or not isinstance(data['answers'],dict):return jsonify(error='Invalid answers'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM firebase_eps_attempts WHERE id=? AND owner=?',(aid,owner())).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['finished'] is not None:return jsonify(json.loads(row['result']))
            questions=json.loads(row['snapshot']);byid={q['id']:q for q in questions};answers=data['answers']
            if set(answers)-set(byid) or any(type(v) is not int or not 0<=v<len(byid[k]['choices']) for k,v in answers.items()):return jsonify(error='Invalid answer selection'),400
            paid=unlimited(c,legacy['current_user']())
            if not paid and any(c.execute('SELECT 1 FROM firebase_eps_question_progress WHERE owner=? AND qid=? AND free_used=1',(owner(),qid)).fetchone() for qid in answers):return jsonify(error='Trial already used; cancel and choose other questions'),409
            correct=0;details=[]
            for q in questions:
                given=answers.get(q['id']);detail=dict(id=q['id'],given=given,answered=given is not None)
                if given is not None:
                    ok=given==q['answer'];correct+=int(ok);detail.update(correct=ok,answer=q['answer'],explanation=q['explanation'])
                    c.execute('INSERT INTO firebase_eps_question_progress VALUES (?,?,?,?,?) ON CONFLICT(owner,qid) DO UPDATE SET correct=MAX(correct,excluded.correct),attempted=1,free_used=MAX(free_used,excluded.free_used)',(owner(),q['id'],int(ok),1,int(not paid)))
                details.append(detail)
            result=dict(correct=correct,total=len(questions),answered=len(answers),score=round(100*correct/len(questions)),detail=details,cancelled=False)
            c.execute('UPDATE firebase_eps_attempts SET finished=?,result=? WHERE id=?',(time.time(),json.dumps(result,ensure_ascii=False),aid))
        return jsonify(result)
    @app.post('/api/platform/original-eps/<aid>/cancel')
    def original_eps_cancel(aid):
        if not owner():return jsonify(error='Login required'),401
        if request.get_json(silent=True)!={}:return jsonify(error='Expected empty request'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT finished FROM firebase_eps_attempts WHERE id=? AND owner=?',(aid,owner())).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['finished'] is None:c.execute('UPDATE firebase_eps_attempts SET finished=?,result=? WHERE id=?',(time.time(),json.dumps(dict(cancelled=True,detail=[],answered=0,correct=0,total=0)),aid))
        return jsonify(ok=True)
