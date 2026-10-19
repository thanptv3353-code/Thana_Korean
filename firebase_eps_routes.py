"""Authenticated source-question review; no learner publication or provider calls."""
import json
import time
from flask import jsonify,render_template,redirect,request
from firebase_curriculum import load_source
from firebase_eps_bank import initialize,import_bank,media_paths,media_mapping,media_state


def install_firebase_eps(app,legacy,db):
    with db() as c:initialize(c)
    category_titles={c['id']:c.get('title_lao',c['id'])+' / '+c.get('title_korean','') for c in load_source()['eps']}
    @app.get('/firebase-eps-review')
    def firebase_eps_page():
        user=legacy['current_user']()
        if not user or user.get('status')!='approved' or user.get('role') not in ('admin','superadmin','teacher'):return redirect('/account')
        return render_template('firebase-eps-review.html')
    @app.post('/api/platform/admin/firebase-eps/import')
    @legacy['admin_required']
    def firebase_eps_import():
        data=request.get_json(silent=True)
        if data!={}:return jsonify(error='Expected an empty import request'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');added=import_bank(c,load_source())
        return jsonify(added=added,published=0,source='Public original pack; private overrides require runtime migration')
    @app.get('/api/platform/admin/firebase-eps')
    @legacy['content_required']
    def firebase_eps_list():
        try:page=int(request.args.get('page','1'))
        except ValueError:return jsonify(error='Invalid page'),400
        category=request.args.get('category','');term=request.args.get('q','').strip()[:200];state=request.args.get('state','')
        if not 1<=page<=100000 or state not in ('','text','media','reviewed','unreviewed'):return jsonify(error='Invalid filter'),400
        with db() as c:
            rows=c.execute('SELECT * FROM firebase_eps_bank ORDER BY category,id').fetchall();mapping=media_mapping(c);publications={r['question']:r['revision'] for r in c.execute('SELECT * FROM firebase_eps_publications')}
        categories=sorted({row['category'] for row in rows})
        if category and category not in categories:return jsonify(error='Invalid category'),400
        items=[]
        for row in rows:
            question=json.loads(row['content']);media=media_state(question,mapping);paths=[m['path'] for m in media if not m['published']];reviewed=bool(row['reviewed']) and not paths
            if category and row['category']!=category:continue
            if term and term.casefold() not in (row['id']+' '+question['question_text']+' '+(question.get('explanation_lao') or '')).casefold():continue
            if state=='text' and media or state=='media' and not paths or state=='reviewed' and not reviewed or state=='unreviewed' and reviewed:continue
            items.append(dict(id=row['id'],category=row['category'],question=question,revision=row['revision'],reviewed=bool(reviewed),missing_media=paths,media=media,published=bool(reviewed and publications.get(row['id'])==row['revision'])))
        return jsonify(questions=items[(page-1)*20:page*20],total=len(items),page=page,categories=categories,category_titles=category_titles,bank_total=len(rows),published=sum(item['published'] for item in items))
    @app.post('/api/platform/admin/firebase-eps/<qid>')
    @legacy['content_required']
    def firebase_eps_review(qid):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'revision','answer','explanation','reviewed'} or type(data['revision']) is not int or type(data['answer']) is not int or type(data['reviewed']) is not bool or not isinstance(data['explanation'],str) or len(data['explanation'])>10000:return jsonify(error='Invalid review'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM firebase_eps_bank WHERE id=?',(qid,)).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['revision']!=data['revision']:return jsonify(error='Question changed; reload'),409
            question=json.loads(row['content'])
            if not 0<=data['answer']<len(question['choices']):return jsonify(error='Invalid answer'),400
            if data['reviewed'] and any(not item['published'] for item in media_state(question,media_mapping(c))):return jsonify(error='Required media is not mapped; review remains incomplete'),409
            question['correct_answer_index']=data['answer'];question['explanation_lao']=data['explanation']
            c.execute('UPDATE firebase_eps_bank SET content=?,revision=revision+1,reviewed=?,updated=? WHERE id=?',(json.dumps(question,ensure_ascii=False),int(data['reviewed']),time.time(),qid))
        return jsonify(revision=row['revision']+1,reviewed=data['reviewed'],published=False)

    @app.post('/api/platform/admin/firebase-eps/<qid>/media')
    @legacy['content_required']
    def firebase_eps_map_media(qid):
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'path','asset','revision','question_revision'} or not isinstance(data['path'],str) or type(data['revision']) is not int or type(data['question_revision']) is not int or (data['asset'] is not None and (not isinstance(data['asset'],str) or not 1<=len(data['asset'])<=100)):return jsonify(error='Invalid media mapping'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT content,revision FROM firebase_eps_bank WHERE id=?',(qid,)).fetchone()
            if not row:return jsonify(error='Not found'),404
            if row['revision']!=data['question_revision']:return jsonify(error='Question changed; reload'),409
            if data['path'] not in media_paths(json.loads(row['content'])):return jsonify(error='Media path does not belong to this question'),400
            old=c.execute('SELECT asset,revision FROM firebase_eps_media_map WHERE path=?',(data['path'],)).fetchone()
            revision=old['revision'] if old else 0
            if data['revision']!=revision:return jsonify(error='Media mapping changed; reload'),409
            if data['asset'] is not None:
                asset=c.execute('SELECT kind,filename FROM media_assets WHERE id=?',(data['asset'],)).fetchone()
                expected='audio' if data['path'].startswith('audio/') else 'image'
                if not asset or asset['kind']!=expected:return jsonify(error='Choose matching library media'),400
            if (old['asset'] if old else None)==data['asset']:return jsonify(changed=False,revision=revision,affected=0)
            c.execute('INSERT INTO firebase_eps_media_map VALUES (?,?,?) ON CONFLICT(path) DO UPDATE SET asset=excluded.asset,revision=excluded.revision',(data['path'],data['asset'],revision+1))
            affected=0
            for question in c.execute('SELECT id,content FROM firebase_eps_bank').fetchall():
                if data['path'] in media_paths(json.loads(question['content'])):
                    c.execute('UPDATE firebase_eps_bank SET reviewed=0,revision=revision+1,updated=? WHERE id=?',(time.time(),question['id']));affected+=1
        return jsonify(changed=True,revision=revision+1,affected=affected,published=False)
