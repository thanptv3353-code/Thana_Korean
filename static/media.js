'use strict';const $=id=>document.getElementById(id);async function api(url,body){const token=body?(await(await fetch('/api/csrf')).json()).token:'';const form=body instanceof FormData;const r=await fetch(url,{method:body?'POST':'GET',headers:form?{'X-CSRF-Token':token}:{'Content-Type':'application/json','X-CSRF-Token':token},body:body?(form?body:JSON.stringify(body)):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Error');return d;}async function load(){$('assets').innerHTML='';for(const a of (await api('/api/platform/admin/media')).assets){const box=document.createElement('article'),h=document.createElement('h3');h.textContent=a.title;const m=document.createElement(a.kind==='image'?'img':a.kind==='video'?'video':'audio');m.src=a.url;if(a.kind==='image'){m.alt=a.title;m.style.maxWidth='100%';}else{m.controls=true;m.preload='metadata';m.style.maxWidth='100%';if(a.kind==='video')m.playsInline=true;}const url=document.createElement('input');url.readOnly=true;url.value=a.url;const b=document.createElement('button');b.textContent=a.published?'ຖອນສາທາລະນະ / 비공개':'ເຜີຍແຜ່ / 공개';b.onclick=async()=>{try{await api('/api/platform/admin/media/'+a.id,{published:!a.published});await load();}catch(e){$('message').textContent=e.message;}};box.append(h,m,url);if(a.generated){const info=document.createElement('p');info.textContent='AI · Microsoft Azure · '+a.generated.voice+' · '+a.generated.text;box.append(info);if(!a.generated.reviewed){b.disabled=true;const review=document.createElement('button');review.textContent='✓ ຟັງກວດສຽງແລ້ວ / 듣고 검토했습니다';review.onclick=async()=>{try{await api('/api/platform/admin/tts/'+a.id+'/review',{reviewed:true});await load();}catch(e){$('message').textContent=e.message;}};box.append(review);}}box.append(b);$('assets').append(box);}}$('upload').onclick=async()=>{try{if(!$('file').files[0])throw Error('Select file');const f=new FormData();f.append('file',$('file').files[0]);f.append('title',$('title').value);await api('/api/platform/admin/media',f);await load();$('message').textContent='✓ ອັບໂຫຼດເປັນຮ່າງ / 초안 업로드';}catch(e){$('message').textContent=e.message;}};load().catch(e=>$('message').textContent=e.message);

let availableVoices=[];
async function ttsStatus(){try{const d=await api('/api/platform/admin/tts/status');$('ttsStatus').textContent=d.enabled?'Microsoft Azure · 1–1000 ຕົວອັກສອນ / 자 · 20 ຄັ້ງ/ມື້ / 회/일':'ຍັງບໍ່ເປີດໃຊ້: ຕ້ອງຕັ້ງຄ່າ Azure TTS / Azure TTS 설정 후 사용할 수 있습니다';availableVoices=d.voices;for(const v of d.voices){const option=document.createElement('option');option.value=v.id;option.textContent=v.language+' · '+v.label;$('ttsVoice').append(option);}$('generateTts').disabled=!d.enabled;}catch(e){$('ttsStatus').textContent=e.message;}}
$('generateTts').onclick=async()=>{if(!$('ttsConsent').checked){$('message').textContent='ກະລຸນາເລືອກການສົ່ງຂໍ້ຄວາມ / 전송에 동의해 주세요';return;}$('generateTts').disabled=true;$('message').textContent='ກຳລັງສ້າງ / 생성 중…';try{const d=await api('/api/platform/admin/tts',{text:$('ttsText').value,voice:$('ttsVoice').value,title:$('ttsTitle').value,consent:true});await load();$('message').textContent=d.cached?'✓ ນຳສຽງເດີມມາໃຊ້ / 기존 음성을 불러왔습니다':'✓ ສ້າງເປັນຮ່າງແລ້ວ. ຟັງກວດກ່ອນເຜີຍແຜ່ / 비공개 초안 생성 완료. 듣고 검토하세요';}catch(e){$('message').textContent=e.message;}finally{$('generateTts').disabled=false;}};


let audioScripts=[];
async function loadAudioScripts(){
  const data=await api('/api/platform/admin/curriculum-audio-scripts');
  audioScripts=data.scripts;
  $('useAudioScript').disabled=false;
  for(const item of audioScripts){const option=document.createElement('option');option.value=item.id;option.textContent=item.language.toUpperCase()+' · '+item.title;$('audioScript').append(option);}
}
$('useAudioScript').onclick=()=>{
  const item=audioScripts.find(item=>item.id===$('audioScript').value);
  if(!item)return;
  if(($('ttsText').value.trim()||$('ttsTitle').value.trim())&&!confirm('ແທນຂໍ້ຄວາມທີ່ກຳລັງແກ້ໄຂບໍ? / 작성 중인 원고를 바꿀까요?'))return;
  $('ttsText').value=item.text;$('ttsTitle').value=(item.language.toUpperCase()+' · '+item.title+' · vocabulary').slice(0,200);
  $('ttsConsent').checked=false;
  const voice=availableVoices.find(v=>v.language.startsWith(item.language));
  $('ttsVoice').value=voice?voice.id:'';
  $('audioScriptStatus').textContent=item.requires_letter_review?'ບົດຕົວອັກສອນ: ຕ້ອງກວດວ່າສຽງອ່ານຮູບອັກສອນ ຫຼືຊື່ອັກສອນໄດ້ຖືກຕ້ອງ. / 문자 수업: 글자 이름과 실제 소리를 구분하여 검토하세요.':'ຮ່າງຄຳສັບພ້ອມກວດ; ຍັງບໍ່ໄດ້ສ້າງສຽງ. / 검토용 단어 원고를 불러왔습니다. 음성은 생성하지 않았습니다.';
};
ttsStatus().then(loadAudioScripts).catch(e=>$('audioScriptStatus').textContent=e.message);
