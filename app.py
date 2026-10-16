#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Thana ພາສາເກົາຫຼີ - ເວັບຮຽນພາສາເກົາຫຼີອອນໄລນ໌
- ນັກຮຽນຕ້ອງລົງທະບຽນ ແລະ ລໍຖ້າ admin ອະນຸມັດກ່ອນຈຶ່ງເຂົ້າໃຊ້ໄດ້
- ບົດຮຽນຮຽງລຳດັບ: ບົດຕໍ່ໄປຈະປົດລ໋ອກອັດຕະໂນມັດເມື່ອສອບເສັງຍ່ອຍຜ່ານ (>=70%)
- admin ເພີ່ມ/ລ໋ອກ/ປົດລ໋ອກວິດີໂອ (ລິ້ງ YouTube ບໍ່ລົງລາຍການ) ແລະ ຈັດການຄໍາຖາມວຽກບ້ານ/quiz/ສອບເສັງ
"""
import io, json, os, hashlib, re, secrets, threading, time, uuid, zipfile
from functools import wraps
from flask import (Flask, jsonify, request, session, send_file,
                   render_template, redirect, url_for, abort)

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
DATA = os.environ.get('THANA_DATA_DIR', os.path.join(BASE, 'data'))
USERS_FILE = os.path.join(DATA, 'users.json')
LESSONS_FILE = os.path.join(DATA, 'lessons.json')
PROGRESS_FILE = os.path.join(DATA, 'progress.json')
SECRET_FILE = os.path.join(DATA, 'secret_key')
PASS_THRESHOLD = 70  # % ຄະແນນຕ່ຳສຸດເພື່ອຜ່ານສອບເສັງຍ່ອຍ ແລະ ປົດລ໋ອກບົດຕໍ່ໄປ

os.makedirs(DATA, exist_ok=True)

YOUTUBE_ID_RE = re.compile(
    r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{11})')

def extract_youtube_id(url_or_id):
    url_or_id = (url_or_id or '').strip()
    m = YOUTUBE_ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', url_or_id):
        return url_or_id
    return None

from legacy_storage import LegacyStorage
_storage = LegacyStorage(DATA)
_lock = _storage.gate
_load = _storage.load
_save = _storage.save

# ---------- password hashing ----------
def hash_pw(pw, salt=None):
    salt = salt or secrets.token_hex(16)
    iterations = 600_000
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), iterations).hex()
    return f'pbkdf2_sha256${iterations}${salt}${h}'

def check_pw(pw, stored):
    if not isinstance(pw, str) or not isinstance(stored, str):
        return False
    try:
        parts = stored.split('$')
        if len(parts) == 2:
            salt, expected = parts
            iterations = 100_000
        elif len(parts) == 4 and parts[0] == 'pbkdf2_sha256':
            _, count, salt, expected = parts
            iterations = int(count)
            if not 100_000 <= iterations <= 1_000_000:
                return False
        else:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt.encode(), iterations).hex()
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False

# ---------- bootstrap ----------
if not os.path.exists(SECRET_FILE):
    with os.fdopen(os.open(SECRET_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as f:
        f.write(secrets.token_hex(32))
with open(SECRET_FILE) as f:
    FLASK_SECRET = f.read().strip()

users = _load(USERS_FILE, None)
if users is None:
    bootstrap_password = os.environ.get('THANA_BOOTSTRAP_PASSWORD') or secrets.token_urlsafe(24)
    if len(bootstrap_password) < 12:
        raise RuntimeError('THANA_BOOTSTRAP_PASSWORD must have at least 12 characters')
    if not os.environ.get('THANA_BOOTSTRAP_PASSWORD'):
        credential_path = os.path.join(DATA, 'bootstrap_credentials.txt')
        with os.fdopen(os.open(credential_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'w') as f:
            f.write('username: admin\npassword: ' + bootstrap_password + '\n')
    users = {
        'admin': {
            'username': 'admin', 'name': 'Admin', 'role': 'admin',
            'status': 'approved', 'pw': hash_pw(bootstrap_password),
        }
    }
    _save(USERS_FILE, users)

lessons = _load(LESSONS_FILE, None)
if lessons is None:
    lessons = _load(os.path.join(BASE, 'data', 'lessons.json'), [])
progress = _load(PROGRESS_FILE, {})

app = Flask(__name__)
app.secret_key = FLASK_SECRET
if os.environ.get('THANA_ENV') == 'production':
    if any(u.get('role') == 'admin' and not str(u.get('pw', '')).startswith('pbkdf2_sha256$') for u in users.values()):
        raise RuntimeError('Upgrade legacy administrator passwords before production')
    app.config['SESSION_COOKIE_SECURE'] = True
from staging_access import install_staging_access
install_staging_access(app)
_storage.install(app, globals())

# ============================================================
# helpers
# ============================================================
def new_id(prefix=''):
    return prefix + uuid.uuid4().hex[:10]

def sorted_lessons():
    return sorted(lessons, key=lambda l: l['order'])

def find_lesson(lid):
    for l in lessons:
        if l['id'] == lid:
            return l
    return None

def student_progress(username, lid, create=True):
    p = progress.setdefault(username, {})
    if lid not in p:
        if not create:
            return None
        p[lid] = {
            'homework_done': False, 'homework_answers': {},
            'quiz_best': 0, 'quiz_attempts': 0,
            'exam_best': 0, 'exam_attempts': 0, 'exam_passed': False,
            'completed_at': None,
        }
    return p[lid]

def is_unlocked(username, lesson):
    """First lesson always unlocked; others unlock once previous lesson's exam is passed."""
    ordered = sorted_lessons()
    idx = next((i for i, l in enumerate(ordered) if l['id'] == lesson['id']), None)
    if idx is None:
        return False
    if idx == 0:
        return True
    prev = ordered[idx - 1]
    prog = student_progress(username, prev['id'], create=False)
    return bool(prog and prog.get('exam_passed'))

