"""Bulk rename existing draft modules without touching published snapshots."""
import json
import time
from flask import jsonify, request
from course_permissions import may_manage


def install_modules(app, legacy, db, owner):
    @app.post('/api/platform/admin/courses/<cid>/rename-module')
    @legacy['content_required']
    def rename_course_module(cid):
        d = request.get_json(silent=True)
        if (not isinstance(d, dict) or set(d) != {'source', 'target', 'lessons'}
                or not isinstance(d['source'], str) or not isinstance(d['target'], str)
                or not d['target'].strip() or len(d['target']) > 200
                or not isinstance(d['lessons'], list) or not 1 <= len(d['lessons']) <= 1000):
            return jsonify(error='Invalid module rename'), 400
        items = d['lessons']
        if any(not isinstance(i, dict) or set(i) != {'id', 'revision'}
               or not isinstance(i['id'], str) or type(i['revision']) is not int
               or i['revision'] < 1 for i in items):
            return jsonify(error='Invalid lesson revisions'), 400
        ids = [i['id'] for i in items]
        if len(ids) != len(set(ids)):
            return jsonify(error='Duplicate lesson'), 400
        target = d['target'].strip()
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            if not c.execute('SELECT 1 FROM courses WHERE id=?', (cid,)).fetchone():
                return jsonify(error='Not found'), 404
            if not may_manage(c, legacy['current_user'](), cid):
                return jsonify(error='Course not assigned'), 403
            rows = c.execute('SELECT id,draft,revision FROM course_lessons WHERE course=?', (cid,)).fetchall()
            selected = {r['id']: (r, json.loads(r['draft'])) for r in rows
                        if json.loads(r['draft']).get('module', '') == d['source']}
            if set(ids) != set(selected) or any(i['revision'] != selected[i['id']][0]['revision'] for i in items):
                return jsonify(error='Module lessons changed; reload before renaming'), 409
            # Avoid silently joining two distinct units; moves remain per-lesson edits.
            if target != d['source'] and any(json.loads(r['draft']).get('module', '') == target for r in rows):
                return jsonify(error='A module already uses this name'), 409
            if target == d['source']:
                return jsonify(ok=True, changed=0)
            now = time.time()
            for lid, (row, content) in selected.items():
                content['module'] = target
                payload = json.dumps(content, ensure_ascii=False)
                revision = row['revision'] + 1
                c.execute('UPDATE course_lessons SET draft=?,revision=?,updated=? WHERE id=?', (payload, revision, now, lid))
                c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)', (lid, revision, payload, owner(), now))
        return jsonify(ok=True, changed=len(selected))
