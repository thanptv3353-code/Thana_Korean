"""Adapt the actual public Firebase curriculum into additive review drafts."""
import copy
import hashlib
import json
import random
import re
import time
from pathlib import Path
import quiz_engine

COURSES=('firebase-thana-lessons-v1','firebase-thana-seasonal-v1')
HANGUL=('BASIC_CONSONANTS','DOUBLE_CONSONANTS','BASIC_VOWELS','COMPOUND_VOWELS','BATCHIM_GROUPS','SYLLABLE_EXAMPLES','BATCHIM_EXAMPLES')
GREETINGS=('GREETINGS_HELLO_GOODBYE','GREETINGS_SORRY_THANKS','GREETINGS_NICE_TO_MEET','CLASSROOM_INSTRUCTIONS','CLASSROOM_RESPONSES')


def load_source():
    return json.loads((Path(__file__).resolve().parent/'data/firebase_static_curriculum.json').read_text(encoding='utf-8'))


def prose(value):
    if isinstance(value,str):return value
    if isinstance(value,list):return '\n\n'.join(filter(None,(prose(item) for item in value)))
    if isinstance(value,dict):return '\n'.join(filter(None,(prose(v) for k,v in value.items() if k not in ('id','icon') and not isinstance(v,bool))))
    return str(value) if type(value) in (int,float) else ''


def text_blocks(text):
    # Keep every character, including long grammar/reading material.
    return [{'type':'text','value':text[start:start+19000]} for start in range(0,len(text),19000)]


def exercises(name,items):
    result=[]
    for index,item in enumerate(items,1):
        qid=item.get('id') or f'firebase-{name.lower()}-{index}'
        if '_FILL_' in name:
            before=item.get('sentence',item.get('before',''));after=(' '+item['after']) if item.get('after') else ''
            options=item['choices'];answer=options.index(item['blank'])
            q=dict(id=qid,type='choice',question=before+'____'+after,options=options,answer=answer,explanation=item.get('lao',''))
        else:
            words=item['words'];indices=list(range(len(words)))
            random.Random(int.from_bytes(hashlib.sha256(qid.encode()).digest()[:8],'big')).shuffle(indices)
            if indices==list(range(len(words))):indices.reverse()
            q=dict(id=qid,type='ordering',question=item.get('lao') or 'ຮຽງຄຳ / 순서대로 배열하세요',options=[words[i] for i in indices],answer=[indices.index(i) for i in range(len(words))],explanation=item.get('lao',''))
        q['source']='THANA KOREAN · original Firebase '+name+' · '+str(index)
        if not quiz_engine.valid(q):raise ValueError('Unsupported original exercise; nothing imported')
        result.append(q)
    return result


def build_drafts(source=None):
    source=source or load_source();constants=source['constants'];drafts=[]
    for lesson in constants['DEFAULT_LESSONS']:
        lid=lesson['id'];order=lesson['order']*10+10
        names=HANGUL if lid=='lesson-0' else GREETINGS if lid=='lesson-greetings' else [k for k in constants if re.match('^L'+lid.split('-')[-1]+'_',k) and not k.endswith('_ALL')]
        blocks=text_blocks(lesson.get('subtitle',''));quiz=[]
        for name in names:
            data=constants[name]
            if '_FILL_' in name or name.endswith('_SENTENCE_ORDER'):quiz.extend(exercises(name,data))
            else:blocks.extend(text_blocks(prose(data)))
        if len(blocks)>100:raise ValueError('Original lesson exceeds editor block capacity')
        for start in range(0,max(len(quiz),1),50):
            page=start//50;identity=lid if page==0 else lid+'-practice-'+str(page+1)
            title=lesson['title'] if page==0 else lesson['title']+' · ຝຶກເພີ່ມ / 추가 연습 '+str(page+1)
            content=dict(title=title,module=lesson.get('titleKo',''),order=order+page,blocks=copy.deepcopy(blocks) if page==0 else text_blocks('ຝຶກຕໍ່ຈາກບົດເດີມ / 원래 수업의 추가 연습'),quiz=quiz[start:start+50])
            drafts.append(dict(id=identity,course=COURSES[0],original_lesson=lid,content=content))
    order=0
    for category in constants['SEASONAL_WORKER_CATEGORIES']:
        for lesson in category.get('subLessons',[]):
            order+=1;blocks=text_blocks(prose(lesson))
            if len(blocks)>100:raise ValueError('Original seasonal lesson exceeds editor block capacity')
            drafts.append(dict(id=lesson['id'],course=COURSES[1],original_lesson=lesson['id'],content=dict(title=lesson.get('title_lao',lesson['id']),module=category['title_lao'],order=order,blocks=blocks,quiz=[])))
    if len({d['id'] for d in drafts})!=len(drafts):raise ValueError('Conflicting original lesson identities')
    ids=[q['id'] for d in drafts for q in d['content']['quiz']]
    if len(ids)!=len(set(ids)):raise ValueError('Conflicting exercise identities')
    return drafts


