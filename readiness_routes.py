"""Staff-only content review queue; presence checks are not language-quality checks."""
import json
from urllib.parse import urlencode
from flask import jsonify, request, render_template, redirect


def collect_issues(c):
    reviews = {r['qid']: r for r in c.execute('SELECT qid,verified FROM reviews')}
    items = []
    for row in c.execute('SELECT id,content FROM eps_bank WHERE active=1 ORDER BY id'):
        q = json.loads(row['content'])
        issues = []
        verified = bool(reviews[row['id']]['verified']) if row['id'] in reviews else bool(q.get('verified'))
        if not verified:
            issues.append('unverified')
        if q.get('stem_ko', '').strip() and not q.get('stem_lo', '').strip():
            issues.append('stem_lo')
        if q.get('passage_ko', '').strip() and not q.get('passage_lo', '').strip():
            issues.append('passage_lo')
        ko, lo = q.get('choices_ko', []), q.get('choices_lo', [])
        if any(str(v).strip() and (i >= len(lo) or not str(lo[i]).strip()) for i, v in enumerate(ko)):
            issues.append('choices_lo')
        if issues:
            items.append({'kind': 'eps', 'id': str(row['id']), 'title': q.get('stem_ko') or q.get('passage_ko') or ('EPS #' + str(row['id'])), 'issues': issues, 'url': '/question-editor?' + urlencode({'id': row['id']})})
    for row in c.execute('SELECT id,ko,lo,audio_ko,audio_lo FROM vocabulary WHERE published=1 ORDER BY ko,id'):
        issues = ['audio_' + lang for lang in ('ko', 'lo') if not (row['audio_' + lang] or '').strip()]
        if issues:
            items.append({'kind': 'vocabulary', 'id': row['id'], 'title': row['ko'] + ' · ' + row['lo'], 'issues': issues, 'url': '/vocabulary-studio?' + urlencode({'id': row['id']})})
    return items


def install_readiness(app, legacy, db):
    @app.get('/content-readiness')
    def readiness_page():
        u = legacy['current_user']()
        if not u or u.get('status') != 'approved' or u.get('role') not in ('admin', 'teacher'):
            return redirect('/admin')
        return render_template('content-readiness.html')

    @app.get('/api/platform/admin/content-readiness')
    @legacy['content_required']
    def readiness_report():
        kind = request.args.get('kind', '')
        try:
            page = int(request.args.get('page', '1'))
            if not 1 <= page <= 100000:
                raise ValueError()
        except ValueError:
            return jsonify(error='Invalid page'), 400
        if kind not in ('', 'eps', 'vocabulary'):
            return jsonify(error='Invalid content type'), 400
        term = request.args.get('q', '').strip()[:200].casefold()
        with db() as c:
            items = collect_issues(c)
        counts = {k: sum(i['kind'] == k for i in items) for k in ('eps', 'vocabulary')}
        filtered = [i for i in items if (not kind or i['kind'] == kind) and (not term or term in (i['id'] + ' ' + i['title']).casefold())]
        total = len(filtered)
        pages = max(1, (total + 29) // 30)
        page = min(page, pages)
        response = jsonify(counts=counts, total=total, page=page, pages=pages, items=filtered[(page-1)*30:page*30])
        response.headers['Cache-Control'] = 'no-store'
        return response
