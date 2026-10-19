'use strict';
const assert=require('node:assert/strict');
const {signIn}=require('../static/firebase-login.js');
(async()=>{
 const config={enabled:true,project:'korean-lao-exam',api_key:'AIza'+'x'.repeat(35)};
 const calls=[],exchanges=[];
 const fetcher=async(url,options)=>{
  calls.push({url,options});assert.equal(options.credentials,'omit');assert.equal(options.redirect,'error');assert.equal(options.cache,'no-store');
  if(url.startsWith('https://firestore.googleapis.com/'))return {ok:true,json:async()=>({fields:{authEmail:{stringValue:'synthetic@example.test'}}})};
  assert(url.startsWith('https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?'));
  assert.deepEqual(JSON.parse(options.body),{email:'synthetic@example.test',password:' synthetic password ',returnSecureToken:true});
  return {ok:true,json:async()=>({idToken:'synthetic-id-token',refreshToken:'never-persisted'})};
 };
 await signIn(config,' Learner_1. ',' synthetic password ',async body=>exchanges.push(body),fetcher);
 assert(calls[0].url.includes('/thana_usernames/learner_1.?'));assert.equal(calls.length,2);
 assert.deepEqual(exchanges,[{id_token:'synthetic-id-token'}]);
 for(const bad of [{...config,enabled:false},{...config,project:'foreign'},{...config,api_key:'private-secret'}])await assert.rejects(()=>signIn(bad,'user','pw',()=>{},()=>{throw Error('Must not fetch');}));
 await assert.rejects(()=>signIn(config,'../escape','pw',()=>{},()=>{throw Error('Must not fetch');}));
 let exchanged=false;
 await assert.rejects(()=>signIn(config,'user','pw',()=>{exchanged=true;},async()=>({ok:false,json:async()=>({error:'private-provider-detail'})})),error=>!error.message.includes('private-provider-detail'));
 assert.equal(exchanged,false);
 await assert.rejects(()=>signIn(config,'user',' synthetic password ',()=>{throw Error('binding-private-detail');},fetcher),error=>!error.message.includes('binding-private-detail'));
 console.log('Legacy username mapping, direct fixed-provider authentication, token-only exchange and generic failures passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
