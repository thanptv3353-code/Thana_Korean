'use strict';
const $=id=>document.getElementById(id);
let run=null,timer=null,expires=0,pending=Promise.resolve(),finishing=false,retryAt=0,configVersion=0;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cats={blank:'ເຕີມຄຳ / 빈칸',img_word:'ຮູບ / 그림',sign:'ປ້າຍ / 표지판',qa:'ຖາມຕອບ / 문답',reading:'ອ່ານ / 읽기'};
const skillName=skill=>skill==='listening'?'ຟັງ / 듣기':'ອ່ານ / 읽기';
const storageKey=skill=>'thana-mock-run-'+skill;
const imageURL=q=>q.image.startsWith('/media/library/')?q.image:'/static/eps-images/'+encodeURIComponent(q.image);
function error(e){$('message').textContent=e.message;}
async function api(url,body){
 const token=body?(await(await fetch('/api/csrf')).json()).token:'';
 const r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:body?JSON.stringify(body):undefined});
 const d=await r.json();
 if(!r.ok){if(d.finished)showResult(d.result,run?.id);const e=Error(d.error||'Error');e.finished=!!d.finished;throw e;}return d;
}
function clearStored(id,skill){if(id&&localStorage.getItem(storageKey(skill))===id)localStorage.removeItem(storageKey(skill));if(skill==='reading'&&id&&localStorage.getItem('thana-mock-run')===id)localStorage.removeItem('thana-mock-run');}
function audioMarkup(q){return q.skill==='listening'&&q.audio?`<audio controls preload="none" src="${esc(q.audio)}" aria-label="ຟັງ / 듣기"></audio>${q.audio_ai_generated?'<p>AI · ສຽງສ້າງໂດຍ AI / AI 생성 음성</p>':''}`:'';}
function showResult(r,id=run?.id){
 const skill=r.skill||run?.skill||'reading';clearStored(id,skill);clearInterval(timer);
 $('timer').hidden=true;$('finish').hidden=true;$('start').disabled=false;$('mockSkill').disabled=false;$('mockSkill').value=skill;
 $('questions').querySelectorAll('input').forEach(e=>e.disabled=true);
 $('questions').querySelectorAll('audio').forEach(e=>e.pause());
 $('result').innerHTML=`<article><h2>${r.score} / ${r.total} · ${skillName(skill)}</h2>${Object.entries(r.categories).map(([cat,v])=>`<p>${esc(cats[cat]||cat)} · ${v.correct}/${v.total}</p>`).join('')}<details><summary>ກວດຄຳຕອບ / 정답 확인</summary>${r.detail.map((q,i)=>`<article><h3>${i+1}. ${esc(q.question?.stem_ko||('EPS #'+q.id))}</h3><p>${esc(q.question?.stem_lo||'')}</p>${q.question?audioMarkup(q.question):''}${q.question?.image?`<img class="question-image" src="${esc(imageURL(q.question))}" alt="EPS question">`:''}<p>${esc(q.question?.passage_ko||'')}</p><p>${esc(q.question?.passage_lo||'')}</p><p>${q.correct?'✓':'✗'} · ${q.given??'—'} → ${q.answer} · ${esc(q.question?.choices_ko?.[q.answer-1]||'')} · ${esc(q.question?.choices_lo?.[q.answer-1]||'')}${q.verified?'':' · ລໍຖ້າກວດທານ / 검토 대기'}</p><p>${esc(q.explanation_ko||'')}</p><p>${esc(q.explanation_lo||'')}</p></article>`).join('')}</details></article>`;
 run=null;history();loadConfig().catch(error);
}
async function resume(id){
 const d=await api('/api/platform/mock/'+encodeURIComponent(id));
 if(d.finished){showResult(d.result,id);return;}
 const skill=d.skill||'reading';if(run?.id!==id)pending=Promise.resolve();run={id,skill};
 $('mockSkill').value=skill;$('mockSkill').disabled=true;localStorage.setItem(storageKey(skill),id);
 expires=performance.now()+d.remaining*1000;$('start').disabled=true;$('finish').hidden=false;$('timer').hidden=false;$('result').replaceChildren();$('questions').replaceChildren();
 $('history').querySelectorAll('button').forEach(b=>b.disabled=true);
 for(const [i,q] of d.questions.entries()){
  const box=document.createElement('article');
  box.innerHTML=`<p>${i+1}/${d.questions.length}${q.verified?'':' · ລໍຖ້າກວດທານ / 검토 대기'}</p>${audioMarkup(q)}${q.image?`<img class="question-image" src="${esc(imageURL(q))}" alt="EPS question">`:''}<p>${esc(q.passage_ko)}</p><p>${esc(q.passage_lo)}</p><h3>${esc(q.stem_ko)}</h3><p>${esc(q.stem_lo)}</p><fieldset><legend>ຄຳຕອບ / 답</legend>${q.choices_ko.map((c,j)=>`<label><input type="radio" name="q${q.id}" value="${j+1}" ${d.answers[q.id]===j+1?'checked':''}>${j+1}. ${esc(c)} · ${esc((q.choices_lo||[])[j])}</label>`).join('')}</fieldset>`;
  box.querySelector('audio')?.addEventListener('error',()=>error(Error('ໂຫຼດສຽງບໍ່ໄດ້. ກວດເນັດ ແລະ ແຈ້ງຄູ; ເວລາສອບຍັງເດີນຢູ່. / 음성을 불러올 수 없습니다. 연결을 확인하고 교사에게 알리세요. 시험 시간은 계속됩니다.')));
  box.addEventListener('change',e=>{
   if(!e.target.matches('input[type=radio]'))return;const aid=run?.id;if(!aid)return;const choice=Number(e.target.value);$('saveStatus').textContent='ກຳລັງບັນທຶກ / 저장 중';
   pending=pending.then(async()=>{if(run?.id!==aid)return;try{await api('/api/platform/mock/'+encodeURIComponent(aid)+'/answer',{id:q.id,choice});$('saveStatus').textContent='✓ ບັນທຶກແລ້ວ / 저장 완료';}catch(e){$('saveStatus').textContent='ຄຳຕອບນີ້ຍັງບໍ່ບັນທຶກ / 저장되지 않았습니다';error(e);}});
  });$('questions').append(box);
 }
 clearInterval(timer);timer=setInterval(tick,250);tick();
}
function tick(){const n=Math.max(0,Math.ceil((expires-performance.now())/1000));$('timer').textContent=`⏱ ${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;if(n===0&&!finishing&&performance.now()>=retryAt)finish();}
async function finish(){
 if(!run||finishing)return;finishing=true;const id=run.id;$('questions').querySelectorAll('input').forEach(e=>e.disabled=true);$('finish').disabled=true;
 try{await pending;if(!run)return;const d=await api('/api/platform/mock/'+encodeURIComponent(id)+'/finish',{});showResult(d.result,id);}
 catch(e){retryAt=performance.now()+5000;error(e);if(run&&performance.now()<expires)$('questions').querySelectorAll('input').forEach(e=>e.disabled=false);}
 finally{finishing=false;$('finish').disabled=false;}
}
$('start').onclick=async()=>{const skill=$('mockSkill').value;$('start').disabled=true;try{$('message').textContent='';const d=await api('/api/platform/mock',{skill});await resume(d.id);}catch(e){error(e);}finally{if(!run)$('start').disabled=false;}};
$('finish').onclick=finish;
async function history(){
 try{const d=await api('/api/platform/mock/history');$('history').replaceChildren();if(!d.attempts.length)$('history').textContent='ຍັງບໍ່ມີ / 기록 없음';
  for(const a of d.attempts){const box=document.createElement('article'),text=document.createElement('p'),button=document.createElement('button');text.textContent=new Date(a.finished*1000).toLocaleString()+' · '+skillName(a.skill)+' · '+a.result.score+'/'+a.result.total;button.textContent='ກວດຄຳຕອບ / 해설 보기';button.disabled=!!run;button.onclick=()=>resume(a.id).catch(error);box.append(text,button);$('history').append(box);}
 }catch(e){$('history').textContent='ເຂົ້າລະບົບເພື່ອເບິ່ງ / 로그인 필요';}
}
async function loadConfig(){const version=++configVersion,skill=$('mockSkill').value;const d=await api('/api/platform/mock/settings?skill='+skill);if(version!==configVersion)return;$('settings').textContent=`${skillName(skill)} · ${d.settings.count} ຂໍ້ / 문항 · ${d.settings.seconds/60} ນາທີ / 분 · ${d.available} ຂໍ້ພ້ອມໃຊ້ / 사용 가능${d.settings.verified_only?' · ກວດທານແລ້ວ / 검토 완료':' · ມີຄຳຖາມລໍຖ້າກວດ / 검토 대기 문항 포함'}`;}
async function chooseSkill(){if(run){$('mockSkill').value=run.skill;return;}await loadConfig();const skill=$('mockSkill').value,previous=localStorage.getItem(storageKey(skill))||(skill==='reading'?localStorage.getItem('thana-mock-run'):null);if(previous)await resume(previous);}
$('mockSkill').onchange=()=>{if(!run){$('questions').replaceChildren();$('result').replaceChildren();$('saveStatus').textContent='';$('message').textContent='';}chooseSkill().catch(error);};
const initialSkill=new URLSearchParams(location.search).get('skill');if(['reading','listening'].includes(initialSkill))$('mockSkill').value=initialSkill;
history();chooseSkill().catch(error);
window.addEventListener('pagehide',()=>clearInterval(timer));
window.addEventListener('pageshow',e=>{if(e.persisted&&run)pending.then(()=>resume(run.id)).catch(error);});
