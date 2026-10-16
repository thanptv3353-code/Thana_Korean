"""Role-aware management overview and private reporting."""
from course_permissions import course_scope
from datetime import datetime,timedelta,timezone
from flask import jsonify,render_template,redirect

def install_management(app,legacy,db,owner):
    @app.get('/management')
    def management_page():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role') not in ('admin','teacher'):return redirect('/admin')
        return render_template('management.html')
    @app.get('/api/platform/management')
    @legacy['content_required']
    def management_info():
        u=legacy['current_user']()
        with db() as c:
            counts={name:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for name,table in [('courses','courses'),('lessons','course_lessons'),('words','vocabulary'),('mock_exams','mock_runs')]}
            counts['draft_lessons']=c.execute('SELECT COUNT(*) FROM course_lessons WHERE published IS NULL').fetchone()[0]
            scope=course_scope(c,u)
            if scope is not None:
                rows=c.execute('SELECT id,course,published FROM course_lessons').fetchall()
                counts['courses']=len(scope)
                counts['lessons']=sum(r['course'] in scope for r in rows)
                counts['draft_lessons']=sum(r['course'] in scope and r['published'] is None for r in rows)
            counts['pending_words']=c.execute('SELECT COUNT(*) FROM vocabulary WHERE published=0').fetchone()[0]
            if u['role']=='admin':counts['pending_payments']=c.execute("SELECT COUNT(*) FROM payment_requests WHERE status='pending'").fetchone()[0]
        counts['legacy_lessons']=len(legacy['lessons'])
        if u['role']=='admin':
            counts['students']=sum(x.get('role')=='student' for x in legacy['users'].values());counts['pending_accounts']=sum(x.get('status')=='pending' for x in legacy['users'].values())
        trend=[]
        if u['role']=='admin':
            zone=timezone(timedelta(hours=7));today=datetime.now(zone).date()
            with db() as c:
                completions=[r[0] for r in c.execute('SELECT completed FROM course_progress')]
                exams=[r[0] for r in c.execute('SELECT finished FROM mock_runs WHERE finished IS NOT NULL')]
            completions += [p['completed_at'] for learner in legacy['progress'].values() for p in learner.values() if p.get('completed_at')]
            for offset in range(6,-1,-1):
                date=today-timedelta(days=offset)
                trend.append({'date':date.isoformat(),'completed':sum(datetime.fromtimestamp(t,zone).date()==date for t in completions),'exams':sum(datetime.fromtimestamp(t,zone).date()==date for t in exams)})
        return jsonify(user={'name':u['name'],'role':u['role']},counts=counts,trend=trend)
