'use strict';
const $=id=>document.getElementById(id);
async function api(url,body){
 const token=body?(await(await fetch('/api/csrf')).json()).token:'';
 const r=await fetch(url,{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:body?JSON.stringify(body):undefined});
 const d=await r.json();
 if(!r.ok){const error=Error(d.error||'ດຳເນີນການບໍ່ສຳເລັດ / 요청 실패');error.status=r.status;throw error;}
 return d;
}
const msg=e=>$('message').textContent=e.message||e;
function clearRegistration(){
 for(const id of ['registerName','registerUsername','registerPassword','registerConfirm'])$(id).value='';
 $('registration').open=false;$('registerStatus').textContent='';
}
function showSignIn(){
 $('profile').hidden=true;$('signIn').hidden=false;$('staffLink').hidden=true;
 $('username').textContent='';$('name').value='';$('current').value='';$('password').value='';
 clearRegistration();$('legacyPassword').value='';$('legacySignInStatus').textContent='';$('legacySignIn').open=false;
}
async function loadProfile(){
 try{
  const d=await api('/api/platform/account');
  $('profile').hidden=false;$('signIn').hidden=true;
  $('staffLink').hidden=!['admin','superadmin','teacher'].includes(d.role);
  const roles={student:'ຜູ້ຮຽນ / 학생',teacher:'ຄູ / 교사',admin:'ແອັດມິນ / 관리자',superadmin:'Super Admin / 최고 관리자'};
  $('username').textContent=d.username+' · '+(roles[d.role]||d.role);
  $('name').value=d.name;$('language').value=d.language;
  clearRegistration();
 }catch(e){showSignIn();if(e.status!==401)throw e;}
}
let resetToken=new URLSearchParams(location.hash.slice(1)).get('reset');
if(resetToken){$('recovery').hidden=false;history.replaceState(null,'','/account');}
else loadProfile().catch(msg);
$('signInForm').onsubmit=async event=>{
 event.preventDefault();$('signInButton').disabled=true;$('registerButton').disabled=true;$('legacySignInButton').disabled=true;msg('ກຳລັງເຂົ້າລະບົບ… / 로그인 중…');
 try{
  await api('/api/login',{username:$('loginUsername').value,password:$('loginPassword').value});
  $('loginPassword').value='';await loadProfile();
  msg($('profile').hidden?'ກະລຸນາເຂົ້າລະບົບອີກຄັ້ງ / 다시 로그인하세요':'✓ ເຂົ້າລະບົບແລ້ວ / 로그인 완료');
 }catch(e){msg(e.status===401?'ຊື່ຜູ້ໃຊ້ ຫຼືລະຫັດບໍ່ຖືກຕ້ອງ / 사용자 이름 또는 비밀번호가 올바르지 않습니다':e);}
 finally{$('signInButton').disabled=false;$('registerButton').disabled=false;$('legacySignInButton').disabled=false;}
};
$('registerForm').onsubmit=async event=>{
 event.preventDefault();
 if($('registerPassword').value!==$('registerConfirm').value){$('registerStatus').textContent='ລະຫັດບໍ່ກົງກັນ / 비밀번호가 일치하지 않습니다';return;}
 $('registerButton').disabled=true;$('signInButton').disabled=true;$('legacySignInButton').disabled=true;
 $('registerStatus').textContent='ກຳລັງສະໝັກ… / 가입 중…';
 try{
  const username=$('registerUsername').value;
  await api('/api/register',{name:$('registerName').value,username,password:$('registerPassword').value});
  clearRegistration();$('loginUsername').value=username.trim().toLowerCase();
  msg('✓ ສະໝັກແລ້ວ. ລໍຖ້າແອັດມິນອະນຸມັດກ່ອນເຂົ້າລະບົບ / 가입 완료. 관리자 승인 후 로그인하세요');
 }catch(e){$('registerStatus').textContent=e.message||e;}
 finally{$('registerButton').disabled=false;$('signInButton').disabled=false;$('legacySignInButton').disabled=false;}
};
$('logout').onclick=async()=>{
 $('logout').disabled=true;
 try{await api('/api/logout',{});showSignIn();$('loginPassword').value='';msg('✓ ອອກຈາກລະບົບແລ້ວ / 로그아웃 완료');}
 catch(e){msg(e);}finally{$('logout').disabled=false;}
};
$('save').onclick=async()=>{try{await api('/api/platform/account',{name:$('name').value,language:$('language').value});localStorage.setItem('thana-language',$('language').value);msg('✓ ບັນທຶກແລ້ວ / 저장 완료');}catch(e){msg(e);}};
$('change').onclick=async()=>{try{await api('/api/platform/account/password',{current:$('current').value,password:$('password').value});location.href='/account';}catch(e){msg(e);}};
$('reset').onclick=async()=>{try{await api('/api/platform/account/recover',{token:resetToken,password:$('resetPassword').value});resetToken=null;location.href='/account';}catch(e){msg(e);}};

let firebaseLoginConfig=null;
if(!resetToken)api('/api/platform/auth/firebase/config').then(config=>{
 firebaseLoginConfig=config;$('legacySignIn').hidden=!config.enabled;
}).catch(()=>{$('legacySignIn').hidden=true;});
$('legacySignInForm').onsubmit=async event=>{
 event.preventDefault();$('legacySignInButton').disabled=true;$('signInButton').disabled=true;$('registerButton').disabled=true;
 $('legacySignInStatus').textContent='ກຳລັງເຂົ້າລະບົບ… / 로그인 중…';
 try{
  if(location.protocol!=='https:')throw Error('ກະລຸນາໃຊ້ HTTPS / HTTPS로 접속하세요');
  await ThanaFirebaseLogin.signIn(firebaseLoginConfig,$('legacyUsername').value,$('legacyPassword').value,body=>api('/api/platform/auth/firebase',body));
  await loadProfile();$('legacySignInStatus').textContent='';$('legacySignIn').open=false;
  msg($('profile').hidden?'ກະລຸນາເຂົ້າລະບົບອີກຄັ້ງ / 다시 로그인하세요':'✓ ເຂົ້າລະບົບແລ້ວ / 로그인 완료');
 }catch(error){$('legacySignInStatus').textContent=error.message;}
 finally{$('legacyPassword').value='';$('legacySignInButton').disabled=false;$('signInButton').disabled=false;$('registerButton').disabled=false;}
};
window.addEventListener('pagehide',()=>{$('legacyPassword').value='';});
