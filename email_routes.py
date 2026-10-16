"""Optional email registration; verification never grants administrator approval."""
import hashlib,json,secrets,time
from flask import jsonify,request,render_template
from email_delivery import configuration,normalize_email


def install_email(app,legacy,db):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS email_accounts (username TEXT PRIMARY KEY,email TEXT UNIQUE,verified INTEGER,created REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS email_verifications (hash TEXT PRIMARY KEY,username TEXT,email TEXT,expires REAL,used INTEGER,auth_version INTEGER)')
        c.execute('CREATE TABLE IF NOT EXISTS email_limits (key TEXT PRIMARY KEY,count INTEGER,started REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS email_outbox (id INTEGER PRIMARY KEY AUTOINCREMENT,recipient TEXT,body TEXT,created REAL,expires REAL,attempts INTEGER,available REAL,lease TEXT,lease_until REAL,sent REAL,state TEXT)')

    def rate(c,scope,maximum):
        key=hashlib.sha256((scope+'|'+(request.remote_addr or '')).encode()).hexdigest();stamp=time.time()
        row=c.execute('SELECT * FROM email_limits WHERE key=?',(key,)).fetchone()
        if row and stamp-row['started']<3600 and row['count']>=maximum:return False
        count=row['count']+1 if row and stamp-row['started']<3600 else 1
        c.execute('INSERT OR REPLACE INTO email_limits VALUES (?,?,?)',(key,count,row['started'] if count>1 else stamp));return True

    def queue(c,username,email,cfg):
        token=secrets.token_urlsafe(32);stamp=time.time();expires=stamp+1800
        c.execute("UPDATE email_outbox SET state='expired',body='',recipient='' WHERE recipient=? AND state='pending'",(email,))
        c.execute('UPDATE email_verifications SET used=1 WHERE username=?',(username,))
        c.execute('INSERT INTO email_verifications VALUES (?,?,?,?,0,?)',(hashlib.sha256(token.encode()).hexdigest(),username,email,expires,legacy['users'][username].get('auth_version',0)))
        body='THANA KOREAN\nVerify your email / 이메일 확인\n'+cfg['base']+'/email-account#verify='+token+'\n\nThis link expires in 30 minutes. Administrator approval is still required.\n30분 이내에 확인하세요. 관리자 승인은 별도로 필요합니다.\nIf you did not request this, ignore this email.'
        c.execute("INSERT INTO email_outbox(recipient,body,created,expires,attempts,available,lease,lease_until,state) VALUES (?,?,?,?,0,?,'',0,'pending')",(email,body,stamp,expires,stamp))

    def email_login_allowed(username):
        with db() as c:row=c.execute('SELECT verified FROM email_accounts WHERE username=?',(username,)).fetchone()
        if row:return bool(row['verified'])
        return not legacy['users'].get(username,{}).get('email_verification_required',False)
    app.config['THANA_EMAIL_LOGIN_ALLOWED']=email_login_allowed

    @app.get('/email-account')
    def email_account_page():return render_template('email-account.html')
    @app.get('/api/platform/email/status')
    def email_status():return jsonify(enabled=configuration() is not None)

    @app.post('/api/platform/email/register')
    def email_register():
        cfg=configuration()
        if not cfg:return jsonify(error='Email registration is not configured'),503
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict):return jsonify(error='Invalid registration'),400
        address=normalize_email(d.get('email'));username=d.get('username','')
        if not address or not isinstance(username,str):return jsonify(error='Invalid email or username'),400
        username=username.strip().lower()
        if not isinstance(d.get('name'),str) or not 1<=len(d['name'].strip())<=100:return jsonify(error='Invalid name'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not rate(c,'register',10):return jsonify(error='Try again later'),429
            if c.execute('SELECT 1 FROM email_accounts WHERE email=?',(address,)).fetchone():return jsonify(error='Registration unavailable; check your details or contact staff'),400
            response=app.make_response(legacy['register']())
            if response.status_code!=200:return response
            # Keep the account fail-closed if the separate platform transaction fails.
            legacy['users'][username]['email_verification_required']=True
            legacy['_save'](legacy['USERS_FILE'],legacy['users'])
            c.execute('INSERT INTO email_accounts VALUES (?,?,0,?)',(username,address,time.time()))
            queue(c,username,address,cfg)
        return jsonify(ok=True,verification_required=True,approval_required=True),201

    @app.post('/api/platform/email/resend')
    def email_resend():
        cfg=configuration()
        if not cfg:return jsonify(error='Email registration is not configured'),503
        d=request.get_json(silent=True) or {}
        if not isinstance(d,dict):return jsonify(error='Invalid request'),400
        username=d.get('username','');password=d.get('password','')
        if not isinstance(username,str) or not isinstance(password,str) or len(password)>128:return jsonify(error='Invalid request'),400
        username=username.strip().lower();u=legacy['users'].get(username)
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not rate(c,'resend',5):return jsonify(error='Try again later'),429
            row=c.execute('SELECT * FROM email_accounts WHERE username=?',(username,)).fetchone()
            if row and not row['verified'] and u and u.get('status')!='rejected' and legacy['check_pw'](password,u.get('pw')):queue(c,username,row['email'],cfg)
        return jsonify(ok=True)

    @app.post('/api/platform/email/verify')
    def email_verify():
        d=request.get_json(silent=True) or {};token=d.get('token') if isinstance(d,dict) else None;password=d.get('password') if isinstance(d,dict) else None
        if not isinstance(token,str) or not 20<=len(token)<=100 or not isinstance(password,str) or not 8<=len(password)<=128:return jsonify(error='Invalid or expired link'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not rate(c,'verify',20):return jsonify(error='Try again later'),429
            row=c.execute('SELECT * FROM email_verifications WHERE hash=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            u=legacy['users'].get(row['username']) if row else None
            account=c.execute('SELECT * FROM email_accounts WHERE username=?',(row['username'],)).fetchone() if row else None
            if not row or row['used'] or row['expires']<=time.time() or not u or u.get('auth_version',0)!=row['auth_version'] or not legacy['check_pw'](password,u.get('pw')) or not account or account['email']!=row['email']:return jsonify(error='Invalid or expired link'),400
            c.execute("UPDATE email_outbox SET state='expired',body='',recipient='' WHERE recipient=? AND state='pending'",(row['email'],))
            c.execute('UPDATE email_accounts SET verified=1 WHERE username=?',(row['username'],))
            c.execute('UPDATE email_verifications SET used=1 WHERE username=?',(row['username'],))
            c.execute("INSERT INTO audit_log(actor,action,target,created) VALUES (?,'email_verified',?,?)",(row['username'],row['username'],time.time()))
        return jsonify(ok=True,approval_required=u.get('status')!='approved')

    @app.after_request
    def remove_deleted_email_account(response):
        if request.endpoint=='admin_delete_student' and 200<=response.status_code<300:
            username=(request.view_args or {}).get('uname')
            with db() as c:
                row=c.execute('SELECT email FROM email_accounts WHERE username=?',(username,)).fetchone()
                if row:c.execute("UPDATE email_outbox SET state='expired',body='',recipient='' WHERE recipient=? AND state='pending'",(row['email'],))
                c.execute('DELETE FROM email_verifications WHERE username=?',(username,))
                c.execute('DELETE FROM email_accounts WHERE username=?',(username,))
        return response
