"""Owner-only EPS exposure statistics from completed immutable attempt data."""
import json
import time
from flask import jsonify, request, render_template
from eps_content import question_skill


def install_analysis(app, legacy, db, owner):
    @app.get('/learning-analysis')
    def learning_analysis_page():return render_template('learning-analysis.html')

    @app.get('/api/platform/learning-analysis')
    def learning_analysis():
        username=owner()
        if not username:return jsonify(error='Login required'),401
        try:days=int(request.args.get('days','30'))
        except ValueError:return jsonify(error='Invalid period'),400
        if days not in (7,30,90,365):return jsonify(error='Invalid period'),400
        cutoff=time.time()-days*86400
        groups={};attempts={'practice':0,'mock':0};missing=0

        def add(mode,skill,category,correct,given,verified):
            key=(mode,skill,category)
            g=groups.setdefault(key,{'mode':mode,'skill':skill,'category':category,'correct':0,'total':0,'unanswered':0,'unverified':0})
            g['total']+=1;g['correct']+=int(correct);g['unanswered']+=int(given is None);g['unverified']+=int(not verified)

        with db() as c:
            rows=c.execute('SELECT a.answers,s.questions FROM attempts a LEFT JOIN snapshots s ON s.attempt=a.id WHERE a.owner=? AND a.finished IS NOT NULL AND a.finished>=?',(username,cutoff)).fetchall()
            for row in rows:
                if not row['questions']:missing+=1;continue
                attempts['practice']+=1;answers=json.loads(row['answers'])
                for q in json.loads(row['questions']):
                    given=answers.get(str(q['id']))
                    add('practice',question_skill(q),q['category'],given==q['answer'],given,q.get('verified',False))
            for row in c.execute('SELECT result FROM mock_runs WHERE owner=? AND finished IS NOT NULL AND finished>=?',(username,cutoff)):
                r=json.loads(row['result']);attempts['mock']+=1
                for q in r['detail']:
                    add('mock',r.get('skill','reading'),q['category'],q['correct'],q.get('given'),q.get('verified',False))
        items=list(groups.values())
        for g in items:g['percent']=round(100*g['correct']/g['total'],1)
        items.sort(key=lambda g:(g['percent'],-g['total'],g['mode'],g['skill'],g['category']))
        response=jsonify(days=days,attempts=attempts,missing_snapshots=missing,groups=items,total=sum(g['total'] for g in items),correct=sum(g['correct'] for g in items))
        response.headers['Cache-Control']='no-store';return response
