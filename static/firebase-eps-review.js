'use strict';
const $=id=>document.getElementById(id);
let page=1,generation=0;
const dirty=new Set();
async function api(path,body){
 const csrf=body?(await(await fetch('/api/csrf')).json()).token:'';
 const response=await fetch('/api/platform/admin/firebase-eps'+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:body?JSON.stringify(body):undefined});
 const data=await response.json();if(!response.ok)throw Error(data.error||'ດຳເນີນການບໍ່ສຳເລັດ / 요청 실패');return data;
}
function text(tag,value,parent){const element=document.createElement(tag);element.textContent=value;parent.append(element);return element;}
function preview(media,parent){
 if(!media.url)return;
 const element=document.createElement(media.kind==='audio'?'audio':'img');
 element.src=media.url;
 if(media.kind==='audio'){element.controls=true;element.preload='none';}
 else{element.alt=media.path;element.style.maxWidth='100%';element.style.maxHeight='220px';}
 parent.append(element);
}
async function load(){
 const version=++generation;$('status').textContent='…';$('questions').inert=true;
 try{
  const [data,assetsResponse]=await Promise.all([api('?'+new URLSearchParams({page,q:$('search').value,category:$('category').value,state:$('state').value})),fetch('/api/platform/admin/media')]);
  if(!assetsResponse.ok)throw Error('ບໍ່ສາມາດໂຫຼດຄັງສື່ / 미디어를 불러올 수 없습니다');
  const assets=(await assetsResponse.json()).assets;
  if(version!==generation)return;
  dirty.clear();const selected=$('category').value;
  $('category').replaceChildren(new Option('ທັງໝົດ / 전체',''),...data.categories.map(c=>new Option(data.category_titles[c]||c,c)));$('category').value=selected;
  $('questions').replaceChildren();$('status').textContent=data.total+' / '+data.bank_total;
  $('previous').disabled=page<=1;$('next').disabled=page*20>=data.total;
  for(const item of data.questions){
   const article=text('article','',$('questions')),q=item.question;
   text('h2',item.id,article);text('p',data.category_titles[item.category]||item.category,article);text('p',q.question_text,article);
   for(let i=0;i<q.choices.length;i++)text('p',(i+1)+'. '+(q.choices_are_images?'ຮູບ / 이미지: ':'')+q.choices[i],article);
   if(item.missing_media.length)text('p','ສື່ຍັງຂາດ / 미디어 누락: '+item.missing_media.join(', '),article).className='missing';
   for(const media of item.media){
    const section=text('section','',article),label=text('label',media.path,section),select=document.createElement('select');
    select.append(new Option('ບໍ່ເຊື່ອມ / 연결 안 함',''));
    for(const asset of assets.filter(a=>a.kind===media.kind))select.append(new Option(asset.title+(asset.published?'':' · ຮ່າງ / 초안'),asset.id));
    select.value=media.asset||'';label.append(select);preview(media,section);
    if(media.asset&&!media.published)text('p','ສື່ຍັງບໍ່ເຜີຍແຜ່ / 미디어가 아직 공개되지 않았습니다',section);
    const link=text('button','ເຊື່ອມສື່ / 미디어 연결',section),note=text('p','',section);note.setAttribute('role','status');
    link.onclick=async()=>{
     if(dirty.size){note.textContent='ບັນທຶກຄຳແກ້ໄຂກ່ອນເຊື່ອມສື່ / 변경 내용을 먼저 저장하세요';return;}
     link.disabled=true;
     try{await api('/'+encodeURIComponent(item.id)+'/media',{path:media.path,asset:select.value||null,revision:media.revision,question_revision:item.revision});await load();}
     catch(error){note.textContent=error.message;}finally{link.disabled=false;}
    };
   }
   const label=text('label','ຄຳຕອບ / 정답',article),answer=document.createElement('select');
   q.choices.forEach((_,i)=>answer.append(new Option(String(i+1),String(i))));answer.value=String(q.correct_answer_index);label.append(answer);
   const explanationLabel=text('label','ອະທິບາຍ / 해설',article),explanation=document.createElement('textarea');explanation.value=q.explanation_lao||'';explanationLabel.append(explanation);
   const reviewLabel=text('label','',article),review=document.createElement('input');review.type='checkbox';review.checked=item.reviewed;review.disabled=!!item.missing_media.length;reviewLabel.append(review);reviewLabel.append(document.createTextNode(' ກວດຄຳຖາມ/ຄຳຕອບແລ້ວ / 문항·정답 검토 완료'));
   answer.onchange=explanation.oninput=review.onchange=()=>dirty.add(item.id);
   const save=text('button','ບັນທຶກຮ່າງ / 초안 저장',article),message=text('p','',article);message.setAttribute('role','status');
   save.onclick=async()=>{
    save.disabled=true;answer.disabled=true;explanation.disabled=true;review.disabled=true;
    try{const result=await api('/'+encodeURIComponent(item.id),{revision:item.revision,answer:Number(answer.value),explanation:explanation.value,reviewed:review.checked});item.revision=result.revision;item.published=false;publish.textContent='ເປີດໃຊ້ / 공개';dirty.delete(item.id);message.textContent='✓ ບັນທຶກແລ້ວ / 저장 완료';}
    catch(error){message.textContent=error.message;}finally{save.disabled=false;answer.disabled=false;explanation.disabled=false;review.disabled=!!item.missing_media.length;}
   };
   const publish=text('button',item.published?'ປິດໃຊ້ / 비공개':'ເປີດໃຊ້ / 공개',article);
   publish.onclick=async()=>{
    if(!savedFirst())return;publish.disabled=true;
    try{await api('/'+encodeURIComponent(item.id)+'/publication',{revision:item.revision,published:!item.published});await load();}
    catch(error){message.textContent=error.message;}finally{publish.disabled=false;}
   };
  }
 }catch(error){if(version===generation)$('status').textContent=error.message;}
 finally{if(version===generation)$('questions').inert=false;}
}
function savedFirst(){if(!dirty.size)return true;$('status').textContent='ບັນທຶກຄຳແກ້ໄຂກ່ອນ / 변경 내용을 먼저 저장하세요';return false;}
$('filter').onclick=()=>{if(savedFirst()){page=1;load();}};$('previous').onclick=()=>{if(savedFirst()){page--;load();}};$('next').onclick=()=>{if(savedFirst()){page++;load();}};
$('import').onclick=async()=>{if(!savedFirst())return;$('import').disabled=true;try{const result=await api('/import',{});page=1;await load();$('status').textContent+=' · +'+result.added;}catch(error){$('status').textContent=error.message;}finally{$('import').disabled=false;}};
fetch('/api/platform/account').then(r=>r.json()).then(user=>{$('import').hidden=!['admin','superadmin'].includes(user.role);}).catch(()=>{});
load();