def public_video(v, unlocked, role):
    d = {'id': v['id'], 'title': v['title'], 'locked': v['locked']}
    playable = role == 'admin' or (unlocked and not v['locked'])
    d['playable'] = playable
    if playable:
        d['embed_url'] = f"https://www.youtube.com/embed/{v['youtube_id']}"
    return d

def public_questions(qs):
    """Strip answers before sending to students."""
    out = []
    for q in qs:
        d = {'id': q['id'], 'question': q['question']}
        if 'options' in q:
            d['options'] = q['options']
        out.append(d)
    return out

def public_lesson_summary(lesson, username, role):
    unlocked = role == 'admin' or is_unlocked(username, lesson)
    prog = student_progress(username, lesson['id'], create=False) if role != 'admin' else None
    status = 'locked'
    if unlocked:
        status = 'in_progress'
        if prog and prog.get('exam_passed'):
            status = 'completed'
    return {
        'id': lesson['id'], 'order': lesson['order'],
        'title_lo': lesson['title_lo'], 'title_ko': lesson.get('title_ko', ''),
        'description': lesson.get('description', ''),
        'unlocked': unlocked, 'status': status,
        'video_count': len(lesson['videos']),
        'homework_count': len(lesson['homework']),
        'quiz_count': len(lesson['quiz']),
        'exam_count': len(lesson['exam']),
        'progress': prog,
    }

def public_lesson_detail(lesson, username, role):
    unlocked = role == 'admin' or is_unlocked(username, lesson)
    prog = student_progress(username, lesson['id']) if role != 'admin' else None
    return {
        'id': lesson['id'], 'order': lesson['order'],
        'title_lo': lesson['title_lo'], 'title_ko': lesson.get('title_ko', ''),
        'description': lesson.get('description', ''),
        'unlocked': unlocked,
        'videos': [public_video(v, unlocked, role) for v in lesson['videos']],
        'homework': public_questions(lesson['homework']),
        'quiz': public_questions(lesson['quiz']),
        'exam': public_questions(lesson['exam']),
        'progress': prog,
    }

# ============================================================
# auth decorators
# ============================================================
def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        u = current_user()
        if not u or u.get('status') != 'approved':
            session.clear()
            return jsonify(error='ກະລຸນາເຂົ້າສູ່ລະບົບ'), 401
        session['role'] = u['role']
        return f(*a, **kw)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        u = current_user()
        if not u or u.get('status') != 'approved' or u.get('role') != 'admin':
            return jsonify(error='ສະເພາະ admin ເທົ່ານັ້ນ'), 403
        return f(*a, **kw)
    return wrap

