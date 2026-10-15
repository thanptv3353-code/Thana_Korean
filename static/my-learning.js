'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function get(path){const r=await fetch(path),d=await r.json();if(!r.ok){const e=Error(d.error||'ບໍ່ສາມາດໂຫຼດ / 불러오기 실패');e.status=r.status;throw e;}return d;}
const date=t=>new Date(t*1000).toLocaleString();
const empty='ຍັງບໍ່ມີຂໍ້ມູນ / 아직 기록이 없습니다';
async function load(){try{
 const p=await get('/api/platform/learning-progress');
 const [catalog,review,practice,mock]=await Promise.allSettled(['/api/platform/courses','/api/platform/review','/api/platform/history','/api/platform/mock/history'].map(get));
 const metrics=[['XP',p.xp],['Level',p.level],['ມື້ຕໍ່ເນື່ອງ / 연속 학습일',p.streak],['ບົດທີ່ຜ່ານ / 완료 수업',p.completed.length]];
 if(review.status==='fulfilled')metrics.push(['ຄຳຄວນທົບທວນ / 복습할 단어',review.value.total]);
 $('metrics').innerHTML=metrics.map(([label,value])=>`<article>${esc(label)}<strong>${esc(value)}</strong></article>`).join('');
 const lessons=new Map();if(catalog.status==='fulfilled')for(const c of catalog.value.courses)for(const l of c.lessons)lessons.set(c.legacy?'legacy:'+l.id:l.id,{title:l.title,url:c.legacy?'/learn?lesson='+encodeURIComponent(l.id):'/courses?language='+c.language+'&lesson='+encodeURIComponent(l.id)});
 $('completed').innerHTML=p.completed.length?p.completed.map(id=>{const l=lessons.get(id);return l?`<a href="${esc(l.url)}">✓ ${esc(l.title)}</a>`:'<p>✓ ບົດຮຽນທີ່ບໍ່ເຜີຍແຜ່ໃນປັດຈຸບັນ / 현재 비공개 수업</p>';}).join(''):empty;
 const failure='ບໍ່ສາມາດໂຫຼດສ່ວນນີ້ ລອງໂຫຼດໜ້າຄືນ / 새로고침 후 다시 시도하세요';
 $('practice').innerHTML=practice.status==='fulfilled'?(practice.value.attempts.length?practice.value.attempts.map(a=>`<article>${esc(a.category)} · <strong>${esc(a.score)} / ${esc(a.total)}</strong> · ${esc(date(a.finished))}</article>`).join(''):empty):failure;
 $('exams').innerHTML=mock.status==='fulfilled'?(mock.value.attempts.length?mock.value.attempts.map(a=>`<article><strong>${esc(a.result.score)} / ${esc(a.result.total)}</strong> · ${esc(date(a.finished))}</article>`).join(''):empty):failure;
 $('content').hidden=false;$('message').textContent='';
 }catch(e){$('message').textContent=e.status===401?'ກະລຸນາເຂົ້າລະບົບເພື່ອເບິ່ງຜົນການຮຽນ / 로그인하여 학습 현황을 확인하세요':e.message;$('signIn').hidden=e.status!==401;}}
load();
