'use strict';
const $=id=>document.getElementById(id);
const labels={unverified:'ຍັງບໍ່ກວດຄຳຕອບ / 정답 미검토',stem_lo:'ຂາດຄຳແປຄຳຖາມ / 질문 라오어 번역 없음',passage_lo:'ຂາດຄຳແປບົດອ່ານ / 지문 라오어 번역 없음',choices_lo:'ຂາດຄຳແປຕົວເລືອກ / 선택지 라오어 번역 없음',audio_ko:'ຂາດສຽງເກົາຫຼີ / 한국어 음성 없음',audio_lo:'ຂາດສຽງລາວ / 라오어 음성 없음'};
let page=1,pages=1,controller;
async function load(target=1){
 if(controller)controller.abort();controller=new AbortController();
 $('status').textContent='ກຳລັງກວດ / 확인 중…';$('prev').disabled=true;$('next').disabled=true;
 try{
  const params=new URLSearchParams({kind:$('kind').value,q:$('query').value,page:String(target)});
  const response=await fetch('/api/platform/admin/content-readiness?'+params,{signal:controller.signal});
  const d=await response.json();if(!response.ok)throw Error(d.error||'Error');
  page=d.page;pages=d.pages;$('counts').textContent=`EPS: ${d.counts.eps} · ຄຳສັບ / 단어: ${d.counts.vocabulary}`;
  $('items').replaceChildren();
  for(const item of d.items){
   const card=document.createElement('article'),title=document.createElement('h3'),list=document.createElement('ul'),link=document.createElement('a');
   title.textContent=`${item.kind==='eps'?'EPS':'ຄຳສັບ / 단어'} #${item.id} · ${item.title}`;
   for(const code of item.issues){const li=document.createElement('li');li.textContent=labels[code]||code;list.append(li);}
   link.href=item.url;link.textContent='ເປີດແກ້ໄຂ / 수정';card.append(title,list,link);$('items').append(card);
  }
  $('status').textContent=d.total?`${d.total} ລາຍການ / 항목`:'ບໍ່ພົບລາຍການທີ່ກົງກັນ / 해당 항목 없음';
  $('page').textContent=`${page} / ${pages}`;$('prev').disabled=page<=1;$('next').disabled=page>=pages;
 }catch(e){if(e.name!=='AbortError'){$('items').replaceChildren();$('status').textContent=e.message;$('page').textContent='';}}
}
$('filters').onsubmit=e=>{e.preventDefault();load();};$('kind').onchange=()=>load();$('refresh').onclick=()=>load(page);$('prev').onclick=()=>load(page-1);$('next').onclick=()=>load(page+1);load();