def content_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        u = current_user()
        if not u or u.get('status') != 'approved' or u.get('role') not in ('admin', 'teacher'):
            return jsonify(error='Content staff only'), 403
        return f(*a, **kw)
    return wrap

def current_user():
    u = users.get(session.get('username'))
    if u and session.get('auth_version', 0) == u.get('auth_version', 0):
        return u
    return None

# ============================================================
# pages
# ============================================================
@app.get('/health')
def health():
    return jsonify(status='ok')

@app.after_request
def response_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "object-src 'none'; base-uri 'self'; frame-ancestors 'self'"
    if request.path.startswith(('/api/', '/media/')):
        response.headers['Cache-Control'] = 'no-store'
    return response

@app.route('/')
def index():
    return render_template('hub.html')

@app.get('/service-worker.js')
def service_worker():
    from flask import send_from_directory
    response = send_from_directory(os.path.join(BASE, 'static'), 'service-worker.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.route('/learn')
def learn_page():
    return render_template('index.html')

@app.route('/admin')
def admin_page():
    user = current_user()
    if user and user.get('status') == 'approved' and user.get('role') in ('admin', 'teacher'):
        return redirect('/management')
    return render_template('admin.html')

@app.get('/legacy-admin')
def legacy_admin_page():
    user = current_user()
    if not user or user.get('status') != 'approved':
        return redirect('/admin')
    if user.get('role') != 'admin':
        abort(403)
    return render_template('admin.html')

# ============================================================
# auth api
# ============================================================
@app.post('/api/register')
def register():
    d = request.get_json(force=True)
    if not all(isinstance(d.get(k), str) for k in ('name', 'username', 'password')):
        return jsonify(error='Invalid registration fields'), 400
    name = d['name'].strip()
    uname = d['username'].strip().lower()
    pw = d['password']
    if not name or not uname or not isinstance(pw, str) or not 8 <= len(pw) <= 128:
        return jsonify(error='ກະລຸນາປ້ອນຂໍ້ມູນໃຫ້ຄົບ (ລະຫັດຜ່ານ 8–128 ຕົວ)'), 400
    if not re.fullmatch(r'[a-z0-9_]{3,50}', uname):
        return jsonify(error='ຊື່ຜູ້ໃຊ້ໃຫ້ໃຊ້ a-z, 0-9, _ ເທົ່ານັ້ນ'), 400
    with _lock:
        if uname in users:
            return jsonify(error='ຊື່ຜູ້ໃຊ້ນີ້ມີຄົນໃຊ້ແລ້ວ'), 400
        users[uname] = {
            'username': uname, 'name': name, 'role': 'student',
            'status': 'pending', 'pw': hash_pw(pw),
            'created_at': time.time(),
        }
        _save(USERS_FILE, users)
    return jsonify(ok=True, message='ລົງທະບຽນສຳເລັດ, ກະລຸນາລໍຖ້າ admin ອະນຸມັດ')

@app.post('/api/login')
def login():
    d = request.get_json(force=True)
    if not isinstance(d.get('username'), str) or not isinstance(d.get('password'), str) or len(d['password']) > 128:
        return jsonify(error='Invalid login fields'), 400
    uname = d['username'].strip().lower()
    pw = d['password']
    u = users.get(uname)
    if not u or not check_pw(pw, u['pw']):
        return jsonify(error='ຊື່ຜູ້ໃຊ້ ຫຼື ລະຫັດຜ່ານບໍ່ຖືກຕ້ອງ'), 401
    email_check=app.config.get('THANA_EMAIL_LOGIN_ALLOWED')
    if email_check and not email_check(uname):return jsonify(error='ກະລຸນາຢືນຢັນອີເມວ / 이메일을 먼저 확인해 주세요'),403
    if u['status'] != 'approved':
        return jsonify(error='ບັນຊີຂອງທ່ານຍັງບໍ່ໄດ້ຮັບການອະນຸມັດ'), 403
    session['username'] = uname
    session['auth_version'] = u.get('auth_version', 0)
    session['role'] = u['role']
    return jsonify(ok=True, user={'username': uname, 'name': u['name'], 'role': u['role']})

@app.post('/api/logout')
def logout():
    session.clear()
    return jsonify(ok=True)

@app.get('/api/me')
def me():
    u = current_user()
    if not u:
        return jsonify(user=None)
    return jsonify(user={'username': u['username'], 'name': u['name'], 'role': u['role']})

# ============================================================
# student api
# ============================================================
@app.get('/api/lessons')
@login_required
def api_lessons():
    role = session['role']
    uname = session['username']
    return jsonify(lessons=[public_lesson_summary(l, uname, role) for l in sorted_lessons()])

@app.get('/api/lessons/<lid>')
@login_required
def api_lesson_detail(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    role = session['role']
    uname = session['username']
    if role != 'admin' and not is_unlocked(uname, lesson):
        return jsonify(error='ບົດຮຽນນີ້ຍັງລ໋ອກຢູ່'), 403
    return jsonify(lesson=public_lesson_detail(lesson, uname, role))

@app.post('/api/lessons/<lid>/homework')
@login_required
def submit_homework(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    uname = session['username']
    if not is_unlocked(uname, lesson):
        return jsonify(error='ບົດຮຽນນີ້ຍັງລ໋ອກຢູ່'), 403
    answers = request.get_json(force=True).get('answers', {})
    with _lock:
        prog = student_progress(uname, lid)
        prog['homework_answers'] = answers
        prog['homework_done'] = True
        _save(PROGRESS_FILE, progress)
    return jsonify(ok=True, message='ສົ່ງວຽກບ້ານສຳເລັດ')

def _grade(qs, answers):
    total = len(qs)
    correct = 0
    detail = []
    for q in qs:
        given = answers.get(q['id'])
        ok = type(given) is int and given == int(q['answer'])
        if ok:
            correct += 1
        detail.append({'id': q['id'], 'correct': ok, 'answer': q['answer'], 'given': given})
    score = round(correct / total * 100) if total else 0
    return score, detail

@app.post('/api/lessons/<lid>/quiz')
@login_required
def submit_quiz(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    uname = session['username']
    if not is_unlocked(uname, lesson):
        return jsonify(error='ບົດຮຽນນີ້ຍັງລ໋ອກຢູ່'), 403
    answers = request.get_json(force=True).get('answers', {})
    score, detail = _grade(lesson['quiz'], answers)
    with _lock:
        prog = student_progress(uname, lid)
        prog['quiz_attempts'] += 1
        prog['quiz_best'] = max(prog['quiz_best'], score)
        _save(PROGRESS_FILE, progress)
    return jsonify(ok=True, score=score, detail=detail)

@app.post('/api/lessons/<lid>/exam')
@login_required
def submit_exam(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    uname = session['username']
    if not is_unlocked(uname, lesson):
        return jsonify(error='ບົດຮຽນນີ້ຍັງລ໋ອກຢູ່'), 403
    answers = request.get_json(force=True).get('answers', {})
    score, detail = _grade(lesson['exam'], answers)
    passed = score >= PASS_THRESHOLD
    next_unlocked = False
    with _lock:
        prog = student_progress(uname, lid)
        prog['exam_attempts'] += 1
        prog['exam_best'] = max(prog['exam_best'], score)
        if passed and not prog['exam_passed']:
            prog['exam_passed'] = True
            prog['completed_at'] = time.time()
            next_unlocked = True
        _save(PROGRESS_FILE, progress)
    return jsonify(ok=True, score=score, passed=passed, threshold=PASS_THRESHOLD,
                   detail=detail, next_unlocked=next_unlocked)

# ============================================================
# admin api - students
# ============================================================
@app.get('/api/admin/students')
@admin_required
def admin_students():
    out = [{'username': u['username'], 'name': u['name'], 'status': u['status'],
            'created_at': u.get('created_at')}
           for u in users.values() if u['role'] == 'student']
    out.sort(key=lambda u: u.get('created_at') or 0, reverse=True)
    return jsonify(students=out)

@app.post('/api/admin/students/<uname>/approve')
@admin_required
def admin_approve(uname):
    with _lock:
        u = users.get(uname)
        if not u:
            return jsonify(error='ບໍ່ພົບຜູ້ໃຊ້'), 404
        if u.get('role') != 'student':
            return jsonify(error='Use account management for staff accounts'), 400
        u['status'] = 'approved'
        _save(USERS_FILE, users)
    return jsonify(ok=True)

@app.post('/api/admin/students/<uname>/reject')
@admin_required
def admin_reject(uname):
    with _lock:
        u = users.get(uname)
        if not u:
            return jsonify(error='ບໍ່ພົບຜູ້ໃຊ້'), 404
        if u.get('role') != 'student':
            return jsonify(error='Use account management for staff accounts'), 400
        u['status'] = 'rejected'
        _save(USERS_FILE, users)
    return jsonify(ok=True)

@app.delete('/api/admin/students/<uname>')
@admin_required
def admin_delete_student(uname):
    with _lock:
        if uname in users and users[uname]['role'] == 'student':
            del users[uname]
            progress.pop(uname, None)
            _save(USERS_FILE, users)
            _save(PROGRESS_FILE, progress)
    return jsonify(ok=True)

# ============================================================
# admin api - lessons
# ============================================================
@app.get('/api/admin/lessons')
@admin_required
def admin_lessons():
    return jsonify(lessons=sorted_lessons())

@app.post('/api/admin/lessons')
@admin_required
def admin_create_lesson():
    d = request.get_json(force=True)
    title_lo = (d.get('title_lo') or '').strip()
    if not title_lo:
        return jsonify(error='ກະລຸນາປ້ອນຊື່ບົດຮຽນ'), 400
    with _lock:
        order = (max([l['order'] for l in lessons], default=0)) + 1
        lesson = {
            'id': new_id('l_'), 'order': order,
            'title_lo': title_lo, 'title_ko': (d.get('title_ko') or '').strip(),
            'description': (d.get('description') or '').strip(),
            'videos': [], 'homework': [], 'quiz': [], 'exam': [],
            'created_at': time.time(),
        }
        lessons.append(lesson)
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True, lesson=lesson)

@app.put('/api/admin/lessons/<lid>')
@admin_required
def admin_edit_lesson(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    d = request.get_json(force=True)
    with _lock:
        for k in ('title_lo', 'title_ko', 'description'):
            if k in d:
                lesson[k] = d[k]
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True, lesson=lesson)

@app.delete('/api/admin/lessons/<lid>')
@admin_required
def admin_delete_lesson(lid):
    global lessons
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    with _lock:
        lessons = [l for l in lessons if l['id'] != lid]
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True)

@app.post('/api/admin/lessons/reorder')
@admin_required
def admin_reorder():
    ids = request.get_json(force=True).get('ids', [])
    with _lock:
        for i, lid in enumerate(ids, start=1):
            l = find_lesson(lid)
            if l:
                l['order'] = i
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True)

# ---------- videos (YouTube unlisted links) ----------
@app.post('/api/admin/lessons/<lid>/videos')
@admin_required
def admin_add_video(lid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    d = request.get_json(force=True)
    title = (d.get('title') or '').strip() or 'ວິດີໂອບົດຮຽນ'
    youtube_id = extract_youtube_id(d.get('youtube_url'))
    if not youtube_id:
        return jsonify(error='ລິ້ງ YouTube ບໍ່ຖືກຕ້ອງ (ວາງລິ້ງແບບ youtube.com/watch?v=... ຫຼື youtu.be/...)'), 400
    video = {'id': new_id('v_'), 'title': title, 'youtube_id': youtube_id, 'locked': True,
             'added_at': time.time()}
    with _lock:
        lesson['videos'].append(video)
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True, video=video)

@app.post('/api/admin/lessons/<lid>/videos/<vid>/toggle')
@admin_required
def admin_toggle_video(lid, vid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    with _lock:
        for v in lesson['videos']:
            if v['id'] == vid:
                v['locked'] = not v['locked']
                _save(LESSONS_FILE, lessons)
                return jsonify(ok=True, locked=v['locked'])
    return jsonify(error='ບໍ່ພົບວິດີໂອ'), 404

@app.delete('/api/admin/lessons/<lid>/videos/<vid>')
@admin_required
def admin_delete_video(lid, vid):
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    with _lock:
        for v in lesson['videos']:
            if v['id'] == vid:
                lesson['videos'].remove(v)
                _save(LESSONS_FILE, lessons)
                return jsonify(ok=True)
    return jsonify(error='ບໍ່ພົບວິດີໂອ'), 404

# ---------- questions (homework / quiz / exam) ----------
SECTIONS = {'homework', 'quiz', 'exam'}

@app.post('/api/admin/lessons/<lid>/<section>')
@admin_required
def admin_add_question(lid, section):
    if section not in SECTIONS:
        abort(404)
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    d = request.get_json(force=True)
    question = (d.get('question') or '').strip()
    if not question:
        return jsonify(error='ກະລຸນາປ້ອນຄໍາຖາມ'), 400
    q = {'id': new_id('q_'), 'question': question}
    if section in ('quiz', 'exam'):
        options = d.get('options') or []
        answer = d.get('answer')
        if len(options) < 2 or answer is None:
            return jsonify(error='ກະລຸນາປ້ອນຕົວເລືອກຢ່າງໜ້ອຍ 2 ຂໍ້ ແລະ ເລືອກຄໍາຕອບທີ່ຖືກ'), 400
        q['options'] = options
        q['answer'] = int(answer)
    with _lock:
        lesson[section].append(q)
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True, question=q)

@app.put('/api/admin/lessons/<lid>/<section>/<qid>')
@admin_required
def admin_edit_question(lid, section, qid):
    if section not in SECTIONS:
        abort(404)
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    d = request.get_json(force=True)
    with _lock:
        for q in lesson[section]:
            if q['id'] == qid:
                if 'question' in d:
                    q['question'] = d['question']
                if section in ('quiz', 'exam'):
                    if 'options' in d:
                        q['options'] = d['options']
                    if 'answer' in d:
                        q['answer'] = int(d['answer'])
                _save(LESSONS_FILE, lessons)
                return jsonify(ok=True, question=q)
    return jsonify(error='ບໍ່ພົບຄໍາຖາມ'), 404

@app.delete('/api/admin/lessons/<lid>/<section>/<qid>')
@admin_required
def admin_delete_question(lid, section, qid):
    if section not in SECTIONS:
        abort(404)
    lesson = find_lesson(lid)
    if not lesson:
        return jsonify(error='ບໍ່ພົບບົດຮຽນ'), 404
    with _lock:
        lesson[section] = [q for q in lesson[section] if q['id'] != qid]
        _save(LESSONS_FILE, lessons)
    return jsonify(ok=True)

# ---------- progress overview ----------
@app.get('/api/admin/progress')
@admin_required
def admin_progress():
    ordered = sorted_lessons()
    rows = []
    for u in users.values():
        if u['role'] != 'student' or u['status'] != 'approved':
            continue
        lesson_rows = []
        for l in ordered:
            prog = student_progress(u['username'], l['id'], create=False)
            lesson_rows.append({
                'lesson_id': l['id'], 'title_lo': l['title_lo'],
                'unlocked': is_unlocked(u['username'], l),
                'progress': prog,
            })
        rows.append({'username': u['username'], 'name': u['name'], 'lessons': lesson_rows})
    return jsonify(rows=rows)

# ---------- backup (free hosting tiers may not persist disk across deploys) ----------
@app.get('/api/admin/backup')
@admin_required
def admin_backup():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for path in (USERS_FILE, LESSONS_FILE, PROGRESS_FILE):
            z.writestr(os.path.basename(path), json.dumps(_load(path, [] if path == LESSONS_FILE else {}), ensure_ascii=False, indent=2))
        from backup_storage import append_platform_backup
        append_platform_backup(z, BASE, DATA)
    buf.seek(0)
    fname = time.strftime('thana-backup-%Y%m%d-%H%M%S.zip')
    return send_file(buf, mimetype='application/zip', as_attachment=True, download_name=fname)

from csrf import install_csrf
install_csrf(app)

from platform_routes import install
install(app, globals())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8035))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('THANA_DEBUG') == '1')
