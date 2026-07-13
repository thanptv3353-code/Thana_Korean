'use strict';
let LESSONS = [];
let ACTIVE_LESSON_ID = null;

async function api(path, opts = {}) {
  const isForm = opts.body instanceof FormData;
  const res = await fetch(path, {
    method: opts.method || 'GET',
    headers: isForm ? {} : { 'Content-Type': 'application/json' },
    body: isForm ? opts.body : (opts.body ? JSON.stringify(opts.body) : undefined),
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
function escapeHtml(s) {
  return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

document.addEventListener('DOMContentLoaded', boot);

async function boot() {
  document.getElementById('btnLogin').onclick = doLogin;
  document.getElementById('btnLogout').onclick = doLogout;
  document.querySelectorAll('#adminTabs .tab').forEach(b => b.onclick = () => switchAdminTab(b.dataset.tab));
  document.querySelectorAll('#modalTabs .tab').forEach(b => b.onclick = () => switchModalTab(b.dataset.mtab));
  document.getElementById('btnCloseModal').onclick = closeModal;
  document.getElementById('btnAddLesson').onclick = addLesson;
  document.getElementById('videoUploadForm').addEventListener('submit', uploadVideo);
  document.getElementById('btnAddHw').onclick = () => addQuestion('homework');
  document.getElementById('btnAddQuiz').onclick = () => addQuestion('quiz');
  document.getElementById('btnAddExam').onclick = () => addQuestion('exam');

  try {
    const { user } = await api('/api/me');
    if (user && user.role === 'admin') { afterLogin(); return; }
  } catch (e) {}
  document.getElementById('viewAdminAuth').classList.remove('hidden');
}

async function doLogin() {
  const username = document.getElementById('liUser').value.trim();
  const password = document.getElementById('liPw').value;
  const msg = document.getElementById('authMsg');
  try {
    const { user } = await api('/api/login', { method: 'POST', body: { username, password } });
    if (user.role !== 'admin') throw new Error('ບັນຊີນີ້ບໍ່ແມ່ນ admin');
    afterLogin();
  } catch (e) { msg.textContent = e.message; }
}

async function doLogout() {
  await api('/api/logout', { method: 'POST' });
  location.reload();
}

function afterLogin() {
  document.getElementById('viewAdminAuth').classList.add('hidden');
  document.getElementById('viewAdmin').classList.remove('hidden');
  loadStudents();
  loadLessons();
}

function switchAdminTab(tab) {
  document.querySelectorAll('#adminTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  ['students', 'lessons', 'progress'].forEach(t => {
    document.getElementById('pane' + t.charAt(0).toUpperCase() + t.slice(1)).classList.toggle('hidden', t !== tab);
  });
  if (tab === 'progress') loadProgress();
  if (tab === 'students') loadStudents();
}

// ---------------- students ----------------
async function loadStudents() {
  const { students } = await api('/api/admin/students');
  const tbody = document.getElementById('studentRows');
  tbody.innerHTML = '';
  if (!students.length) {
    tbody.innerHTML = '<tr><td colspan="4" class="muted">ຍັງບໍ່ມີນັກຮຽນ</td></tr>';
    return;
  }
  students.forEach(s => {
    const tr = document.createElement('tr');
    const statusLabel = { pending: '⏳ ລໍຖ້າອະນຸມັດ', approved: '✅ ອະນຸມັດແລ້ວ', rejected: '❌ ປະຕິເສດ' }[s.status];
    tr.innerHTML = `<td>${escapeHtml(s.name)}</td><td>${escapeHtml(s.username)}</td><td>${statusLabel}</td><td class="actions"></td>`;
    const actions = tr.querySelector('.actions');
    if (s.status !== 'approved') {
      const b = el('button', 'btn small primary', 'ອະນຸມັດ');
      b.onclick = async () => { await api(`/api/admin/students/${s.username}/approve`, { method: 'POST' }); loadStudents(); };
      actions.appendChild(b);
    }
    if (s.status !== 'rejected') {
      const b = el('button', 'btn small outline', 'ປະຕິເສດ');
      b.onclick = async () => { await api(`/api/admin/students/${s.username}/reject`, { method: 'POST' }); loadStudents(); };
      actions.appendChild(b);
    }
    const del = el('button', 'btn small danger', 'ລຶບ');
    del.onclick = async () => {
      if (!confirm(`ລຶບບັນຊີ ${s.username}?`)) return;
      await api(`/api/admin/students/${s.username}`, { method: 'DELETE' });
      loadStudents();
    };
    actions.appendChild(del);
    tbody.appendChild(tr);
  });
}

// ---------------- lessons ----------------
async function loadLessons() {
  const { lessons } = await api('/api/admin/lessons');
  LESSONS = lessons;
  renderLessonAdminList();
}

function renderLessonAdminList() {
  const wrap = document.getElementById('lessonAdminList');
  wrap.innerHTML = '';
  LESSONS.slice().sort((a, b) => a.order - b.order).forEach(l => {
    const card = el('div', 'lessonadminrow');
    card.innerHTML = `
      <div class="lar-main">
        <b>ບົດທີ ${l.order}: ${escapeHtml(l.title_lo)}</b>
        <span class="ko">${escapeHtml(l.title_ko || '')}</span>
        <span class="muted small">🎬${l.videos.length} 📝${l.homework.length} ❓${l.quiz.length} 🏆${l.exam.length}</span>
      </div>
      <div class="lar-actions"></div>
    `;
    const actions = card.querySelector('.lar-actions');
    const editBtn = el('button', 'btn small primary', 'ຈັດການເນື້ອຫາ');
    editBtn.onclick = () => openModal(l.id);
    const delBtn = el('button', 'btn small danger', 'ລຶບບົດ');
    delBtn.onclick = async () => {
      if (!confirm(`ລຶບບົດຮຽນ "${l.title_lo}"? (ວິດີໂອຈະຖືກລຶບຖາວອນ)`)) return;
      await api(`/api/admin/lessons/${l.id}`, { method: 'DELETE' });
      loadLessons();
    };
    actions.appendChild(editBtn);
    actions.appendChild(delBtn);
    wrap.appendChild(card);
  });
}

async function addLesson() {
  const title_lo = document.getElementById('newLessonLo').value.trim();
  const title_ko = document.getElementById('newLessonKo').value.trim();
  const description = document.getElementById('newLessonDesc').value.trim();
  if (!title_lo) return alert('ກະລຸນາປ້ອນຊື່ບົດຮຽນ');
  await api('/api/admin/lessons', { method: 'POST', body: { title_lo, title_ko, description } });
  document.getElementById('newLessonLo').value = '';
  document.getElementById('newLessonKo').value = '';
  document.getElementById('newLessonDesc').value = '';
  loadLessons();
}

// ---------------- lesson content modal ----------------
function openModal(lid) {
  ACTIVE_LESSON_ID = lid;
  const l = LESSONS.find(x => x.id === lid);
  document.getElementById('modalTitle').textContent = `ບົດທີ ${l.order}: ${l.title_lo}`;
  document.getElementById('lessonModal').classList.remove('hidden');
  switchModalTab('videos');
  renderModalContent();
}
function closeModal() {
  document.getElementById('lessonModal').classList.add('hidden');
  ACTIVE_LESSON_ID = null;
}
function switchModalTab(tab) {
  document.querySelectorAll('#modalTabs .tab').forEach(b => b.classList.toggle('active', b.dataset.mtab === tab));
  ['videos', 'homework', 'quiz', 'exam'].forEach(t => {
    document.getElementById('mp' + t.charAt(0).toUpperCase() + t.slice(1)).classList.toggle('hidden', t !== tab);
  });
}

function currentLesson() { return LESSONS.find(x => x.id === ACTIVE_LESSON_ID); }

function renderModalContent() {
  const l = currentLesson();
  if (!l) return;
  // videos
  const vwrap = document.getElementById('videoAdminList');
  vwrap.innerHTML = '';
  l.videos.forEach(v => {
    const row = el('div', 'modalrow');
    row.innerHTML = `<span>${escapeHtml(v.title)}</span> <span class="tag ${v.locked ? 'locktag' : 'unlocktag'}">${v.locked ? '🔒 ລ໋ອກ' : '🔓 ປົດລ໋ອກ'}</span>`;
    const toggle = el('button', 'btn small ' + (v.locked ? 'primary' : 'outline'), v.locked ? 'ປົດລ໋ອກ' : 'ລ໋ອກ');
    toggle.onclick = async () => {
      await api(`/api/admin/lessons/${l.id}/videos/${v.id}/toggle`, { method: 'POST' });
      await loadLessons(); renderModalContent();
    };
    const del = el('button', 'btn small danger', 'ລຶບ');
    del.onclick = async () => {
      if (!confirm('ລຶບວິດີໂອນີ້?')) return;
      await api(`/api/admin/lessons/${l.id}/videos/${v.id}`, { method: 'DELETE' });
      await loadLessons(); renderModalContent();
    };
    row.appendChild(toggle); row.appendChild(del);
    vwrap.appendChild(row);
  });
  // homework
  renderSimpleQList('hwAdminList', l, 'homework');
  // quiz / exam
  renderChoiceQList('quizAdminList', l, 'quiz');
  renderChoiceQList('examAdminList', l, 'exam');
}

function renderSimpleQList(containerId, lesson, section) {
  const wrap = document.getElementById(containerId);
  wrap.innerHTML = '';
  lesson[section].forEach((q, i) => {
    const row = el('div', 'modalrow');
    row.innerHTML = `<span>${i + 1}. ${escapeHtml(q.question)}</span>`;
    const del = el('button', 'btn small danger', 'ລຶບ');
    del.onclick = async () => {
      await api(`/api/admin/lessons/${lesson.id}/${section}/${q.id}`, { method: 'DELETE' });
      await loadLessons(); renderModalContent();
    };
    row.appendChild(del);
    wrap.appendChild(row);
  });
}

function renderChoiceQList(containerId, lesson, section) {
  const wrap = document.getElementById(containerId);
  wrap.innerHTML = '';
  lesson[section].forEach((q, i) => {
    const row = el('div', 'modalrow choicerow');
    const optsHtml = q.options.map((o, oi) => `<span class="${oi === q.answer ? 'correctopt' : ''}">${oi + 1}) ${escapeHtml(o)}</span>`).join(' ');
    row.innerHTML = `<div><b>${i + 1}. ${escapeHtml(q.question)}</b><div class="optrow">${optsHtml}</div></div>`;
    const del = el('button', 'btn small danger', 'ລຶບ');
    del.onclick = async () => {
      await api(`/api/admin/lessons/${lesson.id}/${section}/${q.id}`, { method: 'DELETE' });
      await loadLessons(); renderModalContent();
    };
    row.appendChild(del);
    wrap.appendChild(row);
  });
}

async function addQuestion(section) {
  const l = currentLesson();
  if (!l) return;
  const prefix = { homework: 'hw', quiz: 'quiz', exam: 'exam' }[section];
  const question = document.getElementById(`${prefix}Question`).value.trim();
  if (!question) return alert('ກະລຸນາປ້ອນຄໍາຖາມ');
  const body = { question };
  if (section !== 'homework') {
    const options = [0, 1, 2, 3].map(i => document.getElementById(`${prefix}Opt${i}`).value.trim()).filter(Boolean);
    const answerNum = parseInt(document.getElementById(`${prefix}Answer`).value, 10);
    if (options.length < 2) return alert('ກະລຸນາປ້ອນຕົວເລືອກຢ່າງໜ້ອຍ 2 ຂໍ້');
    if (!answerNum || answerNum < 1 || answerNum > options.length) return alert('ໝາຍເລກຄໍາຕອບບໍ່ຖືກຕ້ອງ');
    body.options = options;
    body.answer = answerNum - 1;
  }
  await api(`/api/admin/lessons/${l.id}/${section}`, { method: 'POST', body });
  document.getElementById(`${prefix}Question`).value = '';
  if (section !== 'homework') {
    [0, 1, 2, 3].forEach(i => document.getElementById(`${prefix}Opt${i}`).value = '');
    document.getElementById(`${prefix}Answer`).value = 1;
  }
  await loadLessons(); renderModalContent();
}

async function uploadVideo(e) {
  e.preventDefault();
  const l = currentLesson();
  if (!l) return;
  const title = document.getElementById('videoTitle').value.trim();
  const youtube_url = document.getElementById('videoUrl').value.trim();
  if (!youtube_url) return alert('ກະລຸນາວາງລິ້ງ YouTube');
  const btn = e.target.querySelector('button[type=submit]');
  btn.disabled = true; btn.textContent = 'ກຳລັງເພີ່ມ...';
  try {
    await api(`/api/admin/lessons/${l.id}/videos`, { method: 'POST', body: { title, youtube_url } });
    document.getElementById('videoTitle').value = '';
    document.getElementById('videoUrl').value = '';
    await loadLessons(); renderModalContent();
  } catch (err) { alert(err.message); }
  btn.disabled = false; btn.textContent = '➕ ເພີ່ມວິດີໂອ';
}

// ---------------- progress ----------------
async function loadProgress() {
  const { rows } = await api('/api/admin/progress');
  const wrap = document.getElementById('progressTableWrap');
  if (!rows.length) { wrap.innerHTML = '<p class="muted">ຍັງບໍ່ມີນັກຮຽນທີ່ອະນຸມັດແລ້ວ</p>'; return; }
  const lessonTitles = rows[0].lessons.map(l => l.title_lo);
  let html = '<table class="admintable"><thead><tr><th>ນັກຮຽນ</th>';
  lessonTitles.forEach(t => html += `<th>${escapeHtml(t)}</th>`);
  html += '</tr></thead><tbody>';
  rows.forEach(r => {
    html += `<tr><td>${escapeHtml(r.name)}</td>`;
    r.lessons.forEach(l => {
      let cell = '🔒';
      if (l.unlocked) {
        if (l.progress && l.progress.exam_passed) cell = `✅ ${l.progress.exam_best}%`;
        else if (l.progress) cell = `▶ exam:${l.progress.exam_best}% quiz:${l.progress.quiz_best}%`;
        else cell = '▶';
      }
      html += `<td>${cell}</td>`;
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  wrap.innerHTML = html;
}
