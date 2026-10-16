'use strict';
function lessonWordCard(word){
 const card=document.createElement('section');card.className='lesson-word';
 if(!word){card.textContent='ຄຳສັບນີ້ຍັງບໍ່ເຜີຍແຜ່ / 이 단어는 현재 공개되지 않았습니다';return card;}
 for(const [tag,value] of [['h3',word.ko+' · '+word.lo],['p',word.part_of_speech],['p',word.example_ko],['p',word.example_lo]]){if(value){const e=document.createElement(tag);e.textContent=value;card.append(e);}}
 if(word.image_url){const img=document.createElement('img');img.src=word.image_url;img.alt=word.ko+' · '+word.lo;img.style.maxWidth='100%';img.style.maxHeight='220px';card.append(img);}
 for(const language of ['ko','lo'])if(word['audio_'+language]){const label=document.createElement('p');label.textContent=language==='ko'?'한국어':'ລາວ';const audio=document.createElement('audio');audio.controls=true;audio.preload='none';audio.src=word['audio_'+language];card.append(label,audio);}
 return card;
}
