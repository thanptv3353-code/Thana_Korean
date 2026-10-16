"""Structured bilingual courses with draft/published snapshots and durable progress."""
import json, secrets, time
import quiz_engine
from course_permissions import course_scope, may_manage
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from flask import jsonify, request, render_template, redirect

def install_courses(app, legacy, db, owner):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS courses (id TEXT PRIMARY KEY, title TEXT, language TEXT, instruction TEXT, description TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS course_lessons (id TEXT PRIMARY KEY, course TEXT, draft TEXT, published TEXT, revision INTEGER, updated REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS course_progress (owner TEXT, lesson TEXT, score INTEGER, completed REAL, PRIMARY KEY(owner,lesson))')
        c.execute('CREATE TABLE IF NOT EXISTS course_rules (course TEXT PRIMARY KEY, sequential INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS lesson_revisions (lesson TEXT, revision INTEGER, content TEXT, actor TEXT, created REAL, PRIMARY KEY(lesson,revision))')
        c.execute('CREATE TABLE IF NOT EXISTS teacher_course_scopes (username TEXT PRIMARY KEY,restricted INTEGER NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS teacher_course_assignments (username TEXT,course TEXT,PRIMARY KEY(username,course))')
    def valid_content(d):
        if not isinstance(d,dict) or not isinstance(d.get('title'),str) or not d['title'].strip() or len(d['title'])>200: return False
        if not isinstance(d.get('module',''),str) or (type(d.get('order',1)) is not int or d.get('order',1)<1): return False
        blocks=d.get('blocks',[]); quiz=d.get('quiz',[])
        if not isinstance(blocks,list) or len(blocks)>100 or not isinstance(quiz,list) or len(quiz)>50:return False
        for b in blocks:
            if not isinstance(b,dict) or b.get('type') not in ('text','audio','image','video') or not isinstance(b.get('value'),str):return False
            if len(b['value'])>20000:return False
            if b['type'] in ('audio','image'):
                u=urlparse(b['value'])
                if not ((u.scheme=='https' and u.netloc and not u.username) or (not u.scheme and (b['value'].startswith('/static/') or b['value'].startswith('/media/audio/') or b['value'].startswith('/media/library/')) and not b['value'].startswith('//'))):return False
            if b['type']=='video':
                if b['value'].startswith('/media/library/'):
                    with db() as c:asset=c.execute("SELECT kind FROM media_assets WHERE filename=?",(b['value'][len('/media/library/'):],)).fetchone()
                    if not asset or asset['kind']!='video':return False
                elif not legacy['extract_youtube_id'](b['value']):return False
        if not all(quiz_engine.valid(q) for q in quiz):return False
        return True
    def public(d):
        d=json.loads(json.dumps(d));d['quiz']=[quiz_engine.public(q) for q in d.get('quiz',[])]
        for b in d.get('blocks',[]):
            if b['type']=='video' and not b['value'].startswith('/media/library/'):b['embed_url']='https://www.youtube.com/embed/'+legacy['extract_youtube_id'](b['value'])
            if b['type']=='audio' and b['value'].startswith('/media/library/'):
                with db() as c:generated=c.execute('SELECT g.voice FROM generated_audio g JOIN media_assets m ON m.id=g.asset WHERE m.filename=?',(b['value'].split('/')[-1],)).fetchone()
                if generated:b['ai_generated']=True
        return d
    def accessible(c,lid):
        row=c.execute('SELECT course FROM course_lessons WHERE id=?',(lid,)).fetchone()
        if not row:return True
        u=legacy['current_user']()
        if may_manage(c,u,row['course']):return True
        restricted=c.execute('SELECT 1 FROM premium_courses WHERE course=?',(row['course'],)).fetchone()
        entitlement=c.execute('SELECT expires FROM entitlements WHERE owner=?',(owner(),)).fetchone()
        if restricted and not (entitlement and entitlement['expires']>time.time()):return False
        rule=c.execute('SELECT sequential FROM course_rules WHERE course=?',(row['course'],)).fetchone()
        if rule and rule['sequential']:
            records=c.execute('SELECT id,published FROM course_lessons WHERE course=? AND published IS NOT NULL',(row['course'],)).fetchall()
            ordered=sorted(records,key=lambda r:(json.loads(r['published']).get('order',1),r['id']))
            index=next((i for i,r in enumerate(ordered) if r['id']==lid),None)
            if index and not c.execute('SELECT 1 FROM course_progress WHERE owner=? AND lesson=?',(owner(),ordered[index-1]['id'])).fetchone():return False
        return True
    @app.get('/my-learning')
    def my_learning_page():return render_template('my-learning.html')
    @app.get('/courses')
    def courses_page():return render_template('courses.html')
    @app.get('/editor')
    def editor_page():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role') not in ('admin','teacher'):return redirect('/admin')
        return render_template('editor.html')
    @app.get('/api/platform/courses')
    def courses_list():
        with db() as c:
            rows=c.execute('SELECT * FROM courses ORDER BY title').fetchall()
            result=[]
            for r in rows:
                lessons=[]
                for l in c.execute('SELECT id,published FROM course_lessons WHERE course=? AND published IS NOT NULL',(r['id'],)):
                    d=json.loads(l['published']);lessons.append({'id':l['id'],'title':d['title'],'module':d.get('module',''),'order':d.get('order',1),'unlocked':accessible(c,l['id'])})
                if lessons:result.append({**dict(r),'premium':bool(c.execute('SELECT 1 FROM premium_courses WHERE course=?',(r['id'],)).fetchone()),'lessons':sorted(lessons,key=lambda l:(l['order'],l['id']))})
        old=legacy['sorted_lessons']()
        if old:
            result.insert(0,{'id':'legacy-ko','title':'ພາສາເກົາຫຼີ / 한국어','language':'ko','instruction':'lo','description':'ບົດຮຽນເກົ່າທີ່ຮັກສາໄວ້ / 기존 강좌','legacy':True,'lessons':[{'id':l['id'],'title':l['title_lo'],'module':l.get('title_ko',''),'order':l['order']} for l in old]})
        return jsonify(courses=result)
    @app.get('/api/platform/lessons/<lid>')
    def course_lesson(lid):
        with db() as c:
            if not accessible(c,lid):return jsonify(error='ບົດຍັງລັອກ. ກວດບົດກ່ອນ ແລະ ສິດການຮຽນ / 이전 수업과 이용권을 확인하세요'),403
            row=c.execute('SELECT published FROM course_lessons WHERE id=?',(lid,)).fetchone()
        if not row or not row['published']:return jsonify(error='Lesson not published'),404
        return jsonify(lesson=public(json.loads(row['published'])))
    @app.post('/api/platform/lessons/<lid>/complete')
    def complete_course_lesson(lid):
        if not owner():return jsonify(error='ກະລຸນາເຂົ້າລະບົບ / 로그인해 주세요'),401
        answers=(request.get_json(silent=True) or {}).get('answers',{})
        if not isinstance(answers,dict):return jsonify(error='Invalid answers'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            row=c.execute('SELECT published FROM course_lessons WHERE id=?',(lid,)).fetchone()
            if not row or not row['published']:return jsonify(error='Not found'),404
            if not accessible(c,lid):return jsonify(error='Lesson locked; check prerequisites and membership'),403
            content=json.loads(row['published']);qs=content.get('quiz',[])
            if set(answers)-{str(i) for i in range(len(qs))}:return jsonify(error='Unexpected answer'),400
            try:
                detail=[quiz_engine.grade(q,answers.get(str(i))) for i,q in enumerate(qs)]
            except ValueError:
                return jsonify(error='Invalid answer'),400
            score=round(100*sum(q['correct'] for q in detail)/len(qs)) if qs else 100
            passed=score>=70
            if passed:c.execute('INSERT INTO course_progress VALUES (?,?,?,?) ON CONFLICT(owner,lesson) DO UPDATE SET score=MAX(course_progress.score,excluded.score)',(owner(),lid,score,time.time()))
        return jsonify(score=score,passed=passed,detail=detail)
    @app.get('/api/platform/learning-progress')
    def learning_progress():
        if not owner():return jsonify(error='Login required'),401
        with db() as c:rows=c.execute('SELECT * FROM course_progress WHERE owner=?',(owner(),)).fetchall()
        old=legacy['progress'].get(owner(),{})
        old_completed=[lid for lid,p in old.items() if p.get('exam_passed') and legacy['find_lesson'](lid)]
        with db() as c:
            activity=[r[0] for r in c.execute('SELECT reviewed FROM word_reviews WHERE owner=?',(owner(),))]+[r[0] for r in c.execute('SELECT finished FROM mock_runs WHERE owner=? AND finished IS NOT NULL',(owner(),))]+[r[0] for r in c.execute('SELECT finished FROM attempts WHERE owner=? AND finished IS NOT NULL',(owner(),))]
        timestamps=activity+[r['completed'] for r in rows]+[old[lid]['completed_at'] for lid in old_completed if old[lid].get('completed_at')]
        tz=timezone(timedelta(hours=7));today=datetime.now(tz).date();dates={datetime.fromtimestamp(t,tz).date() for t in timestamps};day=today if today in dates else today-timedelta(days=1);streak=0
        while day in dates:streak+=1;day-=timedelta(days=1)
        completed=[r['lesson'] for r in rows]+['legacy:'+lid for lid in old_completed]
        return jsonify(completed=completed,xp=len(completed)*20,streak=streak,level=1+len(completed)//5)
    @app.post('/api/platform/admin/courses/<cid>/sequence')
    @legacy['content_required']
    def course_sequence(cid):
        enabled=(request.get_json(silent=True) or {}).get('sequential')
        if type(enabled)!=bool:return jsonify(error='Invalid setting'),400
        with db() as c:
            if not c.execute('SELECT id FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),cid):return jsonify(error='Course not assigned'),403
            c.execute('INSERT OR REPLACE INTO course_rules VALUES (?,?)',(cid,int(enabled)))
        return jsonify(ok=True)
    @app.get('/api/platform/admin/courses')
    @legacy['content_required']
    def admin_course_list():
        with db() as c:
            courses=[dict(r) for r in c.execute('SELECT courses.*, EXISTS(SELECT 1 FROM premium_courses WHERE course=courses.id) AS premium, COALESCE((SELECT sequential FROM course_rules WHERE course=courses.id),0) AS sequential FROM courses ORDER BY title')]
            lessons=[{'id':r['id'],'course':r['course'],'draft':json.loads(r['draft']),'revision':r['revision'],'published':bool(r['published'])} for r in c.execute('SELECT * FROM course_lessons')]
            scope=course_scope(c,legacy['current_user']())
            if scope is not None:
                courses=[r for r in courses if r['id'] in scope]
                lessons=[r for r in lessons if r['course'] in scope]
        return jsonify(courses=courses,lessons=lessons,can_create=scope is None)
    @app.post('/api/platform/admin/courses')
    @legacy['content_required']
    def create_course():
        d=request.get_json(silent=True) or {};title=d.get('title');language=d.get('language');description=d.get('description','')
        if not isinstance(title,str) or not title.strip() or len(title)>200 or language not in ('lo','ko') or not isinstance(description,str):return jsonify(error='Invalid course'),400
        cid=secrets.token_urlsafe(12)
        with db() as c:
            if course_scope(c,legacy['current_user']()) is not None:return jsonify(error='Ask an administrator to create and assign the course'),403
            c.execute('INSERT INTO courses VALUES (?,?,?,?,?)',(cid,title.strip(),language,'ko' if language=='lo' else 'lo',description))
        return jsonify(id=cid),201
    @app.post('/api/platform/admin/courses/<cid>/lessons')
    @legacy['content_required']
    def create_course_lesson(cid):
        d=request.get_json(silent=True) or {}
        if not valid_content(d):return jsonify(error='Invalid lesson'),400
        lid=secrets.token_urlsafe(12);payload=json.dumps(d,ensure_ascii=False)
        with db() as c:
            if not c.execute('SELECT id FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),cid):return jsonify(error='Course not assigned'),403
            c.execute('INSERT INTO course_lessons VALUES (?,?,?,?,?,?)',(lid,cid,payload,None,1,time.time()))
            c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(lid,1,payload,owner(),time.time()))
        return jsonify(id=lid,revision=1),201
    @app.get('/api/platform/admin/lessons/<lid>/revisions')
    @legacy['content_required']
    def lesson_history(lid):
        with db() as c:
            if not c.execute('SELECT 1 FROM course_lessons WHERE id=?',(lid,)).fetchone():return jsonify(error='Not found'),404
            course=c.execute('SELECT course FROM course_lessons WHERE id=?',(lid,)).fetchone()['course']
            if not may_manage(c,legacy['current_user'](),course):return jsonify(error='Course not assigned'),403
            rows=c.execute('SELECT revision,actor,created,content FROM lesson_revisions WHERE lesson=? ORDER BY revision DESC LIMIT 50',(lid,)).fetchall()
        return jsonify(revisions=[{'revision':r['revision'],'actor':r['actor'],'created':r['created'],'title':json.loads(r['content'])['title']} for r in rows])
    @app.get('/api/platform/admin/lessons/<lid>/revisions/<int:revision>')
    @legacy['content_required']
    def lesson_revision(lid,revision):
        with db() as c:
            lesson=c.execute('SELECT course FROM course_lessons WHERE id=?',(lid,)).fetchone()
            if not lesson:return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),lesson['course']):return jsonify(error='Course not assigned'),403
            row=c.execute('SELECT content FROM lesson_revisions WHERE lesson=? AND revision=?',(lid,revision)).fetchone()
        if not row:return jsonify(error='Not found'),404
        return jsonify(content=json.loads(row['content']),revision=revision)
    @app.post('/api/platform/admin/lessons/<lid>')
    @legacy['content_required']
    def save_course_lesson(lid):
        d=request.get_json(silent=True) or {};content=d.get('content');action=d.get('action','save');revision=d.get('revision')
        if action not in ('save','publish','unpublish') or not valid_content(content):return jsonify(error='Invalid lesson'),400
        if action=='publish' and not content.get('blocks'):return jsonify(error='Add lesson content before publishing'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM course_lessons WHERE id=?',(lid,)).fetchone()
            if not row:return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),row['course']):return jsonify(error='Course not assigned'),403
            if type(revision)!=int or revision!=row['revision']:return jsonify(error='ມີການແກ້ໄຂໃໝ່. ໂຫຼດຄືນກ່ອນ / 다른 변경이 있습니다. 새로고침하세요.'),409
            if action=='publish':
                for block in content.get('blocks',[]):
                    if block['value'].startswith('/media/library/'):
                        filename=block['value'].split('/')[-1]
                        asset=c.execute('SELECT published FROM media_assets WHERE filename=?',(filename,)).fetchone()
                        if not asset or not asset['published']:return jsonify(error='ເຜີຍແຜ່ສື່ກ່ອນ / 미디어를 먼저 공개하세요'),400
            payload=json.dumps(content,ensure_ascii=False);published=payload if action=='publish' else (None if action=='unpublish' else row['published']);rev=revision+1
            c.execute('UPDATE course_lessons SET draft=?,published=?,revision=?,updated=? WHERE id=?',(payload,published,rev,time.time(),lid))
            c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(lid,rev,payload,owner(),time.time()))
        return jsonify(revision=rev,published=bool(published))