def import_static_drafts(connection,actor,source=None):
    items=build_drafts(source)
    for cid in COURSES:
        course=connection.execute('SELECT language,instruction FROM courses WHERE id=?',(cid,)).fetchone()
        if course and tuple(course)!=('ko','lo'):raise ValueError('Original course ID conflict')
    for item in items:
        old=connection.execute('SELECT course FROM course_lessons WHERE id=?',(item['id'],)).fetchone()
        if old and old[0]!=item['course']:raise ValueError('Original lesson ID conflict')
    for cid,title in zip(COURSES,('ບົດຮຽນເກົ່າ · Firebase · ຮ່າງກວດ','ພາສາສຳລັບແຮງງານ · Firebase · ຮ່າງກວດ')):
        connection.execute('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',(cid,title,'ko','lo','ຮັກສາ ID ເດີມ · ຮ່າງສຳລັບກວດກ່ອນເຜີຍແຜ່ / 원본 ID 유지 · 게시 전 검토용 초안'))
        connection.execute('INSERT OR IGNORE INTO course_rules VALUES (?,?)',(cid,0))
    added=0
    for item in items:
        content=json.dumps(item['content'],ensure_ascii=False);now=time.time()
        cursor=connection.execute('INSERT OR IGNORE INTO course_lessons VALUES (?,?,?,?,?,?)',(item['id'],item['course'],content,None,1,now))
        if cursor.rowcount:
            connection.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(item['id'],1,content,actor,now));added+=1
    return added


def apply_source_overrides(source,collections):
    """Apply only the content fields the old app exposes; keep unmatched data reported."""
    result=copy.deepcopy(source)
    def visit(value,index,predicate):
        if isinstance(value,list):
            for item in value:visit(item,index,predicate)
        elif isinstance(value,dict):
            if isinstance(value.get('id'),str) and predicate(value):index.setdefault(value['id'],[]).append(value)
            for item in value.values():visit(item,index,predicate)
    indexes={k:{} for k in ('thana_lesson_meta','thana_phrases','thana_seasonal_overrides','thana_eps_overrides')}
    visit(result['constants']['DEFAULT_LESSONS'],indexes['thana_lesson_meta'],lambda v: 'sections' in v and 'order' in v)
    main={k:v for k,v in result['constants'].items() if k!='SEASONAL_WORKER_CATEGORIES'}
    visit(main,indexes['thana_phrases'],lambda v:'ko' in v and 'lao' in v)
    # The original app derives these IDs for Hangul rows without an id field.
    for name,category in (('BASIC_CONSONANTS','cons'),('DOUBLE_CONSONANTS','dcons'),('BASIC_VOWELS','vowel'),('COMPOUND_VOWELS','cvowel'),('BATCHIM_EXAMPLES','batchim')):
        for item in result['constants'][name]:
            key='hangul-'+category+'-'+(item.get('hangul') or item['syllable'])
            indexes['thana_phrases'].setdefault(key,[]).append(item)
    visit(result['constants']['SEASONAL_WORKER_CATEGORIES'],indexes['thana_seasonal_overrides'],lambda v:'ko' in v and 'lao' in v)
    visit(result['eps'],indexes['thana_eps_overrides'],lambda v:'question_text' in v and 'choices' in v)
    report={}
    allow={
        'thana_lesson_meta':{'title','subtitle'},
        'thana_phrases':{'ko','lao','phonetic','example','exampleLao','note'},
        'thana_seasonal_overrides':{'ko','lao','phonetic','bossPhonetic','note','icon'},
        'thana_eps_overrides':{'question_text','choices','choices_lao','explanation_lao','correct_answer_index'},
    }
    for collection,keys in allow.items():
        applied=unmatched=unsupported=0
        for document in collections.get(collection,[]):
            targets=indexes[collection].get(document['id'],[])
            if not targets:unmatched+=1;continue
            for key,value in document['data'].items():
                valid=key in keys and (isinstance(value,str) or (key in ('choices','choices_lao') and isinstance(value,list) and all(isinstance(v,str) for v in value)) or (key=='correct_answer_index' and type(value) is int))
                if not valid:unsupported+=1;continue
                for target in targets:target[key]=copy.deepcopy(value)
                applied+=1
        report[collection]=dict(applied_fields=applied,unmatched_documents=unmatched,unsupported_fields=unsupported)
    return result,report
