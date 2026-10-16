/* Hidden/left speaking sessions cannot retain an active microphone or playback. */
(function(root){
'use strict';
function speakingLifecycle(page,windowTarget,cleanup){
 const visibility=()=>{if(page.hidden)cleanup();};
 const view=event=>{if(event.detail!=='speaking')cleanup();};
 windowTarget.addEventListener('thana-view',view);
 windowTarget.addEventListener('pagehide',cleanup);
 page.addEventListener('visibilitychange',visibility);
 return ()=>{windowTarget.removeEventListener('thana-view',view);windowTarget.removeEventListener('pagehide',cleanup);page.removeEventListener('visibilitychange',visibility);};
}
if(typeof module!=='undefined'&&module.exports)module.exports=speakingLifecycle;else root.speakingLifecycle=speakingLifecycle;
})(typeof window==='undefined'?globalThis:window);
