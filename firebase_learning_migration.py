"""Original scoped access and lesson history; caller owns the SQLite transaction."""
import datetime
import json
from firebase_reconciliation import reconcile_transfer
from firebase_eps_practice import initialize as initialize_eps_progress,import_source_progress

COURSE_SCOPES={'firebase-thana-lessons-v1':'general','firebase-thana-seasonal-v1':'seasonal'}


def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_scope_entitlements (uid TEXT,scope TEXT,granted INTEGER NOT NULL,PRIMARY KEY(uid,scope))')
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_progress_imports (document TEXT PRIMARY KEY,uid TEXT,kind TEXT,status TEXT,source TEXT NOT NULL)')


def course_entitled(connection,username,course):
    scope=COURSE_SCOPES.get(course)
    if not scope or not username:return False
    return bool(connection.execute('SELECT 1 FROM firebase_scope_entitlements e JOIN firebase_account_bindings b ON b.uid=e.uid WHERE b.username=? AND b.enabled=1 AND e.scope=? AND e.granted=1',(username,scope)).fetchone())


def apply_learning(connection,payload):
    plan=reconcile_transfer(payload);initialize(connection);initialize_eps_progress(connection)
    source_uids={identity['firebase_uid'] for identity in plan['identities']}
    users={row[0]:row[1] for row in connection.execute('SELECT uid,username FROM firebase_account_bindings')}
    for identity in plan['identities']:
        if identity['firebase_uid'] not in users:continue
        if users[identity['firebase_uid']]!=identity['username']:raise ValueError('UID binding username differs from source')
        if set(identity['issues'])-{'deleted_profile'}:raise ValueError('Ambiguous identity scopes')
        for scope,state in identity['scopes'].items():
            if state not in ('paid','unpaid'):raise ValueError('Ambiguous entitlement')
            existing=connection.execute('SELECT granted FROM firebase_scope_entitlements WHERE uid=? AND scope=?',(identity['firebase_uid'],scope)).fetchone()
            if existing and existing[0]!=(state=='paid'):raise ValueError('Existing scope differs; explicit review required')
    # Validate journal identity/content before any history writes.
    for row in plan['progress']:
        existing=connection.execute('SELECT source FROM firebase_progress_imports WHERE document=?',(row['document_id'],)).fetchone()
        if existing and json.loads(existing[0])!=row['source']:raise ValueError('Source progress changed; explicit review required')
    scopes=passed=skipped=0;statuses={};eps_added=eps_updated=eps_unknown=0
    for identity in plan['identities']:
        if identity['firebase_uid'] not in users:continue
        for scope,state in identity['scopes'].items():
            scopes+=connection.execute('INSERT OR IGNORE INTO firebase_scope_entitlements VALUES (?,?,?)',(identity['firebase_uid'],scope,int(state=='paid'))).rowcount
    for row in plan['progress']:
        eps=None
        if row['kind']=='eps' and row['firebase_uid'] in users:
            eps=import_source_progress(connection,users[row['firebase_uid']],row['source']);eps_added+=eps['added'];eps_updated+=eps['updated'];eps_unknown+=eps['unknown']
        if connection.execute('SELECT 1 FROM firebase_progress_imports WHERE document=?',(row['document_id'],)).fetchone():
            if eps:connection.execute('UPDATE firebase_progress_imports SET status=? WHERE document=?',(eps['status'],row['document_id']))
            skipped+=1;continue
        data=row['source'];uid=row['firebase_uid'];status='preserved-source-only'
        if uid not in users:status='inactive-source-owner' if uid in source_uids else 'unresolved-owner'
        elif eps:status=eps['status']
        elif row['kind']=='lesson':
            lesson=connection.execute('SELECT course FROM course_lessons WHERE id=?',(row['lesson_id'],)).fetchone()
            if row['issues']:status='invalid-lesson-history'
            elif not lesson or lesson[0]!='firebase-thana-lessons-v1':status='unmapped-lesson'
            elif data['passed'] is not True:status='not-completed'
            else:
                try:
                    stamp=datetime.datetime.fromisoformat(data['completedAt'].replace('Z','+00:00'))
                    if stamp.tzinfo is None:raise ValueError('Timestamp requires timezone')
                    completed=stamp.timestamp()
                    if completed<=0:raise ValueError('Invalid date')
                except (KeyError,TypeError,AttributeError,ValueError,OverflowError):status='invalid-completion-time'
                else:
                    owner=users[uid];score=round(100*data['score']/data['total'])
                    existing=connection.execute('SELECT score,completed FROM course_progress WHERE owner=? AND lesson=?',(owner,row['lesson_id'])).fetchone()
                    if existing:status='existing-completion-preserved'
                    else:
                        connection.execute('INSERT INTO course_progress VALUES (?,?,?,?)',(owner,row['lesson_id'],score,completed));passed+=1;status='imported-completion'
        statuses[status]=statuses.get(status,0)+1
        connection.execute('INSERT INTO firebase_progress_imports VALUES (?,?,?,?,?)',(row['document_id'],uid,row['kind'],status,json.dumps(data,ensure_ascii=False)))
    return dict(eps_question_rows_added=eps_added,eps_flags_updated=eps_updated,eps_unknown_question_refs=eps_unknown,scope_rows_added=scopes,lesson_completions_added=passed,already_recorded=skipped,statuses=statuses)
