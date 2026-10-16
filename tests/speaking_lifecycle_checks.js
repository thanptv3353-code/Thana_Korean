'use strict';
const assert=require('node:assert/strict'),bind=require('../static/speaking-lifecycle.js'),Recorder=require('../static/speaking-recorder.js');
class FakeRecorder{constructor(){this.state='inactive';this.mimeType='audio/webm';}start(){this.state='recording';}stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['synthetic'])});this.onstop?.();}}
(async()=>{
 for(const interruption of ['thana-view','pagehide','visibilitychange']){
  const page=new EventTarget(),target=new EventTarget();page.hidden=false;
  let released=0,cleanups=0,resolve;const stream={getTracks:()=>[{stop:()=>released++}]},results=[];
  const recorder=new Recorder({mediaDevices:{getUserMedia:()=>new Promise(r=>resolve=r)},MediaRecorder:FakeRecorder,onResult:r=>results.push(r)});
  const unbind=bind(page,target,()=>{cleanups++;recorder.cancel();});
  const pending=recorder.start({language:'lo-LA',reference:'Synthetic'});
  const fire=()=>{const event=new Event(interruption);event.detail='courses';if(interruption==='visibilitychange'){page.hidden=true;page.dispatchEvent(event);}else target.dispatchEvent(event);};
  fire();resolve(stream);await pending;assert.equal(released,1);assert.equal(recorder.state,'idle');assert.equal(results.filter(Boolean).length,0);
  recorder.mediaDevices.getUserMedia=()=>Promise.resolve(stream);await recorder.start({language:'ko-KR',reference:'Synthetic second'});const old=recorder.recorder;fire();old.onstop();assert.equal(recorder.state,'idle');assert.equal(released,2);assert.equal(results.filter(Boolean).length,0);
  const before=cleanups;unbind();fire();assert.equal(cleanups,before);
 }
 const page=new EventTarget(),target=new EventTarget();page.hidden=false;let cleanups=0;bind(page,target,()=>cleanups++);page.dispatchEvent(new Event('visibilitychange'));const speaking=new Event('thana-view');speaking.detail='speaking';target.dispatchEvent(speaking);assert.equal(cleanups,0);
 console.log('Speaking exit/hidden lifecycle releases tracks and suppresses late recordings (synthetic only)');
})().catch(e=>{console.error(e);process.exitCode=1;});
