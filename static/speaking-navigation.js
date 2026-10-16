/* Move through the currently visible prompt choices; never select placeholders. */
(function(root){
'use strict';
function speakingNavigation(select,previous,next,isBusy){
 function target(delta){const options=[...select.options].filter(o=>o.value&&!o.disabled);const index=options.findIndex(o=>o.value===select.value);return options[index+delta]?.value||null;}
 function refresh(){previous.disabled=isBusy()||!target(-1);next.disabled=isBusy()||!target(1);}
 function move(delta){if(isBusy())return;const value=target(delta);if(!value)return;select.value=value;select.dispatchEvent(new Event('change'));refresh();}
 previous.addEventListener('click',()=>move(-1));next.addEventListener('click',()=>move(1));select.addEventListener('change',refresh);refresh();return refresh;
}
if(typeof module!=='undefined'&&module.exports)module.exports=speakingNavigation;else root.speakingNavigation=speakingNavigation;
})(typeof window==='undefined'?globalThis:window);
