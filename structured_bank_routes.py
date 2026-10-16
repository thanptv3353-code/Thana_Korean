"""Shared staff-only mixed-format bank; lessons keep independent question copies."""
import json,secrets,time
from flask import jsonify,request
import quiz_engine

FIELDS={'type','question','options','answer','accepted','pairs','explanation','category','difficulty','source','image_url','audio_url'}

def install_structured_bank(app,legacy,db):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS structured_question_bank (id TEXT PRIMARY KEY,language TEXT,content TEXT,revision INTEGER,archived INTEGER,updated REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS structured_question_versions (question TEXT,revision INTEGER,content TEXT,actor TEXT,created REAL,PRIMARY KEY(question,revision))')

    @app.get('/api/platform/admin/lesson-question-bank')
    @legacy['content_required']
    def structured_bank_list():
        language=request.args.get('language','ko');kind=request.args.get('type','');term=request.args.get('q','').strip()[:200];archived=request.args.get('archived','0')
        try:page=int(request.args.get('page','1'))
        except ValueError:return jsonify(error='Invalid page'),400
        if language not in ('ko','lo') or kind not in ('','choice','blank','matching','ordering') or archived not in ('0','1') or not 1<=page<=100000:return jsonify(error='Invalid filter'),400
        with db() as c:
            rows=c.execute('SELECT * FROM structured_question_bank WHERE language=? AND archived=? ORDER BY updated DESC,id',(language,int(archived))).fetchall()
            items=[]
            for row in rows:
                q=json.loads(row['content'])
                if kind and q.get('type','choice')!=kind:continue
                if term and term.casefold() not in (q['question']+' '+q.get('category','')).casefold():continue
                items.append({'id':row['id'],'language':row['language'],'question':q,'revision':row['revision'],'archived':bool(row['archived'])})
        response=jsonify(questions=items[(page-1)*30:page*30],total=len(items),page=page,page_size=30);response.headers['Cache-Control']='no-store';return response

    @app.post('/api/platform/admin/lesson-question-bank')
    @legacy['content_required']
    def structured_bank_save():
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)-{'id','revision','language','question','archived'} or d.get('language') not in ('ko','lo') or type(d.get('archived')) is not bool:return jsonify(error='Invalid bank entry'),400
        q=d.get('question')
        if not isinstance(q,dict) or set(q)-FIELDS or not quiz_engine.valid(q):return jsonify(error='Invalid question'),400
        qid=d.get('id')
        if qid is not None and (not isinstance(qid,str) or not qid or len(qid)>100):return jsonify(error='Invalid ID'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            for key,kind in (('image_url','image'),('audio_url','audio')):
                if q.get(key) and not c.execute('SELECT 1 FROM media_assets WHERE filename=? AND kind=?',(q[key].split('/')[-1],kind)).fetchone():return jsonify(error='Use valid library media'),400
            if qid is not None:
                old=c.execute('SELECT revision FROM structured_question_bank WHERE id=?',(qid,)).fetchone()
                if not old:return jsonify(error='Not found'),404
                if type(d.get('revision')) is not int or d['revision']!=old['revision']:return jsonify(error='Bank entry changed; reload before saving'),409
                revision=old['revision']+1
            else:
                if 'revision' in d:return jsonify(error='New entries have no revision'),400
                qid=secrets.token_urlsafe(12);revision=1
            payload=json.dumps(q,ensure_ascii=False);now=time.time()
            c.execute('INSERT INTO structured_question_bank VALUES (?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET language=excluded.language,content=excluded.content,revision=excluded.revision,archived=excluded.archived,updated=excluded.updated',(qid,d['language'],payload,revision,int(d['archived']),now))
            c.execute('INSERT INTO structured_question_versions VALUES (?,?,?,?,?)',(qid,revision,payload,legacy['current_user']()['username'],now))
        return jsonify(id=qid,revision=revision)
