'use strict';const $=id=>document.getElementById(id),keys=['hero_lo','hero_ko','subtitle_lo','subtitle_ko','help_url'];let revision=null,defaults={};
async function api(body){const token=body?(await(await fetch('/api/csrf')).json()).token:'';const r=await fetch('/api/platform/admin/site-settings',{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:body?JSON.stringify(body):undefined});const d=await r.json();if(!r.ok)throw Error(d.error||'Error');return d;}
function fill(values){for(const key of keys)$(key).value=values[key];}
async function load(){$('save').disabled=true;$('defaults').disabled=true;const d=await api();revision=d.revision;defaults=d.defaults;fill(d.settings);$('save').disabled=false;$('defaults').disabled=false;}
function message(e){$('message').textContent=e.message||e;}
$('reload').onclick=()=>load().then(()=>message('✓ ໂຫຼດແລ້ວ / 불러왔습니다')).catch(message);
$('defaults').onclick=()=>{fill(defaults);message('ກວດຮ່າງ ແລ້ວບັນທຶກ / 내용을 확인하고 저장하세요');};
$('save').onclick=async()=>{if(revision===null)return;$('save').disabled=true;try{const saved=await api({revision,settings:Object.fromEntries(keys.map(key=>[key,$(key).value]))});revision=saved.revision;message('✓ ບັນທຶກແລ້ວ / 저장 완료');}catch(e){message(e);}finally{$('save').disabled=false;}};
$('save').disabled=true;$('defaults').disabled=true;load().catch(message);
