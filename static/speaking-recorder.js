/* A recording belongs to one immutable prompt; cancellation ignores late events. */
(function(root){
'use strict';
class SpeakingRecorder {
 constructor({mediaDevices,MediaRecorder,onState=()=>{},onResult=()=>{},onError=()=>{},setTimer=setTimeout,clearTimer=clearTimeout}){Object.assign(this,{mediaDevices,MediaRecorder,onState,onResult,onError,setTimer,clearTimer});this.epoch=0;this.state='idle';this.stream=null;this.recorder=null;this.timer=null;}
 stateChanged(state){this.state=state;this.onState(state);}
 release(){if(this.timer!==null)this.clearTimer(this.timer);this.timer=null;if(this.stream)this.stream.getTracks().forEach(track=>track.stop());this.stream=null;this.recorder=null;}
 cancel(){++this.epoch;const recorder=this.recorder;this.release();if(recorder&&recorder.state!=='inactive'){try{recorder.stop();}catch(e){/* Already stopped. */}}this.onResult(null);this.stateChanged('idle');}
 async start(context){
  this.cancel();const epoch=++this.epoch;const prompt=Object.freeze({language:context.language,reference:context.reference});
  if(!this.mediaDevices?.getUserMedia||!this.MediaRecorder){this.onError(Error('HTTPS / localhost ແລະ browser ທີ່ຮອງຮັບການອັດສຽງ / 녹음을 지원하는 브라우저와 HTTPS 또는 localhost가 필요합니다'));return;}
  this.stateChanged('requesting');
  try{
   const stream=await this.mediaDevices.getUserMedia({audio:true});
   if(epoch!==this.epoch){stream.getTracks().forEach(track=>track.stop());return;}
   this.stream=stream;const recorder=new this.MediaRecorder(stream),chunks=[];this.recorder=recorder;
   recorder.ondataavailable=e=>{if(epoch===this.epoch&&e.data.size)chunks.push(e.data);};
   recorder.onstop=()=>{if(epoch!==this.epoch)return;this.release();this.stateChanged('idle');const blob=new Blob(chunks,{type:recorder.mimeType});if(blob.size)this.onResult({blob,context:prompt});else this.onError(Error('ບໍ່ມີສຽງອັດ / 녹음 데이터가 없습니다'));};
   recorder.onerror=()=>{if(epoch!==this.epoch)return;this.cancel();this.onError(Error('ອັດສຽງບໍ່ສຳເລັດ / 녹음에 실패했습니다'));};
   recorder.start();this.stateChanged('recording');this.timer=this.setTimer(()=>this.stop(),30000);
  }catch(e){if(epoch!==this.epoch)return;this.cancel();this.onError(e);}
 }
 stop(){if(this.state==='requesting'){this.cancel();return;}if(this.recorder?.state==='recording'){this.stateChanged('stopping');try{this.recorder.stop();}catch(e){this.cancel();this.onError(e);}}}
}
if(typeof module!=='undefined'&&module.exports)module.exports=SpeakingRecorder;else root.SpeakingRecorder=SpeakingRecorder;
})(typeof window!=='undefined'?window:globalThis);
