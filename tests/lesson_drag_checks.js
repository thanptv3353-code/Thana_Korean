'use strict';
const assert=require('assert'),attach=require('../static/lesson-drag.js');
function fixture(viewport){const events={},attributes={},capture=new Set(),moves=[];let allowed=true,rejected=0,target='second';const handle={addEventListener:(name,fn)=>events[name]=fn,setAttribute:(k,v)=>attributes[k]=v,removeAttribute:k=>delete attributes[k],setPointerCapture:id=>capture.add(id),hasPointerCapture:id=>capture.has(id),releasePointerCapture:id=>capture.delete(id)};attach(handle,{viewport,id:'first',canStart:()=>allowed,onReject:()=>rejected++,targetAt:()=>target,onMove:(...args)=>moves.push(args)});return {send:(name,overrides={})=>events[name]({button:0,pointerId:1,clientX:10,clientY:10,preventDefault(){},...overrides}),moves,capture,attributes,handle,allow:v=>allowed=v,target:v=>target=v,rejected:()=>rejected};}
let f=fixture();f.send('pointerdown');assert(f.capture.has(1));f.send('pointermove',{clientY:80});f.send('pointerup',{clientY:80});assert.deepEqual(f.moves,[['first','second']]);assert.equal(f.capture.size,0);assert(!f.attributes['data-dragging']);
for(const cancel of ['pointercancel','lostpointercapture']){f=fixture();f.send('pointerdown');f.send('pointermove',{clientY:80});f.send(cancel);f.send('pointerup');assert.deepEqual(f.moves,[]);assert.equal(f.capture.size,0);}
f=fixture();f.send('pointerdown');f.send('pointerup');assert.deepEqual(f.moves,[]);
f=fixture();f.allow(false);f.send('pointerdown');assert.equal(f.rejected(),1);assert.equal(f.capture.size,0);
f=fixture();f.send('pointerdown');f.send('pointermove',{clientY:80});f.allow(false);f.send('pointerup');assert.deepEqual(f.moves,[]);
f=fixture();f.send('pointerdown',{button:2});assert.equal(f.capture.size,0);
f=fixture();f.send('pointerdown');f.send('pointermove',{pointerId:2,clientY:80});f.send('pointerup',{pointerId:2});assert(f.capture.has(1));f.send('pointerup');assert.deepEqual(f.moves,[]);
for(const target of [null,'first']){f=fixture();f.target(target);f.send('pointerdown');f.send('pointermove',{clientY:80});f.send('pointerup');assert.deepEqual(f.moves,[]);}
console.log('Lesson pointer drag checks passed');

// Deterministic animation frames: edge scrolling repeats while stationary,
// stops in the middle, and never survives an ended/interrupted gesture.
function viewportFixture(){let next=0;const frames=new Map(),listeners={},scrolls=[];return {innerHeight:600,scrolls,frames,listeners,requestAnimationFrame:fn=>{frames.set(++next,fn);return next;},cancelAnimationFrame:id=>frames.delete(id),scrollBy:(x,y)=>scrolls.push(y),addEventListener:(name,fn)=>listeners[name]=fn,removeEventListener:name=>delete listeners[name],step(time){const batch=[...frames.values()];frames.clear();batch.forEach(fn=>fn(time));}};}
let v=viewportFixture();f=fixture(v);f.send('pointerdown');f.send('pointermove',{clientY:590});v.step(0);v.step(16);assert.equal(v.scrolls.length,2);assert(v.scrolls.every(n=>n>0&&n<=9.6));f.send('pointermove',{clientY:300});v.step(32);assert.equal(v.frames.size,0);assert.equal(v.scrolls.length,2);f.send('pointermove',{clientY:1});v.step(48);assert(v.scrolls.at(-1)<0);f.send('pointerup',{clientY:1});assert.equal(v.frames.size,0);assert.equal(v.listeners.blur,undefined);assert.equal(f.moves.length,1);
for(const end of ['pointercancel','lostpointercapture','blur','disabled','removed']){v=viewportFixture();f=fixture(v);f.send('pointerdown');f.send('pointermove',{clientY:590});v.step(0);if(end==='blur')v.listeners.blur();else if(end==='disabled')f.allow(false);else if(end==='removed')f.handle.isConnected=false;else f.send(end);v.step(16);assert.equal(v.frames.size,0,end);assert.equal(f.capture.size,0,end);assert.equal(f.moves.length,0,end);assert.equal(v.listeners.blur,undefined,end);}
v=viewportFixture();f=fixture(v);f.send('pointerdown');f.send('pointermove',{pointerId:2,clientY:590});assert.equal(v.frames.size,0);f.send('pointercancel');
console.log('Edge auto-scroll and interruption checks passed');
