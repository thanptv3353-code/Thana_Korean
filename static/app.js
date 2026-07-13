'use strict';
let ME = null;
let LESSONS = [];
let CURRENT_LESSON = null;

async function api(path, opts = {}) {
  const res = await fetch(path, {
    method: opts.method || 'GET',
    headers: opts.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    body: opts.body instanceof FormData ? opts.body : (opts.body ? JSON.stringify(opts.body) : undefined),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || 'ຜິດພາດ');
  return data;
}

function el(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}

// ---------------- boot ----------------
document.addEventListener('DOMContentLoaded', boot);

async function boot() {
  wireAuth();
  wireLesson();
  document.getElementById('btnLogout').onclick = logout;
  try {
    const { user } = await api('/api/me');
    if (user) { ME = user; afterLogin(); return; }
  } catch (e) {}
  showAuth();
}

function wireAuth() {
  document.getElementById('tabLogin').onclick = () => switchAuthTab('login');
  document.getElementById('tabRegister').onclick = () => switchAuthTab('register');
  document.getElementById('btnLogin').onclick = doLogin;
  document.getElementById('btnRegister').onclick = doRegister;
}

function switchAuthTab(which) {
  document.getElementById('tabLogin').classList.toggle('active', which === 'login');
  document.getElementById('tabRegister').classList.toggle('active', which === 'register');
  document.getElementById('formLogin').classList.toggle('hidden', which !== 'login');
  document.getElementById('formRegister').classList.toggle('hidden', which !== 'register');
  document.getElementById('authMsg').textContent = '';
}

async function doLogin() {
  const username = document.getElementById('liUser').value.trim();
  const password = document.getElementById('liPw').value;
  const msg = document.getElementById('authMsg');
  msg.textContent = '';
  try {
    const { user } = await api('/api/login', { method: 'POST', body: { username, password } });
    ME = user;
    afterLogin();
  } catch (e) { msg.textContent = e.message; msg.classList.add('error'); }
}

async function doRegister() {
  const name = document.getElementById('rgName').value.trim();
  const username = document.getElementById('rgUser').value.trim();
  const password = document.getElementById('rgPw').value;
  const msg = document.getElementById('authMsg');
  msg.textContent = '';
  try {
    const r = await api('/api/register', { method: 'POST', body: { name, username, password } });
    msg.textContent = r.message;
    msg.classList.remove('error');
    switchAuthTab('login');
  } catch (e) { msg.textContent = e.message; msg.classList.add('error'); }
}

async function logout() {
  await api('/api/logout', { method: 'POST' });
  ME = null;
  location.reload();
}

function afterLogin() {
  document.getElementById('userbox').classList.remove('hidden');
  document.getElementById('hello').textContent = `👋 ${ME.name}`;
  document.getElementById('adminLink').classList.toggle('hidden', ME.role !== 'admin');
  showDash();
}

function showAuth() {
  hideAll();
  document.getElementById('viewAuth').classList.remove('hidden');
}

function hideAll() {
  ['viewAuth', 'viewDash', 'viewLesson'].forEach(id => document.getElementById(id).classList.add('hidden'));
}

// ---------------- dashboard ----------------
async function showDash() {
  hideAll();
  document.getElementById('viewDash').classList.remove('hidden');
  const { lessons } = await api('/api/lessons');
  LESSONS = lessons;
  renderLessonList();
}

function renderLessonList() {
  const wrap = document.getElementById('lessonList');
  wrap.innerHTML = '';
  if (!LESSONS.length) {
    wrap.appendChild(el('p', 'muted', 'ຍັງບໍ່ມີບົດຮຽນ, ກະລຸນາລໍຖ້າ admin ເພີ່ມເນື້ອຫາ'));
    return;
  }
  LESSONS.forEach(l => {
    const card = el('div', 'lessoncard ' + l.status);
    const badge = { locked: '🔒 ລ໋ອກ', in_progress: '▶ ກຳລັງຮຽນ', completed: '✅ ຮຽນຈົບ' }[l.status];
    card.innerHTML = `
      <div class="lc-top">
        <span class="lc-order">ບົດທີ ${l.order}</span>
        <span class="lc-badge">${badge}</span>
      </div>
      <h3>${escapeHtml(l.title_lo)}</h3>
      <p class="ko">${escapeHtml(l.title_ko || '')}</p>
      <p class="muted small">${escapeHtml(l.description || '')}</p>
      <div class="lc-meta">🎬 ${l.video_count}  📝 ${l.homework_count}  ❓ ${l.quiz_count}  🏆 ${l.exam_count}</div>
    `;
    if (l.status !== 'locked') {
      card.onclick = () => openLesson(l.id);
    }
    wrap.appendChild(card);
  });
}

// ---------------- lesson detail ----------------
function wireLesson() {
  document.querySelectorAll('#lessonTabs .tab').forEach(btn => {
    btn.onclick = () => switchLessonTab(btn.dataset.tab);
  });
  document.getElementById('btnSubmitHomework').onclick = submitHomework;
  document.getElementById('btnSubmitQuiz').onclick = submitQuiz;
  document.getElementById('btnSubmitExam').onclick = submitExam;
}

async function openLesson(lid) {
  try {
    const { lesson } = await api('/api/lessons/' + lid);
    CURRENT_LESSON = lesson;
    hideAll();
    document.getElementById('viewLesson').classList.remove('hidden');
    document.getElementById('lsTitleLo').textContent = `ບົດທີ ${lesson.order}: ${lesson.title_lo}`;
    document.getElementById('lsTitleKo').textContent = lesson.title_ko || '';
    document.getElementById('lsDesc').textContent = lesson.description || '';
    switchLessonTab('video');
    renderVideo();
    renderHomework();
    renderQuiz();
    renderExam();
  } catch (e) { alert(e.message); }
}

function switchLessonTab(tab) {
  document.querySelectorAll('#lessonTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  ['video', 'homework', 'quiz', 'exam'].forEach(t => {
    document.getElementById('pane' + t.charAt(0).toUpperCase() + t.slice(1)).classList.toggle('hidden', t !== tab);
  });
}

