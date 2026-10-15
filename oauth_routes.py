"""Optional Google OIDC sign-in; no email-based account auto-linking."""
import os,secrets,hashlib,time,importlib.util
from flask import jsonify,session,redirect

def install_oauth(app,legacy):
    configured=all(os.environ.get(k) for k in ('GOOGLE_CLIENT_ID','GOOGLE_CLIENT_SECRET','GOOGLE_REDIRECT_URI'))
    enabled=configured and importlib.util.find_spec('authlib') is not None
    google=None
    if enabled:
        from authlib.integrations.flask_client import OAuth
        oauth=OAuth(app);google=oauth.register(name='google',client_id=os.environ['GOOGLE_CLIENT_ID'],client_secret=os.environ['GOOGLE_CLIENT_SECRET'],server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',client_kwargs={'scope':'openid email profile'})
    @app.get('/api/oauth/status')
    def oauth_status():return jsonify(google=enabled)
    @app.get('/auth/google')
    def google_start():
        if not enabled:return jsonify(error='Google sign-in has not been configured'),503
        return google.authorize_redirect(os.environ['GOOGLE_REDIRECT_URI'])
    @app.get('/auth/google/callback')
    def google_callback():
        if not enabled:return jsonify(error='Google sign-in has not been configured'),503
        try:
            token=google.authorize_access_token();info=token.get('userinfo')
            if not token.get('id_token') or not info or not isinstance(info.get('sub'),str):raise ValueError()
        except Exception:return jsonify(error='Google authentication failed; start again'),400
        sub=info['sub'];username='google_'+hashlib.sha256(sub.encode()).hexdigest()[:20]
        u=legacy['users'].get(username)
        if u and u.get('google_sub')!=sub:return jsonify(error='Identity conflict; contact administrator'),409
        if not u:
            u={'username':username,'name':str(info.get('name') or 'Google learner')[:100],'role':'student','status':'pending','google_sub':sub,'pw':legacy['hash_pw'](secrets.token_urlsafe(32)),'created_at':time.time()}
            legacy['users'][username]=u;legacy['_save'](legacy['USERS_FILE'],legacy['users'])
        if u['status']!='approved':return redirect('/learn?google=pending')
        session.clear();session['username']=username;session['role']=u['role'];session['auth_version']=u.get('auth_version',0)
        return redirect('/courses')
