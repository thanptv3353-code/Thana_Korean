"""Additive platform routes; legacy lessons and account records remain intact."""
import json, os, secrets, sqlite3, time
from contextlib import contextmanager
from flask import jsonify, request, session, render_template

def install(app, legacy):
    root=legacy['BASE']
    with open(os.path.join(root,'data/eps_questions.json'),encoding='utf-8') as f:
        questions=json.load(f)
    by_id={q['id']:q for q in questions}
    dbpath=os.environ.get('THANA_PLATFORM_DB',os.path.join(root,'data/platform.sqlite3'))
    @contextmanager
    def db():
        c=sqlite3.connect(dbpath); c.row_factory=sqlite3.Row
        c.execute('CREATE TABLE IF NOT EXISTS attempts (id TEXT PRIMARY KEY, owner TEXT, category TEXT, ids TEXT, answers TEXT, created REAL, finished REAL, score INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS reviews (qid INTEGER PRIMARY KEY, answer INTEGER, verified INTEGER, reviewer TEXT, updated REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS snapshots (attempt TEXT PRIMARY KEY, questions TEXT)')
        c.commit()
        try:
            with c:
                yield c
        finally:
            c.close()
    with db() as c:
        for r in c.execute('SELECT * FROM reviews'):
            if r['qid'] in by_id:
                by_id[r['qid']]['answer']=r['answer']; by_id[r['qid']]['verified']=bool(r['verified'])
    def owner():
        u=legacy['current_user']()
        return u['username'] if u and u.get('status')=='approved' else None
    @app.get('/hub')
    def hub(): return render_template('hub.html')
    @app.get('/api/platform/catalog')
    def catalog():
        with db() as c:
            lao_available=bool(c.execute("SELECT 1 FROM courses c JOIN course_lessons l ON c.id=l.course WHERE c.language='lo' AND l.published IS NOT NULL LIMIT 1").fetchone())
        return jsonify(categories=[{'id':k,'count':sum(q['category']==k for q in questions)} for k in sorted({q['category'] for q in questions})], tracks=[{'id':'ko','label':'ຮຽນພາສາເກົາຫຼີ','available':True},{'id':'lo','label':'라오어 배우기','available':lao_available}], user=({'name':legacy['current_user']()['name']} if owner() else None))
    @app.get('/api/platform/sample')
    def sample():
        ls=legacy['sorted_lessons']()
        if not ls: return jsonify(error='No lesson'),404
        l=ls[0]
        return jsonify(title=l['title_lo'],title_ko=l.get('title_ko',''),description=l.get('description',''),questions=legacy['public_questions'](l['quiz'][:3]))
    @app.post('/api/platform/practice')
    def start():
        if not owner(): return jsonify(error='ກະລຸນາເຂົ້າລະບົບ / 로그인해 주세요'),401
        d=request.get_json(silent=True) or {}; cat=d.get('category')
        if cat not in {q['category'] for q in questions}: return jsonify(error='Invalid category'),400
        # Keep passage groups together; practice has no official exam timer.
        pool=[q for q in questions if q['category']==cat]
        import random
        if cat=='reading':
            groups={}
            for q in pool: groups.setdefault(q['source'].split('-')[0],[]).append(q)
            chunks=list(groups.values()); random.shuffle(chunks); chosen=[]
            for chunk in chunks:
                if len(chosen)+len(chunk)>15 and chosen: break
                chosen.extend(chunk)
        else: chosen=random.sample(pool,min(10,len(pool)))
        with db() as c:
            reviews={r['qid']:r for r in c.execute('SELECT * FROM reviews')}
        chosen=[dict(q) for q in chosen]
        for q in chosen:
            if q['id'] in reviews:
                q['answer']=reviews[q['id']]['answer']; q['verified']=bool(reviews[q['id']]['verified'])
        aid=secrets.token_urlsafe(24)
        with db() as c:
            c.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',(aid,owner(),cat,json.dumps([q['id'] for q in chosen]),None,time.time(),None,None))
            c.execute('INSERT INTO snapshots VALUES (?,?)',(aid,json.dumps(chosen)))
        return jsonify(id=aid,questions=[{k:v for k,v in q.items() if k not in ('answer','source')} for q in chosen])
    @app.post('/api/platform/practice/<aid>/retry')
    def retry_incorrect(aid):
        if not owner():return jsonify(error='Login required'),401
        with db() as c:
            row=c.execute('SELECT * FROM attempts WHERE id=? AND owner=?',(aid,owner())).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['finished'] is None:return jsonify(error='Finish the original attempt first'),409
            snapshot=c.execute('SELECT questions FROM snapshots WHERE attempt=?',(aid,)).fetchone()
            if not snapshot:return jsonify(error='Original question snapshot unavailable'),409
            original=json.loads(snapshot['questions']);answers=json.loads(row['answers'])
            wrong=[q for q in original if answers.get(str(q['id']))!=q['answer']]
            if not wrong:return jsonify(error='ບໍ່ມີຂໍ້ທີ່ຕອບຜິດ / 틀린 문제가 없습니다'),409
            # A reading retry retains the complete original passage group.
            sources={q['source'].split('-')[0] for q in wrong} if row['category']=='reading' else set()
            chosen=[q for q in original if q in wrong or (sources and q['source'].split('-')[0] in sources)]
            retry=secrets.token_urlsafe(24)
            c.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',(retry,owner(),row['category'],json.dumps([q['id'] for q in chosen]),None,time.time(),None,None))
            c.execute('INSERT INTO snapshots VALUES (?,?)',(retry,json.dumps(chosen)))
        return jsonify(id=retry,questions=[{k:v for k,v in q.items() if k not in ('answer','source')} for q in chosen])
    @app.post('/api/platform/practice/<aid>')
    def finish(aid):
        if not owner(): return jsonify(error='Login required'),401
        answers=(request.get_json(silent=True) or {}).get('answers')
        if not isinstance(answers,dict): return jsonify(error='Invalid answers'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT * FROM attempts WHERE id=? AND owner=?',(aid,owner())).fetchone()
            if not row: return jsonify(error='Not found'),404
            ids=json.loads(row['ids'])
            snapshot=c.execute('SELECT questions FROM snapshots WHERE attempt=?',(aid,)).fetchone()
            bank={q['id']:q for q in json.loads(snapshot['questions'])} if snapshot else by_id
            if set(answers)-{str(i) for i in ids}: return jsonify(error='Unexpected question'),400
            if any(type(v)!=int or not 1<=v<=len(bank[int(k)]['choices_ko']) for k,v in answers.items()): return jsonify(error='Invalid choice'),400
            if row['finished']: answers=json.loads(row['answers'])
            detail=[{'id':i,'answer':bank[i]['answer'],'given':answers.get(str(i)),'correct':answers.get(str(i))==bank[i]['answer'],'verified':bank[i].get('verified',False)} for i in ids]
            score=sum(q['correct'] for q in detail)
            if not row['finished']: c.execute('UPDATE attempts SET answers=?,finished=?,score=? WHERE id=?',(json.dumps(answers),time.time(),score,aid))
        return jsonify(score=score,total=len(ids),detail=detail)
    @app.get('/api/platform/history')
    def history():
        if not owner(): return jsonify(error='Login required'),401
        with db() as c: rows=c.execute('SELECT id,category,created,finished,score,ids FROM attempts WHERE owner=? AND finished IS NOT NULL ORDER BY created DESC LIMIT 20',(owner(),)).fetchall()
        return jsonify(attempts=[{'id':r['id'],'category':r['category'],'score':r['score'],'total':len(json.loads(r['ids'])),'finished':r['finished']} for r in rows])

    @app.get('/studio')
    def studio():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role')!='admin':
            from flask import redirect
            return redirect('/admin')
        return render_template('studio.html')
    @app.get('/api/platform/admin/questions')
    @legacy['admin_required']
    def review_questions():
        with db() as c:
            for r in c.execute('SELECT * FROM reviews'):
                if r['qid'] in by_id:
                    by_id[r['qid']]['answer']=r['answer']; by_id[r['qid']]['verified']=bool(r['verified'])
        return jsonify(questions=questions)
    @app.post('/api/platform/admin/questions/<int:qid>')
    @legacy['admin_required']
    def review_question(qid):
        q=by_id.get(qid)
        if not q: return jsonify(error='Not found'),404
        d=request.get_json(silent=True) or {}; answer=d.get('answer'); verified=d.get('verified')
        if type(answer)!=int or not 1<=answer<=len(q['choices_ko']) or type(verified)!=bool: return jsonify(error='Invalid review'),400
        with db() as c: c.execute('INSERT OR REPLACE INTO reviews VALUES (?,?,?,?,?)',(qid,answer,int(verified),owner(),time.time()))
        q['answer']=answer; q['verified']=verified
        return jsonify(ok=True)

    from course_routes import install_courses
    install_courses(app, legacy, db, owner)
    from mock_routes import install_mock
    install_mock(app, legacy, db, owner, questions)
    from vocabulary_routes import install_vocabulary
    install_vocabulary(app, legacy, db, owner)
    from review_routes import install_review
    install_review(app, legacy, db, owner)

    from account_routes import install_accounts
    install_accounts(app, legacy, db, owner)
    from membership_routes import install_membership
    install_membership(app, legacy, db, owner)
    from management_routes import install_management
    install_management(app, legacy, db, owner)
    from community_routes import install_community
    install_community(app, legacy, db, owner)
    from tutor_routes import install_tutor
    install_tutor(app, legacy, db, owner)
    from media_routes import install_media
    install_media(app, legacy, db, owner)
    from question_routes import install_questions
    install_questions(app, legacy, db, questions, by_id)
    from oauth_routes import install_oauth
    install_oauth(app, legacy)
    from speech_routes import install_speech
    install_speech(app, legacy, db, owner)
    from tts_routes import install_tts
    install_tts(app, legacy, db, owner)
