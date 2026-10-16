'use strict';
const assert=require('assert'),direction=require('../static/learning-direction.js');
assert.equal(direction.studyLanguage('ko','lo','ko'),'ko');assert.equal(direction.studyLanguage('lo','ko','lo'),'lo');
assert.equal(direction.studyLanguage(null,'ko','ko'),'ko');assert.equal(direction.studyLanguage(null,'lo','lo'),'lo');
assert.equal(direction.studyLanguage(null,null,'ko'),'lo');assert.equal(direction.studyLanguage(null,null,'lo'),'ko');
for(const bad of ['javascript:alert(1)','xx','',null]){assert.equal(direction.studyLanguage(bad,'lo','lo'),'lo');assert.equal(direction.studyLanguage(bad,bad,'lo'),'ko');}
assert.equal(direction.courseUrl('lo'),'/courses?language=lo');assert.equal(direction.courseUrl('ko'),'/courses?language=ko');assert.equal(direction.practiceUrl('lo'),'/courses?language=lo');assert.equal(direction.practiceUrl('ko'),'/#practice');
console.log('Learning direction preference and safe navigation checks passed');
