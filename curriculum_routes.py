"""Explicit staff import of authored bilingual curriculum drafts."""
from flask import jsonify, request
from curriculum_pack import PACK, COURSES, import_drafts


def install_curriculum(app, legacy, db, owner):
    @app.post('/api/platform/admin/curriculum-pack')
    @legacy['admin_required']
    def curriculum_pack_import():
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'pack','language'} or d['pack']!=PACK or not isinstance(d['language'],str) or d['language'] not in ('all','ko','lo'):
            return jsonify(error='Invalid curriculum pack'),400
        try:
            with db() as c:
                c.execute('BEGIN IMMEDIATE');counts=import_drafts(c,owner(),d['language'])
        except ValueError as error:return jsonify(error=str(error)),409
        return jsonify(ok=True,added=sum(counts.values()),counts=counts,courses=[COURSES[language][0] for language in counts],published_new=0)
