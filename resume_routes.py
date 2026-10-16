"""Owner-only resume suggestions across structured and preserved lessons."""
import json,math,time
from urllib.parse import quote
from flask import jsonify,request

def install_resume(app,legacy,db,owner,accessible):
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS lesson_visits (owner TEXT,kind TEXT,lesson TEXT,visited REAL,PRIMARY KEY(owner,kind,lesson))')

    def legacy_allowed(lesson):
        return legacy['current_user']().get('role') in ('admin','superadmin') or legacy['is_unlocked'](owner(),lesson)

    @app.after_request
    def clear_deleted_resume(response):
        if request.endpoint=='admin_delete_student' and 200<=response.status_code<300:
            username=(request.view_args or {}).get('uname')
            if username and username not in legacy['users']:
                with db() as c:
                    c.execute('DELETE FROM lesson_visits WHERE owner=?',(username,))
                    c.execute('DELETE FROM course_progress WHERE owner=?',(username,))
        return response

    @app.post('/api/platform/lesson-visits')
    def record_lesson_visit():
        if not owner():return jsonify(error='Login required'),401
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'kind','lesson'} or d.get('kind') not in ('structured','legacy') or not isinstance(d.get('lesson'),str) or not 1<=len(d['lesson'])<=100:return jsonify(error='Invalid visit'),400
        with db() as c:
            if d['kind']=='structured':
                row=c.execute('SELECT published FROM course_lessons WHERE id=?',(d['lesson'],)).fetchone()
                if not row or not row['published']:return jsonify(error='Not found'),404
                if not accessible(c,d['lesson']):return jsonify(error='Lesson locked'),403
            else:
                lesson=legacy['find_lesson'](d['lesson'])
                if not lesson:return jsonify(error='Not found'),404
                if not legacy_allowed(lesson):return jsonify(error='Lesson locked'),403
            c.execute('INSERT INTO lesson_visits VALUES (?,?,?,?) ON CONFLICT(owner,kind,lesson) DO UPDATE SET visited=excluded.visited',(owner(),d['kind'],d['lesson'],time.time()))
        return jsonify(ok=True)

    @app.get('/api/platform/resume')
    def learning_resume():
        if not owner():return jsonify(error='Login required'),401
        language=request.args.get('language','ko')
        if language not in ('ko','lo'):return jsonify(error='Invalid language'),400
        old_progress=legacy['progress'].get(owner(),{})
        with db() as c:
            completed={r['lesson']:r['completed'] for r in c.execute('SELECT lesson,completed FROM course_progress WHERE owner=?',(owner(),))}
            events=[(r['visited'],r['kind'],r['lesson']) for r in c.execute('SELECT kind,lesson,visited FROM lesson_visits WHERE owner=? ORDER BY visited DESC LIMIT 100',(owner(),))]
            events.extend((stamp,'structured',lid) for lid,stamp in completed.items())
            for lid,p in old_progress.items():
                stamp=p.get('completed_at')
                if p.get('exam_passed') and type(stamp) in (int,float) and math.isfinite(stamp):events.append((stamp,'legacy',lid))
            result=None
            for stamp,kind,lid in sorted(events,reverse=True):
                if kind=='legacy':
                    if language!='ko':continue
                    lessons=legacy['sorted_lessons']();index=next((i for i,l in enumerate(lessons) if l['id']==lid),None)
                    if index is None or not legacy_allowed(lessons[index]):continue
                    target=lessons[index];action='resume'
                    if old_progress.get(lid,{}).get('exam_passed'):
                        if index+1<len(lessons) and legacy_allowed(lessons[index+1]):target=lessons[index+1];action='next'
                        else:action='review'
                    result={'kind':kind,'lesson':target['id'],'title':target['title_lo'],'title_ko':target.get('title_ko',''),'language':'ko','action':action,'url':'/learn?lesson='+quote(target['id'],safe='')}
                else:
                    row=c.execute('SELECT l.course,c.language,c.title FROM course_lessons l JOIN courses c ON c.id=l.course WHERE l.id=? AND l.published IS NOT NULL',(lid,)).fetchone()
                    if not row or row['language']!=language or not accessible(c,lid):continue
                    lessons=sorted([{'id':r['id'],'content':json.loads(r['published'])} for r in c.execute('SELECT id,published FROM course_lessons WHERE course=? AND published IS NOT NULL',(row['course'],))],key=lambda l:(l['content'].get('order',1),l['id']))
                    index=next(i for i,l in enumerate(lessons) if l['id']==lid);target=lessons[index];action='resume'
                    if lid in completed:
                        if index+1<len(lessons) and accessible(c,lessons[index+1]['id']):target=lessons[index+1];action='next'
                        else:action='review'
                    result={'kind':kind,'lesson':target['id'],'title':target['content']['title'],'course':row['title'],'language':language,'action':action,'url':'/courses?language='+language+'&lesson='+quote(target['id'],safe='')}
                if result:break
        response=jsonify(resume=result);response.headers['Cache-Control']='no-store';return response