function renderVideo() {
  const wrap = document.getElementById('videoList');
  wrap.innerHTML = '';
  if (!CURRENT_LESSON.videos.length) {
    wrap.appendChild(el('p', 'muted', 'ຍັງບໍ່ມີວິດີໂອໃນບົດນີ້'));
    return;
  }
  CURRENT_LESSON.videos.forEach(v => {
    const box = el('div', 'videobox');
    if (v.playable) {
      box.innerHTML = `<h4>${escapeHtml(v.title)}</h4>
        <div class="videoframe"><iframe src="${v.embed_url}" title="${escapeHtml(v.title)}"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowfullscreen></iframe></div>`;
    } else {
      box.innerHTML = `<h4>${escapeHtml(v.title)}</h4><div class="videolocked">🔒 admin ຍັງບໍ່ໄດ້ປົດລ໋ອກວິດີໂອນີ້</div>`;
    }
    wrap.appendChild(box);
  });
}

function renderHomework() {
  const wrap = document.getElementById('homeworkForm');
  wrap.innerHTML = '';
  const prev = (CURRENT_LESSON.progress && CURRENT_LESSON.progress.homework_answers) || {};
  if (!CURRENT_LESSON.homework.length) {
    wrap.appendChild(el('p', 'muted', 'ຍັງບໍ່ມີວຽກບ້ານໃນບົດນີ້'));
    document.getElementById('btnSubmitHomework').classList.add('hidden');
    return;
  }
  document.getElementById('btnSubmitHomework').classList.remove('hidden');
  CURRENT_LESSON.homework.forEach((q, i) => {
    const box = el('div', 'qbox');
    box.innerHTML = `<label>${i + 1}. ${escapeHtml(q.question)}
      <textarea rows="2" data-qid="${q.id}">${escapeHtml(prev[q.id] || '')}</textarea></label>`;
    wrap.appendChild(box);
  });
  if (CURRENT_LESSON.progress && CURRENT_LESSON.progress.homework_done) {
    document.getElementById('homeworkMsg').textContent = '✅ ສົ່ງແລ້ວ, ສາມາດແກ້ໄຂ ແລະ ສົ່ງໃໝ່ໄດ້';
  }
}

async function submitHomework() {
  const answers = {};
  document.querySelectorAll('#homeworkForm textarea').forEach(t => { answers[t.dataset.qid] = t.value; });
  try {
    const r = await api(`/api/lessons/${CURRENT_LESSON.id}/homework`, { method: 'POST', body: { answers } });
    document.getElementById('homeworkMsg').textContent = '✅ ' + r.message;
  } catch (e) { document.getElementById('homeworkMsg').textContent = e.message; }
}

