"""Structured bilingual courses with draft/published snapshots and durable progress."""
import json, secrets, time, re
from lesson_vocabulary import public_word
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
        c.execute('CREATE TABLE IF NOT EXISTS lesson_access (lesson TEXT PRIMARY KEY, mode TEXT NOT NULL, revision INTEGER NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS course_levels (course TEXT PRIMARY KEY, level TEXT NOT NULL, revision INTEGER NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS course_rules (course TEXT PRIMARY KEY, sequential INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS lesson_revisions (lesson TEXT, revision INTEGER, content TEXT, actor TEXT, created REAL, PRIMARY KEY(lesson,revision))')
        c.execute('CREATE TABLE IF NOT EXISTS teacher_course_scopes (username TEXT PRIMARY KEY,restricted INTEGER NOT NULL)')
        c.execute('CREATE TABLE IF NOT EXISTS teacher_course_assignments (username TEXT,course TEXT,PRIMARY KEY(username,course))')
        c.execute('CREATE TABLE IF NOT EXISTS course_metadata_revisions (course TEXT PRIMARY KEY, revision INTEGER NOT NULL)')
    def valid_content(d):
        if not isinstance(d,dict) or not isinstance(d.get('title'),str) or not d['title'].strip() or len(d['title'])>200: return False
        if not isinstance(d.get('module',''),str) or (type(d.get('order',1)) is not int or d.get('order',1)<1): return False
        if not isinstance(d.get('objectives',''),str) or len(d.get('objectives',''))>2000:return False
        blocks=d.get('blocks',[]); quiz=d.get('quiz',[])
        if not isinstance(blocks,list) or len(blocks)>100 or not isinstance(quiz,list) or len(quiz)>50:return False
        for b in blocks:
            if not isinstance(b,dict) or b.get('type') not in ('text','audio','image','video','vocabulary') or not isinstance(b.get('value'),str):return False
            if len(b['value'])>20000:return False
            if b['type']=='vocabulary' and not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',b['value']):return False
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
        with db() as c:
            for q in d['quiz']:
                q.pop('ai_audio',None)
                for key,kind in (('image_url','image'),('audio_url','audio')):
                    if q.get(key):
                        asset=c.execute('SELECT published FROM media_assets WHERE filename=? AND kind=?',(q[key].split('/')[-1],kind)).fetchone()
                        if not asset or not asset['published']:q[key]=''
                        elif key=='audio_url' and c.execute('SELECT 1 FROM generated_audio g JOIN media_assets m ON m.id=g.asset WHERE m.filename=?',(q[key].split('/')[-1],)).fetchone():q['ai_audio']=True
        for b in d.get('blocks',[]):
            if b['type']=='vocabulary':
                with db() as c:b['word']=public_word(c,b['value'])
            if b['type']=='video' and not b['value'].startswith('/media/library/'):b['embed_url']='https://www.youtube.com/embed/'+legacy['extract_youtube_id'](b['value'])
            if b['type']=='audio' and b['value'].startswith('/media/library/'):
                with db() as c:generated=c.execute('SELECT g.voice FROM generated_audio g JOIN media_assets m ON m.id=g.asset WHERE m.filename=?',(b['value'].split('/')[-1],)).fetchone()
                if generated:b['ai_generated']=True
        return d
    def premium_lesson(c,lid,course):
        rule=c.execute('SELECT mode FROM lesson_access WHERE lesson=?',(lid,)).fetchone()
        mode=rule['mode'] if rule else 'inherit'
        if mode!='inherit':return mode=='premium'
        return bool(c.execute('SELECT 1 FROM premium_courses WHERE course=?',(course,)).fetchone())

    def accessible(c,lid):
        row=c.execute('SELECT course FROM course_lessons WHERE id=?',(lid,)).fetchone()
        if not row:return True
        u=legacy['current_user']()
        if may_manage(c,u,row['course']):return True
        restricted=premium_lesson(c,lid,row['course'])
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
        if not u or u.get('status')!='approved' or u.get('role') not in ('admin','superadmin','teacher'):return redirect('/admin')
        return render_template('editor.html')
    @app.get('/api/platform/courses')
    def courses_list():
        with db() as c:
            rows=c.execute('SELECT courses.*, COALESCE(course_levels.level,\'\') AS level, COALESCE(course_levels.revision,0) AS level_revision FROM courses LEFT JOIN course_levels ON course_levels.course=courses.id ORDER BY title').fetchall()
            result=[]
            for r in rows:
                lessons=[]
                for l in c.execute('SELECT id,published FROM course_lessons WHERE course=? AND published IS NOT NULL',(r['id'],)):
                    d=json.loads(l['published']);lessons.append({'id':l['id'],'title':d['title'],'module':d.get('module',''),'order':d.get('order',1),'unlocked':accessible(c,l['id']),'premium':premium_lesson(c,l['id'],r['id'])})
                if lessons:result.append({**dict(r),'premium':bool(c.execute('SELECT 1 FROM premium_courses WHERE course=?',(r['id'],)).fetchone()),'lessons':sorted(lessons,key=lambda l:(l['order'],l['id']))})
        old=legacy['sorted_lessons']()
        if old:
            result.insert(0,{'id':'legacy-ko','title':'ພາສາເກົາຫຼີ / 한국어','language':'ko','instruction':'lo','description':'ບົດຮຽນເກົ່າທີ່ຮັກສາໄວ້ / 기존 강좌','legacy':True,'level':'','lessons':[{'id':l['id'],'title':l['title_lo'],'module':l.get('title_ko',''),'order':l['order']} for l in old]})
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
    @app.post('/api/platform/admin/courses/<cid>/order')
    @legacy['content_required']
    def course_order_save(cid):
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'lessons'} or not isinstance(d['lessons'],list) or len(d['lessons'])>1000:
            return jsonify(error='Invalid lesson order'),400
        items=d['lessons']
        if any(not isinstance(i,dict) or set(i)!={'id','revision'} or not isinstance(i['id'],str) or type(i['revision']) is not int or i['revision']<1 for i in items):
            return jsonify(error='Invalid lesson order'),400
        ids=[i['id'] for i in items]
        if len(ids)!=len(set(ids)):return jsonify(error='Duplicate lesson'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),cid):return jsonify(error='Course not assigned'),403
            rows={r['id']:r for r in c.execute('SELECT id,draft,revision FROM course_lessons WHERE course=?',(cid,))}
            if set(ids)!=set(rows) or any(i['revision']!=rows[i['id']]['revision'] for i in items):
                return jsonify(error='Lesson list changed; reload before reordering'),409
            changed=0
            for position,item in enumerate(items,1):
                row=rows[item['id']];content=json.loads(row['draft'])
                if content.get('order',1)==position:continue
                content['order']=position;revision=row['revision']+1;payload=json.dumps(content,ensure_ascii=False);now=time.time()
                c.execute('UPDATE course_lessons SET draft=?,revision=?,updated=? WHERE id=?',(payload,revision,now,item['id']))
                c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(item['id'],revision,payload,owner(),now))
                changed+=1
        return jsonify(ok=True,changed=changed)

    @app.post('/api/platform/admin/courses/<cid>/level')
    @legacy['content_required']
    def course_level_save(cid):
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'level','revision'} or not isinstance(d.get('level'),str) or d['level'] not in ('','beginner','intermediate','advanced','eps-topik') or type(d.get('revision')) is not int or d['revision']<0:
            return jsonify(error='Invalid course level'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),cid):return jsonify(error='Course not assigned'),403
            row=c.execute('SELECT revision FROM course_levels WHERE course=?',(cid,)).fetchone()
            revision=row['revision'] if row else 0
            if revision!=d['revision']:return jsonify(error='Course level changed; reload before saving'),409
            c.execute('INSERT INTO course_levels VALUES (?,?,?) ON CONFLICT(course) DO UPDATE SET level=excluded.level,revision=excluded.revision',(cid,d['level'],revision+1))
        return jsonify(ok=True,level=d['level'],revision=revision+1)

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
            courses=[dict(r) for r in c.execute('SELECT courses.*, COALESCE((SELECT level FROM course_levels WHERE course=courses.id),\'\') AS level, COALESCE((SELECT revision FROM course_levels WHERE course=courses.id),0) AS level_revision, COALESCE((SELECT revision FROM course_metadata_revisions WHERE course=courses.id),0) AS metadata_revision, EXISTS(SELECT 1 FROM premium_courses WHERE course=courses.id) AS premium, COALESCE((SELECT sequential FROM course_rules WHERE course=courses.id),0) AS sequential FROM courses ORDER BY title')]
            lessons=[{'id':r['id'],'course':r['course'],'draft':json.loads(r['draft']),'revision':r['revision'],'published':bool(r['published']),'access_mode':r['access_mode'],'access_revision':r['access_revision']} for r in c.execute("SELECT l.*,COALESCE(a.mode,'inherit') AS access_mode,COALESCE(a.revision,0) AS access_revision FROM course_lessons l LEFT JOIN lesson_access a ON a.lesson=l.id")]
            scope=course_scope(c,legacy['current_user']())
            if scope is not None:
                courses=[r for r in courses if r['id'] in scope]
                lessons=[r for r in lessons if r['course'] in scope]
        return jsonify(courses=courses,lessons=lessons,can_create=scope is None,can_set_access=legacy['current_user']().get('role') in ('admin','superadmin'))
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
    @app.post('/api/platform/admin/courses/<cid>/metadata')
    @legacy['content_required']
    def course_metadata_save(cid):
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'title','description','revision'} or not isinstance(d.get('title'),str) or not d['title'].strip() or len(d['title'])>200 or not isinstance(d.get('description'),str) or len(d['description'])>10000 or type(d.get('revision')) is not int or d['revision']<0:
            return jsonify(error='Invalid course details'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if not may_manage(c,legacy['current_user'](),cid):return jsonify(error='Course not assigned'),403
            row=c.execute('SELECT revision FROM course_metadata_revisions WHERE course=?',(cid,)).fetchone()
            revision=row['revision'] if row else 0
            if revision!=d['revision']:return jsonify(error='Course details changed; reload before saving'),409
            c.execute('UPDATE courses SET title=?,description=? WHERE id=?',(d['title'].strip(),d['description'],cid))
            c.execute('INSERT INTO course_metadata_revisions VALUES (?,?) ON CONFLICT(course) DO UPDATE SET revision=excluded.revision',(cid,revision+1))
        return jsonify(ok=True,title=d['title'].strip(),description=d['description'],revision=revision+1)

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
    @app.post('/api/platform/admin/lessons/<lid>/access')
    @legacy['admin_required']
    def lesson_access_save(lid):
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'mode','revision'} or not isinstance(d.get('mode'),str) or d['mode'] not in ('inherit','free','premium') or type(d.get('revision')) is not int or d['revision']<0:return jsonify(error='Invalid lesson access'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM course_lessons WHERE id=?',(lid,)).fetchone():return jsonify(error='Not found'),404
            row=c.execute('SELECT revision FROM lesson_access WHERE lesson=?',(lid,)).fetchone();revision=row['revision'] if row else 0
            if d['revision']!=revision:return jsonify(error='Access setting changed; reload before saving'),409
            c.execute('INSERT INTO lesson_access VALUES (?,?,?) ON CONFLICT(lesson) DO UPDATE SET mode=excluded.mode,revision=excluded.revision',(lid,d['mode'],revision+1))
        return jsonify(ok=True,mode=d['mode'],revision=revision+1)

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
                for q in content.get('quiz',[]):
                    for key,kind in (('image_url','image'),('audio_url','audio')):
                        if q.get(key):
                            asset=c.execute('SELECT published FROM media_assets WHERE filename=? AND kind=?',(q[key].split('/')[-1],kind)).fetchone()
                            if not asset or not asset['published']:return jsonify(error='Publish valid question media first'),400
                for block in content.get('blocks',[]):
                    if block['type']=='vocabulary' and not public_word(c,block['value']):return jsonify(error='Publish the referenced vocabulary first'),400
                    if block['value'].startswith('/media/library/'):
                        filename=block['value'].split('/')[-1]
                        asset=c.execute('SELECT published FROM media_assets WHERE filename=?',(filename,)).fetchone()
                        if not asset or not asset['published']:return jsonify(error='ເຜີຍແຜ່ສື່ກ່ອນ / 미디어를 먼저 공개하세요'),400
            payload=json.dumps(content,ensure_ascii=False);published=payload if action=='publish' else (None if action=='unpublish' else row['published']);rev=revision+1
            c.execute('UPDATE course_lessons SET draft=?,published=?,revision=?,updated=? WHERE id=?',(payload,published,rev,time.time(),lid))
            c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(lid,rev,payload,owner(),time.time()))
        return jsonify(revision=rev,published=bool(published))

    from resume_routes import install_resume
    install_resume(app,legacy,db,owner,accessible)
