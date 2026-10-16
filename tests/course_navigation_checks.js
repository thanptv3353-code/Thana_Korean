'use strict';
const assert=require('node:assert/strict'),neighbors=require('../static/course-navigation.js');
const legacy={id:'legacy',legacy:true,lessons:[{id:'a'}]};
const course={id:'ko-course',language:'ko',lessons:[{id:'a',unlocked:true},{id:'b',unlocked:false},{id:'c',unlocked:true}]};
const other={id:'other',language:'lo',lessons:[{id:'d'}]};
let nav=neighbors([legacy,course,other],'a');assert.equal(nav.course.id,'ko-course');assert.equal(nav.previous,null);assert.equal(nav.next.id,'b');assert.equal(nav.next.unlocked,false);
nav=neighbors([course,other],'b');assert.equal(nav.previous.id,'a');assert.equal(nav.next.id,'c');
nav=neighbors([course,other],'c');assert.equal(nav.previous.id,'b');assert.equal(nav.next,null); // Never crosses into the other course.
nav=neighbors([course,other],'d');assert.equal(nav.course.language,'lo');assert.equal(nav.previous,null);assert.equal(nav.next,null);
assert.deepEqual(neighbors([legacy],'a'),{course:null,previous:null,next:null});
assert.deepEqual(neighbors([course],'missing'),{course:null,previous:null,next:null});
console.log('Course navigation checks passed');
