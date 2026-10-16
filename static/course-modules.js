/* Present consecutive module runs without changing the server's lesson order. */
(function(root){
'use strict';
function courseModules(course){
 const groups=[];
 for(const lesson of course.lessons){
  const name=course.legacy?'':(lesson.module||'').trim();
  let group=groups[groups.length-1];
  if(!group||group.name!==name){group={name,lessons:[]};groups.push(group);}
  group.lessons.push(lesson);
 }
 return groups;
}
if(typeof module!=='undefined'&&module.exports)module.exports=courseModules;else root.courseModules=courseModules;
})(typeof window==='undefined'?globalThis:window);
