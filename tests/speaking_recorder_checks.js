'use strict';
const assert=require('node:assert/strict');
const SpeakingRecorder=require('../static/speaking-recorder.js');
class FakeRecorder {
 static instances=[];
 constructor(stream){this.stream=stream;this.state='inactive';this.mimeType='audio/webm';FakeRecorder.instances.push(this);}
 start(){this.state='recording';}
 stop(){this.state='inactive';this.ondataavailable?.({data:new Blob(['synthetic bytes'])});this.onstop?.();}
}
function fixture(getUserMedia){
 const track={stops:0,stop(){this.stops++;}},stream={getTracks:()=>[track]},results=[],states=[],errors=[];let timeout;
 const recorder=new SpeakingRecorder({mediaDevices:{getUserMedia:getUserMedia||(()=>Promise.resolve(stream))},MediaRecorder:FakeRecorder,onResult:r=>results.push(r),onState:s=>states.push(s),onError:e=>errors.push(e),setTimer:(fn,delay)=>{assert.equal(delay,30000);timeout=fn;return 1;},clearTimer:()=>{timeout=null;}});
 return {recorder,track,stream,results,states,errors,timeout:()=>timeout};
}
(async()=>{
 // Recording retains the prompt at start even if caller mutates its object.
 let f=fixture(),prompt={language:'ko-KR',reference:'original'};
 const pending=f.recorder.start(prompt);prompt.reference='changed';await pending;f.recorder.stop();
 let saved=f.results.filter(Boolean);assert.equal(saved.length,1);assert.equal(saved[0].context.reference,'original');assert(Object.isFrozen(saved[0].context));assert.equal(f.track.stops,1);assert.equal(f.recorder.state,'idle');assert.equal(f.timeout(),null);
 // A late permission response after navigation/cancel must release its tracks.
 let resolve;f=fixture(()=>new Promise(r=>resolve=r));const late=f.recorder.start(prompt);f.recorder.cancel();resolve(f.stream);await late;assert.equal(f.track.stops,1);assert.equal(f.results.filter(Boolean).length,0);assert.equal(f.recorder.state,'idle');
 // Cancellation suppresses stop/data events rather than resurrecting old audio.
 f=fixture();await f.recorder.start(prompt);const old=f.recorder.recorder;f.recorder.cancel();old.onstop();assert.equal(f.results.filter(Boolean).length,0);assert.equal(f.track.stops,1);
 // Replacing a recording ignores late events from the previous instance.
 f=fixture();await f.recorder.start({language:'ko-KR',reference:'first'});const first=f.recorder.recorder;await f.recorder.start({language:'lo-LA',reference:'second'});first.ondataavailable({data:new Blob(['stale'])});first.onstop();f.recorder.stop();saved=f.results.filter(Boolean);assert.equal(saved.length,1);assert.equal(saved[0].context.reference,'second');assert.equal(saved[0].context.language,'lo-LA');assert.equal(f.track.stops,2);
 // Auto stop shares the same completion/cleanup path, without real devices.
 f=fixture();await f.recorder.start(prompt);f.timeout()();assert.equal(f.results.filter(Boolean).length,1);assert.equal(f.track.stops,1);
 // Permission and recorder failures restore idle and never retain audio.
 f=fixture(()=>Promise.reject(Error('denied')));await f.recorder.start(prompt);assert.equal(f.errors.length,1);assert.equal(f.recorder.state,'idle');
 f=fixture();await f.recorder.start(prompt);f.recorder.recorder.onerror();assert.equal(f.errors.length,1);assert.equal(f.recorder.state,'idle');assert.equal(f.results.filter(Boolean).length,0);assert.equal(f.track.stops,1);
 console.log('Speaking recorder lifecycle checks passed (synthetic media only)');
})().catch(e=>{console.error(e);process.exitCode=1;});