function renderChoiceForm(containerId, questions) {
  const wrap = document.getElementById(containerId);
  wrap.innerHTML = '';
  if (!questions.length) {
    wrap.appendChild(el('p', 'muted', 'ຍັງບໍ່ມີຄໍາຖາມ'));
    return;
  }
  questions.forEach((q, i) => {
    const box = el('div', 'qbox');
    box.innerHTML = `<div class="qtext">${i + 1}. ${escapeHtml(q.question)}</div>`;
    const opts = el('div', 'options');
    q.options.forEach((opt, oi) => {
      const id = `${containerId}_${q.id}_${oi}`;
      const label = el('label', 'optlabel');
      label.innerHTML = `<input type="radio" name="${containerId}_${q.id}" value="${oi}" id="${id}"> ${escapeHtml(opt)}`;
      opts.appendChild(label);
    });
    box.appendChild(opts);
    wrap.appendChild(box);
  });
}

function collectChoiceAnswers(containerId, questions) {
  const answers = {};
  questions.forEach(q => {
    const checked = document.querySelector(`input[name="${containerId}_${q.id}"]:checked`);
    if (checked) answers[q.id] = parseInt(checked.value, 10);
  });
  return answers;
}

function renderQuiz() {
  const prog = CURRENT_LESSON.progress;
  document.getElementById('quizBest').textContent = prog && prog.quiz_attempts
    ? `ຄະແນນດີສຸດ: ${prog.quiz_best}% (ພະຍາຍາມ ${prog.quiz_attempts} ຄັ້ງ)` : '';
  renderChoiceForm('quizForm', CURRENT_LESSON.quiz);
  document.getElementById('quizResult').classList.add('hidden');
  document.getElementById('btnSubmitQuiz').classList.toggle('hidden', !CURRENT_LESSON.quiz.length);
}

async function submitQuiz() {
  const answers = collectChoiceAnswers('quizForm', CURRENT_LESSON.quiz);
  try {
    const r = await api(`/api/lessons/${CURRENT_LESSON.id}/quiz`, { method: 'POST', body: { answers } });
    const box = document.getElementById('quizResult');
    box.classList.remove('hidden');
    box.innerHTML = `<div class="scorebig">${r.score}%</div>`;
    if (!CURRENT_LESSON.progress) CURRENT_LESSON.progress = {};
    CURRENT_LESSON.progress.quiz_best = Math.max(CURRENT_LESSON.progress.quiz_best || 0, r.score);
    CURRENT_LESSON.progress.quiz_attempts = (CURRENT_LESSON.progress.quiz_attempts || 0) + 1;
    document.getElementById('quizBest').textContent = `ຄະແນນດີສຸດ: ${CURRENT_LESSON.progress.quiz_best}% (ພະຍາຍາມ ${CURRENT_LESSON.progress.quiz_attempts} ຄັ້ງ)`;
  } catch (e) { alert(e.message); }
}

function renderExam() {
  const prog = CURRENT_LESSON.progress;
  document.getElementById('examBest').textContent = prog && prog.exam_attempts
    ? `ຄະແນນດີສຸດ: ${prog.exam_best}% (ພະຍາຍາມ ${prog.exam_attempts} ຄັ້ງ) ${prog.exam_passed ? '✅ ຜ່ານແລ້ວ' : ''}` : '';
  renderChoiceForm('examForm', CURRENT_LESSON.exam);
  document.getElementById('examResult').classList.add('hidden');
  document.getElementById('btnSubmitExam').classList.toggle('hidden', !CURRENT_LESSON.exam.length);
}

async function submitExam() {
  const answers = collectChoiceAnswers('examForm', CURRENT_LESSON.exam);
  try {
    const r = await api(`/api/lessons/${CURRENT_LESSON.id}/exam`, { method: 'POST', body: { answers } });
    const box = document.getElementById('examResult');
    box.classList.remove('hidden');
    if (r.passed) {
      box.innerHTML = `<div class="scorebig pass">${r.score}%</div><p class="passmsg">🎉 ຜ່ານແລ້ວ! ບົດຕໍ່ໄປໄດ້ຖືກປົດລ໋ອກອັດຕະໂນມັດ</p>
        <button class="btn primary" onclick="showDash()">ໄປບົດຕໍ່ໄປ →</button>`;
    } else {
      box.innerHTML = `<div class="scorebig fail">${r.score}%</div><p class="failmsg">ຍັງບໍ່ຜ່ານ (ຕ້ອງໄດ້ ${r.threshold}%+) ລອງໃໝ່ໄດ້</p>`;
    }
    if (!CURRENT_LESSON.progress) CURRENT_LESSON.progress = {};
    CURRENT_LESSON.progress.exam_best = Math.max(CURRENT_LESSON.progress.exam_best || 0, r.score);
    CURRENT_LESSON.progress.exam_attempts = (CURRENT_LESSON.progress.exam_attempts || 0) + 1;
    CURRENT_LESSON.progress.exam_passed = CURRENT_LESSON.progress.exam_passed || r.passed;
  } catch (e) { alert(e.message); }
}

function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
