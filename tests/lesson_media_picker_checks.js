'use strict';
const assert=require('assert'),fs=require('fs'),vm=require('vm');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.paused=0;this.style={};}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
 setAttribute(){}
 querySelectorAll(selector){return this.children.flatMap(c=>[...(selector.split(',').includes(c.tag)?[c]:[]),...c.querySelectorAll(selector)]);}
 pause(){this.paused++;}
}
const root=new Element('div'),chosen=[];
const context={document:{createElement:tag=>new Element(tag)}};vm.createContext(context);vm.runInContext(fs.readFileSync('static/lesson-media-picker.js','utf8'),context);
context.renderLessonMediaPicker(root,[{title:'KO · 05 greetings',kind:'audio',published:true,url:'/media/library/a.wav'},{title:'LO · 05 draft',kind:'audio',published:false,url:'/media/library/b.wav'},{title:'Picture',kind:'image',published:true,url:'/media/library/c.png'}],a=>chosen.push(a.url));
const [query,kind,count,list]=root.children;
assert.equal(list.children.length,3);assert.equal(list.children[1].children.at(-1).disabled,true);
list.children[1].children.at(-1).onclick();assert.equal(chosen.length,0);
list.children[0].children.at(-1).onclick();assert.deepEqual(chosen,['/media/library/a.wav']);
const audio=list.querySelectorAll('audio')[0];assert.equal(audio.preload,'none');assert.equal(audio.controls,true);
kind.value='audio';kind.onchange();assert.equal(audio.paused,1);assert.equal(list.children.length,2);
query.value='ko · 05';query.oninput();assert.equal(list.children.length,1);
query.value='nothing';query.oninput();assert.equal(count.textContent.startsWith('0'),true);assert.equal(list.children[0].tag,'p');
console.log('Media picker filtering, private guard, playback cleanup and lazy audio verified');
