/* Pointer-based lesson handles; keyboard reordering remains available separately. */
(function(root){
'use strict';
function lessonDrag(handle,options){
 let gesture=null;
 const clear=()=>{const previous=gesture;gesture=null;handle.removeAttribute('data-dragging');if(previous&&handle.hasPointerCapture(previous.pointerId))handle.releasePointerCapture(previous.pointerId);};
 handle.addEventListener('pointerdown',event=>{
  if(event.button!==0||gesture)return;
  if(!options.canStart()){options.onReject();return;}
  event.preventDefault();gesture={pointerId:event.pointerId,x:event.clientX,y:event.clientY,moved:false};
  handle.setAttribute('data-dragging','true');handle.setPointerCapture(event.pointerId);
 });
 handle.addEventListener('pointermove',event=>{
  if(!gesture||event.pointerId!==gesture.pointerId)return;
  event.preventDefault();if(Math.hypot(event.clientX-gesture.x,event.clientY-gesture.y)>=6)gesture.moved=true;
 });
 handle.addEventListener('pointerup',event=>{
  if(!gesture||event.pointerId!==gesture.pointerId)return;
  const moved=gesture.moved,target=moved?options.targetAt(event.clientX,event.clientY):null;
  clear();if(moved&&target&&target!==options.id&&options.canStart())options.onMove(options.id,target);
 });
 handle.addEventListener('pointercancel',event=>{if(gesture?.pointerId===event.pointerId)clear();});
 handle.addEventListener('lostpointercapture',event=>{if(gesture?.pointerId===event.pointerId)clear();});
}
if(typeof module!=='undefined'&&module.exports)module.exports=lessonDrag;else root.lessonDrag=lessonDrag;
})(typeof window==='undefined'?globalThis:window);
