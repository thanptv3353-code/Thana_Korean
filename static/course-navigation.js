/* Catalog order and server-provided access flags determine adjacent navigation. */
(function(root){
'use strict';
function courseNeighbors(courses,id){
 const course=courses.find(c=>!c.legacy&&c.lessons.some(l=>l.id===id));
 if(!course)return {course:null,previous:null,next:null};
 const index=course.lessons.findIndex(l=>l.id===id);
 return {course,previous:course.lessons[index-1]||null,next:course.lessons[index+1]||null};
}
if(typeof module!=='undefined'&&module.exports)module.exports=courseNeighbors;else root.courseNeighbors=courseNeighbors;
})(typeof window!=='undefined'?window:globalThis);
