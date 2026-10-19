"""Disabled-by-default Firebase session bridge for explicitly bound legacy UIDs."""
import datetime
import hashlib
import os
import re
import threading
import time
from flask import g,jsonify,request,session

PROJECT='korean-lao-exam'
COOKIE='__Host-thana-firebase'
_lock=threading.Lock()


def sdk():
    if os.environ.get('FIREBASE_AUTH_EMULATOR_HOST'):raise ValueError('Emulator is not allowed for legacy authentication')
    import firebase_admin
    from firebase_admin import auth
    with _lock:
        try:app=firebase_admin.get_app('thana-legacy')
        except ValueError:app=firebase_admin.initialize_app(options={'projectId':PROJECT},name='thana-legacy')
    return auth,app


def verify_token(token):
    auth,app=sdk()
    return auth.verify_id_token(token,app=app,check_revoked=True)


def issue_cookie(token):
    auth,app=sdk()
    return auth.create_session_cookie(token,expires_in=datetime.timedelta(minutes=5),app=app)


def verify_cookie(cookie):
    auth,app=sdk()
    return auth.verify_session_cookie(cookie,app=app,check_revoked=True)


def enabled():return os.environ.get('THANA_FIREBASE_AUTH_ENABLED')=='1'


def install_firebase_auth(app,legacy,db):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS firebase_account_bindings (uid TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, enabled INTEGER NOT NULL DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS firebase_login_attempts (key TEXT PRIMARY KEY, count INTEGER NOT NULL, started REAL NOT NULL)')
    def bound_user(uid):
        if not isinstance(uid,str) or not uid:return None
        with db() as c:r=c.execute('SELECT username FROM firebase_account_bindings WHERE uid=? AND enabled=1',(uid,)).fetchone()
        user=legacy['users'].get(r['username']) if r else None
        return user if user and user.get('status')=='approved' else None
    def clear_auth():
        session.clear();g.clear_firebase_cookie=True
    @app.before_request
    def check_firebase_session():
        if session.get('auth_provider')!='firebase':return
        try:
            if not enabled():raise ValueError('Disabled')
            claims=verify_cookie(request.cookies.get(COOKIE,''));uid=claims.get('uid');user=bound_user(uid)
            if uid!=session.get('firebase_uid') or not user or user['username']!=session.get('username') or user.get('auth_version',0)!=session.get('auth_version',0):raise ValueError('Binding changed')
            # Always use current local permissions, never a token's role/email claims.
            session['role']=user['role']
        except Exception:
            clear_auth()
            if request.path.startswith(('/api/','/media/')):return jsonify(error='Login required'),401
    @app.after_request
    def cleanup_firebase_cookie(response):
        if g.get('clear_firebase_cookie') or request.path=='/api/logout':response.delete_cookie(COOKIE,secure=True,httponly=True,samesite='Strict',path='/')
        return response
    @app.get('/api/platform/auth/firebase/config')
    def firebase_config():
        key=os.environ.get('THANA_FIREBASE_WEB_API_KEY','')
        ready=enabled() and bool(re.fullmatch(r'AIza[A-Za-z0-9_-]{35}',key))
        return jsonify(enabled=ready,project=PROJECT,**({'api_key':key} if ready else {}))
    @app.post('/api/platform/auth/firebase')
    def firebase_login():
        if not enabled():return jsonify(error='Legacy sign-in is not enabled'),503
        if not request.is_secure:return jsonify(error='HTTPS required'),400
        key=hashlib.sha256((request.remote_addr or 'unknown').encode()).hexdigest();now=time.time()
        with db() as c:
            c.execute('BEGIN IMMEDIATE');row=c.execute('SELECT count,started FROM firebase_login_attempts WHERE key=?',(key,)).fetchone()
            if row and now-row['started']<600 and row['count']>=10:return jsonify(error='Too many attempts'),429
            if not row or now-row['started']>=600:c.execute('INSERT OR REPLACE INTO firebase_login_attempts VALUES (?,?,?)',(key,1,now))
            else:c.execute('UPDATE firebase_login_attempts SET count=count+1 WHERE key=?',(key,))
        data=request.get_json(silent=True)
        if not isinstance(data,dict) or set(data)!={'id_token'} or not isinstance(data['id_token'],str) or not 1<=len(data['id_token'])<=8192:return jsonify(error='Invalid sign-in request'),400
        try:
            claims=verify_token(data['id_token']);uid=claims.get('uid');user=bound_user(uid)
            auth_time=claims.get('auth_time')
            if type(auth_time) not in (int,float) or not 0<=now-auth_time<=300 or not user:raise ValueError('Recent authentication and explicit binding required')
            cookie=issue_cookie(data['id_token'])
            if not isinstance(cookie,str) or not cookie:raise ValueError('Session not issued')
        except Exception:return jsonify(error='Unable to sign in'),401
        session.clear();session.update(username=user['username'],role=user['role'],auth_version=user.get('auth_version',0),auth_provider='firebase',firebase_uid=uid)
        response=jsonify(ok=True,user={k:user[k] for k in ('username','name','role')})
        response.set_cookie(COOKIE,cookie,max_age=300,secure=True,httponly=True,samesite='Strict',path='/')
        response.headers['Cache-Control']='no-store'
        return response
