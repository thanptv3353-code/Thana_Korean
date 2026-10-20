"""Owner-only legacy history; no answers, raw records or inferred identities."""
from flask import jsonify,request
from firebase_result_history import initialize


def install_original_history(app,legacy,db,owner):
    with db() as c:initialize(c)
    @app.get('/api/platform/original-history')
    def original_history():
        username=owner()
        if not username:return jsonify(error='Login required'),401
        user=legacy['current_user']()
        try:
            limit=int(request.args.get('limit','20'));offset=int(request.args.get('offset','0'))
            if not 1<=limit<=100 or not 0<=offset<=1000000:raise ValueError()
        except ValueError:return jsonify(error='Invalid pagination'),400
        uid=user.get('firebase_uid')
        with db() as c:
            bound=c.execute('SELECT 1 FROM firebase_account_bindings WHERE uid=? AND username=? AND enabled=1',(uid,username)).fetchone() if isinstance(uid,str) and uid else None
            if not bound:results=[];total=0
            else:
                total=c.execute('SELECT COUNT(*) FROM firebase_original_results WHERE uid=?',(uid,)).fetchone()[0]
                rows=c.execute('SELECT document,group_id,score,total,pct,passed,submitted FROM firebase_original_results WHERE uid=? ORDER BY submitted DESC,document LIMIT ? OFFSET ?',(uid,limit,offset)).fetchall()
                results=[dict(id=r['document'],group=r['group_id'],score=r['score'],total=r['total'],pct=r['pct'],passed=bool(r['passed']),finished=r['submitted'],kind='original-seasonal') for r in rows]
        response=jsonify(results=results,total=total,limit=limit,offset=offset)
        response.headers['Cache-Control']='no-store'
        return response
