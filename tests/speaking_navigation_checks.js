'use strict';
const assert=require('node:assert/strict'),attach=require('../static/speaking-navigation.js');
class Control extends EventTarget{constructor(){super();this.disabled=false;}}
const select=new Control(),previous=new Control(),next=new Control();
select.options=[{value:''},{value:'one'},{value:'private',disabled:true},{value:'two'}];select.value='';
let busy=false,changes=[];
select.addEventListener('change',()=>changes.push(select.value));
const refresh=attach(select,previous,next,()=>busy);
assert(previous.disabled);assert(!next.disabled);next.dispatchEvent(new Event('click'));assert.equal(select.value,'one');assert(previous.disabled);assert(!next.disabled);
next.dispatchEvent(new Event('click'));assert.equal(select.value,'two');assert(next.disabled);assert(!previous.disabled);
next.dispatchEvent(new Event('click'));assert.deepEqual(changes,['one','two']);
busy=true;refresh();assert(previous.disabled&&next.disabled);previous.dispatchEvent(new Event('click'));assert.equal(select.value,'two');
busy=false;refresh();previous.dispatchEvent(new Event('click'));assert.equal(select.value,'one');assert.deepEqual(changes,['one','two','one']);
select.options=[];select.value='';refresh();assert(previous.disabled&&next.disabled);next.dispatchEvent(new Event('click'));assert.equal(changes.length,3);
select.options=[{value:''},{value:'filtered'}];refresh();assert(!next.disabled);next.dispatchEvent(new Event('click'));assert.equal(select.value,'filtered');assert(previous.disabled&&next.disabled);
console.log('Speaking navigation bounds, busy-state guard, visible choices and change cleanup hooks passed');
