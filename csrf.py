"""Session-bound CSRF protection for all cookie-authenticated writes."""
import secrets
from flask import request, session, jsonify

def install_csrf(app):
    app.config['SESSION_COOKIE_HTTPONLY']=True
    app.config['SESSION_COOKIE_SAMESITE']='Lax'
    @app.get('/api/csrf')
    def csrf_token():
        if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
        response=jsonify(token=session['csrf']);response.headers['Cache-Control']='no-store';return response
    @app.before_request
    def protect_writes():
        if request.method not in ('POST','PUT','PATCH','DELETE'):return
        expected=session.get('csrf','');given=request.headers.get('X-CSRF-Token','')
        if not expected or not secrets.compare_digest(expected,given):return jsonify(error='Reload the page and try again / ໂຫຼດໜ້າຄືນ / 페이지를 새로고침하세요'),403
        if request.is_json and not isinstance(request.get_json(silent=True),dict):return jsonify(error='Expected a JSON object'),400
