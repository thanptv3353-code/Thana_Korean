/* Shared learning direction; interface language remains a separate preference. */
(function(root){
'use strict';
function studyLanguage(explicit,remembered,interfaceLanguage){return ['ko','lo'].includes(explicit)?explicit:['ko','lo'].includes(remembered)?remembered:interfaceLanguage==='ko'?'lo':'ko';}
function courseUrl(language){return '/courses?language='+studyLanguage(language,null,'lo');}
function practiceUrl(language){return studyLanguage(language,null,'lo')==='lo'?courseUrl('lo'):'/#practice';}
const api={studyLanguage,courseUrl,practiceUrl};
if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
root.ThanaDirection=api;
function apply(explicit,persist){const selected=studyLanguage(explicit,localStorage.getItem('thana-study-language'),localStorage.getItem('thana-language'));if(persist)localStorage.setItem('thana-study-language',selected);const learn=document.getElementById('navLearn'),practice=document.getElementById('navPractice');if(learn)learn.href=courseUrl(selected);if(practice){practice.href=practiceUrl(selected);practice.querySelector('span').textContent=selected==='lo'?'ຝຶກໃນບົດ / 수업 연습':'ຝຶກ EPS / EPS 연습';}}
const explicit=location.pathname==='/courses'?new URLSearchParams(location.search).get('language'):document.getElementById('studyLanguage')?.value;
apply(explicit,location.pathname==='/courses'&&['ko','lo'].includes(explicit));
window.addEventListener('thana-direction',event=>apply(event.detail,false));
})(typeof window==='undefined'?globalThis:window);
