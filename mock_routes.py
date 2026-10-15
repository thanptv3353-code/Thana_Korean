"""Timed reading mock exams with server deadlines and saved-answer snapshots."""
import json, random, secrets
from time import time as now
from flask import jsonify, request, render_template

def install_mock(app, legacy, db, owner, questions):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS mock_runs (id TEXT PRIMARY KEY, owner TEXT, questions TEXT, answers TEXT, deadline REAL, finished REAL, result TEXT, created REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS mock_settings (id INTEGER PRIMARY KEY, count INTEGER, seconds INTEGER, verified_only INTEGER)')
        c.execute('INSERT OR IGNORE INTO mock_settings VALUES (1,20,1200,0)')
    def settings():
        with db() as c:return dict(c.execute('SELECT * FROM mock_settings WHERE id=1').fetchone())
    def pool():
        with db() as c:reviews={r['qid']:r for r in c.execute('SELECT * FROM reviews')}
        result=[]
        for original in questions:
            q=dict(original)
            if q['id'] in reviews:q['answer']=reviews[q['id']]['answer'];q['verified']=bool(reviews[q['id']]['verified'])
            result.append(q)
        return result
    def result(row):
        qs=json.loads(row['questions']);answers=json.loads(row['answers'])
        detail=[{'id':q['id'],'category':q['category'],'answer':q['answer'],'given':answers.get(str(q['id'])),'correct':answers.get(str(q['id']))==q['answer'],'verified':q.get('verified',False)} for q in qs]
        categories={}
        for q in detail:
            group=categories.setdefault(q['category'],{'correct':0,'total':0});group['correct']+=int(q['correct']);group['total']+=1
        return {'score':sum(q['correct'] for q in detail),'total':len(detail),'detail':detail,'categories':categories}
    def finalize(c,row):
        if row['finished'] is not None:return json.loads(row['result'])
        r=result(row);c.execute('UPDATE mock_runs SET finished=?,result=? WHERE id=?',(now(),json.dumps(r),row['id']));return r
    def owned(c,aid):return c.execute('SELECT * FROM mock_runs WHERE id=? AND owner=?',(aid,owner())).fetchone()
    @app.get('/mock-exam')
    def mock_page():return render_template('mock.html')
    @app.get('/api/platform/mock/settings')
    def mock_config():return jsonify(settings=settings())
    @app.post('/api/platform/admin/mock/settings')
    @legacy['admin_required']
    def mock_config_save():
        d=request.get_json(silent=True) or {};count=d.get('count');seconds=d.get('seconds');verified=d.get('verified_only')
        if type(count)!=int or not 5<=count<=60 or type(seconds)!=int or not 60<=seconds<=7200 or type(verified)!=bool:return jsonify(error='Invalid settings'),400
        with db() as c:c.execute('UPDATE mock_settings SET count=?,seconds=?,verified_only=? WHERE id=1',(count,seconds,int(verified)))
        return jsonify(ok=True)
    @app.post('/api/platform/mock')
    def mock_start():
        if not owner():return jsonify(error='ກະລຸນາເຂົ້າລະບົບ / 로그인해 주세요'),401
        cfg=settings();bank=pool();bank=[q for q in bank if q.get('verified') or not cfg['verified_only']]
        if len(bank)<cfg['count']:return jsonify(error='ຄຳຖາມທີ່ກວດທານແລ້ວຍັງບໍ່ພຽງພໍ / 검토된 문항이 부족합니다'),409
        groups={}
        for q in bank:
            key='passage:'+q['source'].split('-')[0] if q['category']=='reading' else 'question:'+str(q['id'])
            groups.setdefault(key,[]).append(q)
        chunks=list(groups.values());random.shuffle(chunks);chosen=[]
        for chunk in chunks:
            if len(chosen)+len(chunk)<=cfg['count']:chosen.extend(chunk)
            if len(chosen)==cfg['count']:break
        if len(chosen)!=cfg['count']:return jsonify(error='Cannot assemble complete passage groups'),409
        aid=secrets.token_urlsafe(24);started=now()
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            existing=c.execute('SELECT id FROM mock_runs WHERE owner=? AND finished IS NULL AND deadline>? LIMIT 1',(owner(),started)).fetchone()
            if existing:return jsonify(id=existing['id'],resumed=True)
            c.execute('INSERT INTO mock_runs VALUES (?,?,?,?,?,?,?,?)',(aid,owner(),json.dumps(chosen), '{}',started+cfg['seconds'],None,None,started))
        return jsonify(id=aid,resumed=False),201
    @app.get('/api/platform/mock/<aid>')
    def mock_state(aid):
        if not owner():return jsonify(error='Login required'),401
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=owned(c,aid)
            if not row:return jsonify(error='Not found'),404
            if row['finished'] is not None or now()>=row['deadline']:return jsonify(finished=True,result=finalize(c,row))
        return jsonify(id=aid,finished=False,remaining=max(0,row['deadline']-now()),answers=json.loads(row['answers']),questions=[{k:v for k,v in q.items() if k not in ('answer','source')} for q in json.loads(row['questions'])])
    @app.post('/api/platform/mock/<aid>/answer')
    def mock_save_answer(aid):
        if not owner():return jsonify(error='Login required'),401
        d=request.get_json(silent=True) or {};qid=d.get('id');choice=d.get('choice')
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=owned(c,aid)
            if not row:return jsonify(error='Not found'),404
            if row['finished'] is not None or now()>=row['deadline']:return jsonify(error='ໝົດເວລາ / 시간이 종료되었습니다',finished=True,result=finalize(c,row)),409
            bank={q['id']:q for q in json.loads(row['questions'])}
            if type(qid)!=int or qid not in bank or type(choice)!=int or not 1<=choice<=len(bank[qid]['choices_ko']):return jsonify(error='Invalid answer'),400
            answers=json.loads(row['answers']);answers[str(qid)]=choice
            c.execute('UPDATE mock_runs SET answers=? WHERE id=?',(json.dumps(answers),aid))
        return jsonify(saved=True)
    @app.post('/api/platform/mock/<aid>/finish')
    def mock_finish(aid):
        if not owner():return jsonify(error='Login required'),401
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=owned(c,aid)
            if not row:return jsonify(error='Not found'),404
            return jsonify(finished=True,result=finalize(c,row))
    @app.get('/api/platform/mock/history')
    def mock_history():
        if not owner():return jsonify(error='Login required'),401
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            for row in c.execute('SELECT * FROM mock_runs WHERE owner=? AND finished IS NULL AND deadline<=?',(owner(),now())).fetchall():finalize(c,row)
            rows=c.execute('SELECT id,finished,result FROM mock_runs WHERE owner=? AND finished IS NOT NULL ORDER BY finished DESC LIMIT 20',(owner(),)).fetchall()
        return jsonify(attempts=[{'id':r['id'],'finished':r['finished'],'result':json.loads(r['result'])} for r in rows])
