'use strict';
function renderLessonMediaPicker(container,assets,onChoose){
  for(const media of container.querySelectorAll('audio,video'))media.pause();
  container.replaceChildren();
  const query=document.createElement('input');query.type='search';query.placeholder='ຄົ້ນຫາຊື່ສື່ / 미디어 제목 검색';query.setAttribute('aria-label',query.placeholder);
  const kind=document.createElement('select');kind.setAttribute('aria-label','ປະເພດສື່ / 미디어 유형');
  for(const [value,label] of [['','ທັງໝົດ / 전체'],['audio','ສຽງ / 음성'],['image','ຮູບ / 이미지'],['video','ວິດີໂອ / 영상']]){const option=document.createElement('option');option.value=value;option.textContent=label;kind.append(option);}
  const count=document.createElement('p');count.setAttribute('role','status');
  const list=document.createElement('div');container.append(query,kind,count,list);
  function draw(){
    for(const media of list.querySelectorAll('audio,video'))media.pause();
    list.replaceChildren();
    const matches=assets.filter(a=>(!kind.value||a.kind===kind.value)&&a.title.toLocaleLowerCase().includes(query.value.trim().toLocaleLowerCase()));
    count.textContent=matches.length+' · ລາຍການ / 항목';
    if(!matches.length){const empty=document.createElement('p');empty.textContent='ບໍ່ພົບສື່ / 일치하는 미디어가 없습니다';list.append(empty);}
    for(const asset of matches){
      const row=document.createElement('article'),title=document.createElement('p');title.textContent=asset.title+(asset.published?'':' · ຮ່າງ / 비공개');row.append(title);
      if(['audio','video'].includes(asset.kind)){const media=document.createElement(asset.kind);media.controls=true;media.preload='none';media.src=asset.url;media.style.maxWidth='100%';if(asset.kind==='video')media.playsInline=true;row.append(media);}
      const choose=document.createElement('button');choose.type='button';choose.textContent='＋ ເພີ່ມໃນຮ່າງ / 초안에 추가';choose.disabled=!asset.published;
      choose.onclick=()=>{if(asset.published)onChoose(asset);};row.append(choose);list.append(row);
    }
  }
  query.oninput=draw;kind.onchange=draw;draw();
}
