"""Administrator-managed course scope; shared dictionaries/media stay shared."""
from flask import jsonify,request,render_template,redirect


def install_teachers(app,legacy,db):
    @app.get('/teacher-assignments')
    def teacher_assignments_page():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role')!='admin':return redirect('/admin')
        return render_template('teacher-assignments.html')

    @app.get('/api/platform/admin/teacher-assignments')
    @legacy['admin_required']
    def teacher_assignments_list():
        teachers=[]
        with db() as c:
            courses=[dict(r) for r in c.execute('SELECT id,title FROM courses ORDER BY title,id')]
            for username,u in legacy['users'].items():
                if u.get('role')!='teacher':continue
                scope=c.execute('SELECT restricted FROM teacher_course_scopes WHERE username=?',(username,)).fetchone()
                ids=[r['course'] for r in c.execute('SELECT course FROM teacher_course_assignments WHERE username=? ORDER BY course',(username,))]
                teachers.append({'username':username,'name':u.get('name',username),'status':u.get('status'),'restricted':bool(scope and scope['restricted']),'courses':ids})
        response=jsonify(teachers=sorted(teachers,key=lambda t:t['username']),courses=courses)
        response.headers['Cache-Control']='no-store';return response

    @app.post('/api/platform/admin/teacher-assignments/<username>')
    @legacy['admin_required']
    def teacher_assignments_save(username):
        u=legacy['users'].get(username)
        if not u or u.get('role')!='teacher':return jsonify(error='Teacher not found'),404
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict) or type(d.get('restricted'))!=bool or not isinstance(d.get('courses'),list) or len(d['courses'])>500 or any(not isinstance(cid,str) for cid in d['courses']):return jsonify(error='Invalid scope'),400
        ids=set(d['courses'])
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            existing={r['id'] for r in c.execute('SELECT id FROM courses')}
            if not ids<=existing:return jsonify(error='Unknown course'),400
            c.execute('INSERT OR REPLACE INTO teacher_course_scopes VALUES (?,?)',(username,int(d['restricted'])))
            c.execute('DELETE FROM teacher_course_assignments WHERE username=?',(username,))
            c.executemany('INSERT INTO teacher_course_assignments VALUES (?,?)',[(username,cid) for cid in sorted(ids)])
        return jsonify(ok=True)
