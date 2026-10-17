/* Staff-only unsaved quiz rehearsal; uses the same server grading engine. */
(function(root){
'use strict';
function renderQuizPreview(container,content,grade,isCurrent){
 const doc=container.ownerDocument,form=doc.createElement('form'),notice=doc.createElement('p'),result=doc.createElement('div');
 notice.textContent='ລອງຕອບຮ່າງ — ບໍ່ບັນທຶກຜົນ/XP / 초안 시험 — 결과·XP 저장 안 함';form.append(notice);result.setAttribute('role','status');
 const questionFields=[];
 content.quiz.forEach((q,index)=>{
  const fieldset=doc.createElement('fieldset'),legend=doc.createElement('legend'),fields=[];legend.textContent=(index+1)+'. '+q.question;fieldset.append(legend);
  for(const [key,tag,pattern] of [['image_url','img',/\.(png|jpg|jpeg|webp)$/],['audio_url','audio',/\.(wav|mp3)$/]])if(q[key]&&/^\/media\/library\/[0-9a-f]{32}\./.test(q[key])&&pattern.test(q[key])){const media=doc.createElement(tag);media.src=q[key];if(tag==='img'){media.alt=q.question;media.style.maxWidth='100%';}else{media.controls=true;media.preload='none';}fieldset.append(media);}
  function select(labelText,options){const label=doc.createElement('label'),select=doc.createElement('select');label.textContent=labelText;select.append(new Option('ເລືອກ / 선택',''));for(const [value,text] of options)select.append(new Option(text,value));label.append(select);fieldset.append(label);fields.push(select);}
  const type=q.type||'choice';
  if(type==='choice')for(const [i,text] of q.options.entries()){const label=doc.createElement('label'),input=doc.createElement('input');input.type='radio';input.name='preview-q'+index;input.value=String(i);label.append(input,doc.createTextNode(text));fieldset.append(label);fields.push(input);}
  else if(type==='blank'){const label=doc.createElement('label'),input=doc.createElement('input');label.textContent='ຄຳຕອບ / 답';label.append(input);fieldset.append(label);fields.push(input);}
  else if(type==='ordering')q.options.forEach((_,i)=>select(String(i+1),q.options.map((text,j)=>[String(j),text])));
  else for(const pair of q.pairs)select(pair.left,q.pairs.map(p=>p.right).sort().map(text=>[text,text]));
  questionFields.push({type,fields});form.append(fieldset);
 });
 const submit=doc.createElement('button');submit.type='submit';submit.textContent='ກວດຄຳຕອບທົດລອງ / 초안 답안 확인';submit.disabled=!content.quiz.length;form.append(submit,result);container.append(form);
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(!isCurrent()){result.textContent='ຮ່າງປ່ຽນແລ້ວ — ກົດ Preview ໃໝ່ / 초안이 변경되었습니다. 미리보기를 다시 여세요.';return;}
  const answers={};questionFields.forEach(({type,fields},i)=>{if(type==='choice'){const selected=fields.find(f=>f.checked);if(selected)answers[i]=Number(selected.value);}else if(type==='blank'){if(fields[0].value)answers[i]=fields[0].value;}else if(fields.every(f=>f.value!==''))answers[i]=fields.map(f=>type==='ordering'?Number(f.value):f.value);});
  submit.disabled=true;result.replaceChildren();try{const response=await grade(answers);if(!isCurrent())return;const heading=doc.createElement('h3');heading.textContent=response.score+'% · ທົດລອງເທົ່ານັ້ນ / 초안 시험';result.append(heading);for(const [i,item] of response.detail.entries()){const p=doc.createElement('p');p.textContent=(i+1)+'. '+(item.correct?'✓':'✗')+' '+item.solution+' · '+(item.explanation||'')+(item.source?' · '+item.source:'');result.append(p);}}catch(error){if(isCurrent())result.textContent=error.message;}finally{submit.disabled=false;}
 });
}
root.renderQuizPreview=renderQuizPreview;
})(window);
