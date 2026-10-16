/* Pointer-based lesson handles; keyboard reordering remains available separately. */
(function(root){
'use strict';
function lessonDrag(handle,options){
 let gesture=null,frame=null,lastTime=null;
 const viewport=options.viewport||(typeof window!=='undefined'?window:null);
 const cancelFrame=()=>{if(frame!==null)viewport.cancelAnimationFrame(frame);frame=null;lastTime=null;};
 function tick(time){
  frame=null;
  if(!gesture||!gesture.moved||!options.canStart()||handle.isConnected===false){clear();return;}
  const height=viewport.innerHeight,edge=Math.min(72,height/4),y=gesture.currentY;
  const direction=y<edge?-Math.min(1,(edge-y)/edge):y>height-edge?Math.min(1,(y-height+edge)/edge):0;
  if(!direction){lastTime=null;return;}
  const elapsed=lastTime===null?16:Math.min(32,Math.max(0,time-lastTime));lastTime=time;
  viewport.scrollBy(0,direction*600*elapsed/1000);
  frame=viewport.requestAnimationFrame(tick);
 }
 const schedule=()=>{if(viewport&&frame===null)frame=viewport.requestAnimationFrame(tick);};
 const clear=()=>{const previous=gesture;gesture=null;cancelFrame();if(viewport)viewport.removeEventListener('blur',clear);handle.removeAttribute('data-dragging');if(previous&&handle.hasPointerCapture(previous.pointerId))handle.releasePointerCapture(previous.pointerId);};
 handle.addEventListener('pointerdown',event=>{
  if(event.button!==0||gesture)return;
  if(!options.canStart()){options.onReject();return;}
  event.preventDefault();gesture={pointerId:event.pointerId,x:event.clientX,y:event.clientY,currentY:event.clientY,moved:false};
  handle.setAttribute('data-dragging','true');handle.setPointerCapture(event.pointerId);if(viewport)viewport.addEventListener('blur',clear);
 });
 handle.addEventListener('pointermove',event=>{
  if(!gesture||event.pointerId!==gesture.pointerId)return;
  event.preventDefault();gesture.currentY=event.clientY;if(Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)>=6)gesture.moved=true;if(gesture.moved)schedule();
 });
 handle.addEventListener('pointerup',event=>{
  if(!gesture||event.pointerId!==gesture.pointerId)return;
  const moved=gesture.moved,target=moved?options.targetAt(event.clientX,event.clientY):null;
  clear();if(moved&&target&&target!==options.id&&options.canStart())options.onMove(options.id,target);
 });
 handle.addEventListener('pointercancel',event=>{if(gesture?.pointerId===event.pointerId)clear();});
 handle.addEventListener('lostpointercapture',event=>{if(gesture?.pointerId===event.pointerId)clear();});
 // A window interruption must not leave a captured gesture scrolling the editor.
 return clear;
}
if(typeof module!=='undefined'&&module.exports)module.exports=lessonDrag;else root.lessonDrag=lessonDrag;
})(typeof window==='undefined'?globalThis:window);
