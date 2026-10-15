"""Configurable manual-payment requests; no external transfers are performed."""
import os,secrets,time
from flask import jsonify,request,render_template,send_from_directory

def install_membership(app,legacy,db,owner):
    receipts=os.path.join(legacy['DATA'],'receipts');os.makedirs(receipts,exist_ok=True)
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS membership_plan (id INTEGER PRIMARY KEY, amount INTEGER, currency TEXT, days INTEGER, instructions TEXT, enabled INTEGER)')
        c.execute("INSERT OR IGNORE INTO membership_plan VALUES (1,0,'LAK',30,'',0)")
        c.execute('CREATE TABLE IF NOT EXISTS payment_requests (id TEXT PRIMARY KEY, owner TEXT, amount INTEGER, currency TEXT, days INTEGER, proof TEXT, status TEXT, created REAL, reviewed REAL, reviewer TEXT, note TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS entitlements (owner TEXT PRIMARY KEY, expires REAL)')
        c.execute('CREATE TABLE IF NOT EXISTS premium_courses (course TEXT PRIMARY KEY)')
    def premium(username):
        if not username:return False
        with db() as c:r=c.execute('SELECT expires FROM entitlements WHERE owner=?',(username,)).fetchone()
        return bool(r and r['expires']>time.time())
    legacy['has_premium']=premium
    @app.get('/membership')
    def membership_page():return render_template('membership.html')
    @app.get('/api/platform/membership')
    def membership_info():
        with db() as c:
            plan=dict(c.execute('SELECT * FROM membership_plan WHERE id=1').fetchone())
            r=c.execute('SELECT expires FROM entitlements WHERE owner=?',(owner(),)).fetchone()
            payments=[{k:row[k] for k in ('id','amount','currency','status','created','note')} for row in c.execute('SELECT * FROM payment_requests WHERE owner=? ORDER BY created DESC',(owner(),))] if owner() else []
        return jsonify(plan=plan,premium=premium(owner()),expires=r['expires'] if r else None,payments=payments)
    @app.post('/api/platform/membership/request')
    def payment_request():
        if not owner():return jsonify(error='Login required'),401
        file=request.files.get('file')
        if not file:return jsonify(error='Select a receipt image'),400
        raw=file.read(5*1024*1024+1)
        if not raw or len(raw)>5*1024*1024:return jsonify(error='Receipt limit: 5 MB'),400
        ext='png' if raw[:8]==b'\x89PNG\r\n\x1a\n' else ('jpg' if raw[:3]==b'\xff\xd8\xff' else '')
        if not ext:return jsonify(error='PNG or JPEG image required'),400
        aid=secrets.token_urlsafe(12);filename=secrets.token_hex(16)+'.'+ext
        with db() as c:
            c.execute('BEGIN IMMEDIATE');p=c.execute('SELECT * FROM membership_plan WHERE id=1').fetchone()
            if not p['enabled']:return jsonify(error='Payments are not enabled'),409
            if c.execute("SELECT 1 FROM payment_requests WHERE owner=? AND status='pending'",(owner(),)).fetchone():return jsonify(error='A request is already pending'),409
            with open(os.path.join(receipts,filename),'xb') as f:f.write(raw)
            c.execute('INSERT INTO payment_requests VALUES (?,?,?,?,?,?,?,?,?,?,?)',(aid,owner(),p['amount'],p['currency'],p['days'],filename,'pending',time.time(),None,None,''))
        return jsonify(id=aid),201
    @app.get('/api/platform/admin/payments')
    @legacy['admin_required']
    def payment_list():
        with db() as c:rows=c.execute('SELECT * FROM payment_requests ORDER BY created DESC LIMIT 100').fetchall()
        return jsonify(payments=[{**dict(r),'proof_url':'/api/platform/payments/'+r['id']+'/proof'} for r in rows])
    @app.get('/api/platform/payments/<aid>/proof')
    def receipt_file(aid):
        u=legacy['current_user']()
        if not owner():return jsonify(error='Login required'),401
        with db() as c:r=c.execute('SELECT * FROM payment_requests WHERE id=?',(aid,)).fetchone()
        if not r or (r['owner']!=owner() and u['role']!='admin'):return jsonify(error='Not found'),404
        response=send_from_directory(receipts,r['proof']);response.headers['Cache-Control']='no-store';response.headers['X-Content-Type-Options']='nosniff';return response
    @app.post('/api/platform/admin/payments/<aid>')
    @legacy['admin_required']
    def payment_review(aid):
        d=request.get_json(silent=True) or {};status=d.get('status');note=d.get('note','')
        if status not in ('approved','rejected') or not isinstance(note,str) or len(note)>1000:return jsonify(error='Invalid review'),400
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT * FROM payment_requests WHERE id=?',(aid,)).fetchone()
            if not r:return jsonify(error='Not found'),404
            if r['status']!='pending':return jsonify(error='Already reviewed'),409
            if status=='approved':
                existing=c.execute('SELECT expires FROM entitlements WHERE owner=?',(r['owner'],)).fetchone()
                expires=max(time.time(),existing['expires'] if existing else 0)+r['days']*86400
                c.execute('INSERT OR REPLACE INTO entitlements VALUES (?,?)',(r['owner'],expires))
            c.execute('UPDATE payment_requests SET status=?,reviewed=?,reviewer=?,note=? WHERE id=?',(status,time.time(),owner(),note,aid))
        return jsonify(ok=True)
    @app.post('/api/platform/admin/membership')
    @legacy['admin_required']
    def plan_update():
        d=request.get_json(silent=True) or {};amount=d.get('amount');currency=d.get('currency');days=d.get('days');instructions=d.get('instructions');enabled=d.get('enabled')
        if type(amount)!=int or not 0<=amount<=100_000_000 or currency not in ('LAK','KRW') or type(days)!=int or not 1<=days<=366 or not isinstance(instructions,str) or len(instructions)>3000 or type(enabled)!=bool or (enabled and (not amount or not instructions.strip())):return jsonify(error='Set a valid price, duration and payment instructions'),400
        with db() as c:c.execute('UPDATE membership_plan SET amount=?,currency=?,days=?,instructions=?,enabled=? WHERE id=1',(amount,currency,days,instructions,int(enabled)))
        return jsonify(ok=True)
    @app.post('/api/platform/admin/courses/<cid>/premium')
    @legacy['admin_required']
    def course_premium(cid):
        enabled=(request.get_json(silent=True) or {}).get('premium')
        if type(enabled)!=bool:return jsonify(error='Invalid premium setting'),400
        with db() as c:
            if not c.execute('SELECT id FROM courses WHERE id=?',(cid,)).fetchone():return jsonify(error='Not found'),404
            if enabled:c.execute('INSERT OR IGNORE INTO premium_courses VALUES (?)',(cid,))
            else:c.execute('DELETE FROM premium_courses WHERE course=?',(cid,))
        return jsonify(ok=True)
