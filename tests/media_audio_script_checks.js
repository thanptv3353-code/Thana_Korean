'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/media.js','utf8').split('let audioScripts=[];')[1];
const elements={};for(const id of ['audioScript','ttsText','ttsTitle','ttsConsent','ttsVoice','audioScriptStatus','useAudioScript'])elements[id]={value:'',checked:false,append(){},disabled:true};
let replace=false;const requests=[];
const context={document:{createElement:()=>({})},$:id=>elements[id],confirm:()=>replace,availableVoices:[{id:'korean',language:'ko-KR'},{id:'lao',language:'lo-LA'}],ttsStatus:async()=>{},api:async path=>{requests.push(path);return{scripts:[{id:'ko',title:'Korean',language:'ko',text:'안녕하세요。',requires_letter_review:false},{id:'lo',title:'Lao',language:'lo',text:'ກ。',requires_letter_review:true}]};}};
vm.runInNewContext('let audioScripts=[];'+source,context);
(async()=>{
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(elements.useAudioScript.disabled,false);
 elements.audioScript.value='lo';elements.ttsConsent.checked=true;elements.useAudioScript.onclick();
 assert.equal(elements.ttsVoice.value,'lao');assert.equal(elements.ttsText.value,'ກ。');assert.equal(elements.ttsConsent.checked,false);
 assert(elements.audioScriptStatus.textContent.includes('문자'));
 elements.audioScript.value='ko';elements.useAudioScript.onclick();assert.equal(elements.ttsText.value,'ກ。');
 replace=true;elements.useAudioScript.onclick();assert.equal(elements.ttsText.value,'안녕하세요。');assert.equal(elements.ttsVoice.value,'korean');
 assert.deepEqual(requests,['/api/platform/admin/curriculum-audio-scripts']);
 console.log('Audio script UI: language voice, overwrite guard, consent reset, no synthesis verified');
})().catch(e=>{console.error(e);process.exitCode=1;});
