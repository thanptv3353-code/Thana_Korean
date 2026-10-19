'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require('node:path').join(__dirname,'../static/account.js'),'utf8');
async function fixture({role='student',hash='',legacyEnabled=false}={}){
 const ids=['legacySignIn','legacyPassword','legacySignInStatus','legacySignInButton','legacySignInForm','legacyUsername','message','profile','signIn','staffLink','username','name','current','password','language','recovery','signInForm','signInButton','loginUsername','loginPassword','logout','save','change','reset','resetPassword','registration','registerForm','registerName','registerUsername','registerPassword','registerConfirm','registerButton','registerStatus'];
 const elements=Object.fromEntries(ids.map(id=>[id,{hidden:true,value:'',textContent:'',disabled:false}]));
 let signed=false,mode='valid';const calls=[],history=[];
 const fetch=async(url,options={})=>{
  calls.push(url);let status=200,data={};
  if(options.method==='POST')assert.equal(options.headers['X-CSRF-Token'],'synthetic-csrf');
  if(url==='/api/csrf')data={token:'synthetic-csrf'};
  else if(url==='/api/platform/auth/firebase/config')data={enabled:legacyEnabled};
  else if(url==='/api/platform/account') {if(signed)data={username:'synthetic',name:'Synthetic learner',role,language:'ko'};else{status=401;data={error:'Login required'};}}
  else if(url==='/api/login'){
   const body=JSON.parse(options.body);assert.equal(body.password,' synthetic existing password ');
   if(mode==='valid'){signed=true;data={ok:true};}else{status=mode==='pending'?403:401;data={error:mode==='pending'?'Pending approval':'Wrong password'};}
  }else if(url==='/api/register'){const body=JSON.parse(options.body);assert.equal(body.password,'synthetic registration password');if(mode==='duplicate'){status=400;data={error:'Duplicate synthetic username'};}else data={ok:true};
  }else if(url==='/api/platform/auth/firebase'){signed=true;data={ok:true};}
  else if(url==='/api/logout'){signed=false;data={ok:true};}
  else throw Error('Unexpected route '+url);
  return {ok:status<400,status,json:async()=>data};
 };
 const events={};
 const context={ThanaFirebaseLogin:{async signIn(config,username,password,exchange){assert(config.enabled);assert.equal(password,'legacy synthetic password');if(mode==='wrong')throw Error('Generic legacy failure');await exchange({id_token:'synthetic-token'});}},window:{addEventListener(name,handler){events[name]=handler;}},document:{getElementById:id=>elements[id]},fetch,URLSearchParams,location:{hash,protocol:'https:'},history:{replaceState:(...args)=>history.push(args)},localStorage:{setItem(){}}};
 vm.runInNewContext(source,context);for(let i=0;i<4;i++)await new Promise(setImmediate);
 return {elements,calls,history,events,setMode:value=>mode=value};
}
(async()=>{
 for(const role of ['student','teacher','admin','superadmin']){
  const f=await fixture({role}),e=f.elements;
  assert.equal(e.signIn.hidden,false);assert.equal(e.profile.hidden,true);assert.equal(e.message.textContent,'');
  e.loginUsername.value='synthetic';e.loginPassword.value=' synthetic existing password ';
  let prevented=false;await e.signInForm.onsubmit({preventDefault(){prevented=true;}});
  assert(prevented);assert.equal(e.profile.hidden,false);assert.equal(e.signIn.hidden,true);
  assert.equal(e.loginPassword.value,'');assert.equal(e.language.value,'ko');assert.equal(e.staffLink.hidden,role==='student');
  e.current.value='private old value';e.password.value='private unsaved value';
  await e.logout.onclick();assert.equal(e.profile.hidden,true);assert.equal(e.signIn.hidden,false);assert.equal(e.staffLink.hidden,true);
  assert.equal(e.current.value,'');assert.equal(e.password.value,'');assert.equal(e.name.value,'');
 }
 for(const mode of ['wrong','pending']){
  const f=await fixture(),e=f.elements;f.setMode(mode);e.loginPassword.value=' synthetic existing password ';
  await e.signInForm.onsubmit({preventDefault(){}});assert.equal(e.profile.hidden,true);assert.equal(e.signInButton.disabled,false);
  assert(e.message.textContent.includes(mode==='pending'?'Pending approval':'비밀번호'));
 }
 const signup=await fixture(),r=signup.elements;r.registration.open=true;
 r.registerName.value='Synthetic new learner';r.registerUsername.value='new_synthetic';
 r.registerPassword.value='synthetic registration password';r.registerConfirm.value='different';
 await r.registerForm.onsubmit({preventDefault(){}});assert(!signup.calls.includes('/api/register'));assert(r.registerStatus.textContent.includes('일치'));
 r.registerConfirm.value=r.registerPassword.value;signup.setMode('duplicate');
 await r.registerForm.onsubmit({preventDefault(){}});assert(r.registerStatus.textContent.includes('Duplicate'));assert.equal(r.registerButton.disabled,false);assert.equal(r.registerPassword.value,'synthetic registration password');
 signup.setMode('valid');await r.registerForm.onsubmit({preventDefault(){}});
 assert.equal(r.profile.hidden,true);assert.equal(r.signIn.hidden,false);assert.equal(r.loginUsername.value,'new_synthetic');
 assert.equal(r.registerPassword.value,'');assert.equal(r.registerConfirm.value,'');assert.equal(r.registration.open,false);assert(r.message.textContent.includes('승인'));
 const recovery=await fixture({hash:'#reset=synthetic-one-use-token'});
 assert.equal(recovery.elements.recovery.hidden,false);assert.equal(recovery.elements.signIn.hidden,true);
 assert.deepEqual(recovery.calls,[]);assert.equal(recovery.history[0][2],'/account');
 const legacy=await fixture({legacyEnabled:true}),le=legacy.elements;
 assert.equal(le.legacySignIn.hidden,false);le.legacyUsername.value='old_learner';le.legacyPassword.value='legacy synthetic password';
 await le.legacySignInForm.onsubmit({preventDefault(){}});
 assert.equal(le.profile.hidden,false);assert.equal(le.legacyPassword.value,'');assert.equal(le.legacySignInButton.disabled,false);
 const failedLegacy=await fixture({legacyEnabled:true}),fl=failedLegacy.elements;failedLegacy.setMode('wrong');fl.legacyPassword.value='legacy synthetic password';
 await fl.legacySignInForm.onsubmit({preventDefault(){}});assert.equal(fl.legacyPassword.value,'');assert.equal(fl.legacySignInStatus.textContent,'Generic legacy failure');assert.equal(fl.signInButton.disabled,false);
 fl.legacyPassword.value='unsaved';failedLegacy.events.pagehide();assert.equal(fl.legacyPassword.value,'');
 console.log('Account sign-in/profile/logout, current staff roles, failure recovery and reset isolation passed (synthetic only)');
})().catch(error=>{console.error(error);process.exitCode=1;});
