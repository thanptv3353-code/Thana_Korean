"""Account preferences, password maintenance and admin-assisted recovery."""
import hashlib,secrets,time
from flask import jsonify,request,session,render_template

def install_accounts(app,legacy,db,owner):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS recovery_tokens (hash TEXT PRIMARY KEY, username TEXT, expires REAL, used INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS audit_log (id INTEGER PRIMARY KEY AUTOINCREMENT, actor TEXT, action TEXT, target TEXT, created REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS login_attempts (key TEXT PRIMARY KEY, count INTEGER, started REAL)')
    def audit(action,target):
        with db() as c:c.execute('INSERT INTO audit_log (actor,action,target,created) VALUES (?,?,?,?)',(owner(),action,target,time.time()))
    @app.before_request
    def limit_login():
        if request.path!='/api/login' or request.method!='POST':return
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict):return
        username=d.get('username','')
        if not isinstance(username,str):return
        key=hashlib.sha256((request.remote_addr+'|'+username.strip().lower()).encode()).hexdigest()
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT * FROM login_attempts WHERE key=?',(key,)).fetchone();now=time.time()
            if row and now-row['started']<600 and row['count']>=10:return jsonify(error='ລອງຫຼາຍເກີນໄປ. ລໍຖ້າ 10 ນາທີ / 시도가 많습니다. 10분 후 다시 시도하세요'),429
            if not row or now-row['started']>=600:c.execute('INSERT OR REPLACE INTO login_attempts VALUES (?,?,?)',(key,1,now))
            else:c.execute('UPDATE login_attempts SET count=count+1 WHERE key=?',(key,))
    @app.get('/account')
    def account_page():return render_template('account.html')
    @app.get('/api/platform/account')
    @legacy['login_required']
    def account_info():
        u=legacy['current_user']();return jsonify(username=u['username'],name=u['name'],role=u['role'],language=u.get('language','lo'))
    @app.post('/api/platform/account')
    @legacy['login_required']
    def account_save():
        d=request.get_json(silent=True) or {};name=d.get('name');language=d.get('language')
        if not isinstance(name,str) or not 1<=len(name.strip())<=100 or language not in ('lo','ko'):return jsonify(error='Invalid profile'),400
        u=legacy['current_user']();u['name']=name.strip();u['language']=language;legacy['_save'](legacy['USERS_FILE'],legacy['users']);return jsonify(ok=True)
    def replace_password(u,password,c):
        c.execute('UPDATE recovery_tokens SET used=1 WHERE username=?',(u['username'],))
        u['pw']=legacy['hash_pw'](password);u['auth_version']=u.get('auth_version',0)+1;legacy['_save'](legacy['USERS_FILE'],legacy['users'])
    @app.post('/api/platform/account/password')
    @legacy['login_required']
    def change_password():
        d=request.get_json(silent=True) or {};old=d.get('current');password=d.get('password');u=legacy['current_user']()
        if not isinstance(password,str) or not 8<=len(password)<=128 or not legacy['check_pw'](old,u.get('pw')):return jsonify(error='Check current password; new password must have 8–128 characters'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');replace_password(u,password,c)
        audit('password_changed',u['username']);session.clear();return jsonify(ok=True)
    @app.get('/api/platform/admin/accounts')
    @legacy['admin_required']
    def admin_accounts():return jsonify(system_control=legacy['has_system_control'](),users=[{k:u.get(k) for k in ('username','name','role','status')} for u in legacy['users'].values()])
    @app.post('/api/platform/admin/accounts/<username>')
    @legacy['admin_required']
    def admin_account_update(username):
        d=request.get_json(silent=True) or {};role=d.get('role');status=d.get('status');u=legacy['users'].get(username)
        if not u:return jsonify(error='Not found'),404
        if role not in ('student','teacher','admin','superadmin') or status not in ('pending','approved','rejected'):return jsonify(error='Invalid account settings'),400
        actor=legacy['current_user']();system=legacy['has_system_control']()
        if not system and (role!=u['role'] or u['role'] in ('admin','superadmin')):return jsonify(error='Super Admin controls staff permissions'),403
        if role=='superadmin' and actor.get('role')!='superadmin':return jsonify(error='Initial Super Admin requires operator activation'),403
        if username==owner() and (role!=u['role'] or status!='approved'):return jsonify(error='Cannot remove your own administrator access'),400
        if u['role']=='superadmin' and (role!='superadmin' or status!='approved') and not any(x.get('role')=='superadmin' and x.get('status')=='approved' and x.get('username')!=username for x in legacy['users'].values()):return jsonify(error='Keep an approved Super Admin'),400
        u['role']=role;u['status']=status;legacy['_save'](legacy['USERS_FILE'],legacy['users']);audit('account_permissions',username);return jsonify(ok=True)
    @app.post('/api/platform/admin/accounts/<username>/recovery')
    @legacy['admin_required']
    def create_recovery(username):
        if username not in legacy['users']:return jsonify(error='Not found'),404
        if legacy['users'][username].get('role') in ('admin','superadmin') and not legacy['has_system_control']():return jsonify(error='Super Admin required for staff recovery'),403
        token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
        with db() as c:
            c.execute('UPDATE recovery_tokens SET used=1 WHERE username=?',(username,))
            c.execute('INSERT INTO recovery_tokens VALUES (?,?,?,0)',(digest,username,time.time()+1800))
        audit('recovery_issued',username);return jsonify(link='/account#reset='+token,expires_in=1800)
    @app.post('/api/platform/account/recover')
    def recover():
        d=request.get_json(silent=True) or {};token=d.get('token');password=d.get('password')
        if not isinstance(token,str) or not isinstance(password,str) or not 8<=len(password)<=128:return jsonify(error='Invalid recovery'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM recovery_tokens WHERE hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            if not r or r['used'] or r['expires']<=time.time():return jsonify(error='Link invalid or expired'),400
            u=legacy['users'].get(r['username'])
            if not u:return jsonify(error='Link invalid or expired'),400
            replace_password(u,password,c)
        audit('password_recovered',u['username'])
        session.clear();return jsonify(ok=True)
    @app.get('/api/platform/admin/audit')
    @legacy['admin_required']
    def audit_list():
        q=request.args.get('q','').strip()[:200]
        try:page=int(request.args.get('page','1'))
        except ValueError:return jsonify(error='Invalid page'),400
        if not 1<=page<=100000:return jsonify(error='Invalid page'),400
        # instr treats search text literally, including SQL wildcard characters.
        where="WHERE instr(lower(COALESCE(actor,'')||' '||action||' '||target),lower(?))>0"
        with db() as c:
            total=c.execute('SELECT COUNT(*) FROM audit_log '+where,(q,)).fetchone()[0]
            rows=c.execute('SELECT * FROM audit_log '+where+' ORDER BY created DESC,id DESC LIMIT 100 OFFSET ?',(q,(page-1)*100)).fetchall()
        response=jsonify(events=[dict(r) for r in rows],total=total,page=page,page_size=100)
        response.headers['Cache-Control']='no-store'
        return response
