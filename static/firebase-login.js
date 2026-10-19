/* Legacy username sign-in. No credential or Firebase token persistence. */
'use strict';
(function(root){
 const failure='ບໍ່ສາມາດເຂົ້າບັນຊີເກົ່າໄດ້. ກວດຊື່/ລະຫັດ ຫຼືຕິດຕໍ່ແອັດມິນ / 기존 계정으로 로그인할 수 없습니다. 계정을 확인하거나 관리자에게 문의하세요';
 async function signIn(config,username,password,exchange,fetcher=fetch){
  if(!config||!config.enabled||config.project!=='korean-lao-exam'||!/^AIza[A-Za-z0-9_-]{35}$/.test(config.api_key))throw Error(failure);
  username=username.trim().toLowerCase();
  if(!/^[a-z0-9_.]{1,100}$/.test(username)||!password)throw Error(failure);
  const options={credentials:'omit',cache:'no-store',redirect:'error',referrerPolicy:'no-referrer'};
  try{
   // Same public username mapping used by the original app, fixed collection only.
   const lookup=await fetcher('https://firestore.googleapis.com/v1/projects/korean-lao-exam/databases/(default)/documents/thana_usernames/'+encodeURIComponent(username)+'?key='+encodeURIComponent(config.api_key),options);
   if(!lookup.ok)throw Error(failure);
   const mapping=await lookup.json();const email=mapping.fields?.authEmail?.stringValue;
   if(typeof email!=='string'||!/^\S+@\S+\.\S+$/.test(email))throw Error(failure);
   const response=await fetcher('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key='+encodeURIComponent(config.api_key),{...options,method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,password,returnSecureToken:true})});
   if(!response.ok)throw Error(failure);
   const result=await response.json();
   if(typeof result.idToken!=='string'||!result.idToken)throw Error(failure);
   await exchange({id_token:result.idToken});
  }catch(error){throw Error(failure);}
 }
 if(typeof module!=='undefined'&&module.exports)module.exports={signIn};
 else root.ThanaFirebaseLogin={signIn};
})(typeof window==='undefined'?{}:window);
