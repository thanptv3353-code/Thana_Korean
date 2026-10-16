"""Optional course-scoped teachers; existing shared-staff access is preserved."""
def course_scope(connection, user):
    if not user or user.get('status')!='approved':return set()
    if user.get('role')=='admin':return None
    if user.get('role')!='teacher':return set()
    row=connection.execute('SELECT restricted FROM teacher_course_scopes WHERE username=?',(user['username'],)).fetchone()
    if not row or not row['restricted']:return None
    return {r['course'] for r in connection.execute('SELECT course FROM teacher_course_assignments WHERE username=?',(user['username'],))}


def may_manage(connection,user,course):
    scope=course_scope(connection,user)
    return scope is None or course in scope
