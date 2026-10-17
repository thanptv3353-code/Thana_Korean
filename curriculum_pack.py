"""Authored 48-lesson foundation pack; additive, explicit, draft-only import."""
import copy
import hashlib
import json
import random
import time
from pathlib import Path
from curriculum.korean import ROWS as KOREAN
from curriculum.lao import ROWS as LAO

PACK = 'foundation-v1'
COURSES = {
 'ko': ('thana-ko-foundation-v1','ພາສາເກົາຫຼີພື້ນຖານ · 24 ບົດ (ຮ່າງ)','lo'),
 'lo': ('thana-lo-foundation-v1','라오어 기초 · 24개 수업 (검토용 초안)','ko'),
}
MODULES = {
 'ko': ['01 · ຕົວອັກສອນແລະການອ່ານ','02 · ແນະນຳຕົວແລະຄອບຄົວ','03 · ຕົວເລກແລະເວລາ','04 · ສິ່ງຂອງແລະກິດຈະກຳ','05 · ຊີວິດປະຈຳວັນ','06 · ນຳໃຊ້ແລະທົບທວນ'],
 'lo': ['01 · 문자와 읽기','02 · 인사와 자기소개','03 · 숫자와 시간','04 · 사물과 위치','05 · 동작과 계획','06 · 실생활과 종합 복습'],
}
NOTICES = {
 'ko':'ຮ່າງຂອງ THANA KOREAN ສຳລັບເຈົ້າຂອງກວດ. ຍັງບໍ່ມີສຽງທີ່ກວດແລ້ວ. ຄະແນນແບບຝຶກບໍ່ແມ່ນການປະເມີນສຽງ ຫຼືຜົນສອບທາງການ.',
 'lo':'THANA KOREAN 검토용 원고입니다. 검토된 음성은 아직 포함되어 있지 않습니다. 연습 점수는 발음 평가나 공인 시험 성적이 아닙니다.',
}

def lessons(language):
    if language not in COURSES:raise ValueError('Unknown curriculum language')
    original=json.loads((Path(__file__).resolve().parent/'data/lessons.json').read_text(encoding='utf-8'))
    preserved={q['id']:(l,q) for l in original for q in l.get('quiz',[])}
    result=[];ko=language=='ko';cid=COURSES[language][0]
    for index,row in enumerate(KOREAN if ko else LAO,1):
        title,objective,rule,vocabulary,example,prompt,answer,distractors,written,chunks,legacy_id=row
        lid=f'{cid}-{index:02d}';module=MODULES[language][(index-1)//4]
        pairs=[part.split('|',1) for part in vocabulary.splitlines()]
        seed=int.from_bytes(hashlib.sha256(lid.encode()).digest()[:8],'big');rng=random.Random(seed)
        options=[answer]+list(distractors);rng.shuffle(options)
        blank_prompt,blank_answer=written
        accepted=list(dict.fromkeys([blank_answer,blank_answer.rstrip('.?!。')]))
        shuffled=list(range(len(chunks)));rng.shuffle(shuffled)
        if shuffled==list(range(len(chunks))):shuffled.reverse()
        quiz=[
          dict(type='choice',question=prompt,options=options,answer=options.index(answer),explanation=('ຄຳຕອບ: ' if ko else '정답: ')+answer),
          dict(type='blank',question=blank_prompt,accepted=accepted,explanation=('ຄຳຕອບ: ' if ko else '정답 표기: ')+blank_answer),
          dict(type='matching',question='ຈັບຄູ່ຄຳ/ຮູບກັບຄວາມໝາຍໃນບົດ.' if ko else '본문의 단어·표기와 뜻을 연결하세요.',pairs=[dict(left=a,right=b) for a,b in pairs[:4]],explanation='\n'.join(a+' → '+b for a,b in pairs[:4])),
          dict(type='ordering',question='ຮຽງສ່ວນຕ່າງໆຕາມລຳດັບຕົວຢ່າງໃນບົດ (ໃຊ້ທຸກສ່ວນ).' if ko else '본문 예시의 순서대로 모든 조각을 배열하세요. 띄어쓰기는 학습용 분절입니다.',options=[chunks[i] for i in shuffled],answer=[shuffled.index(i) for i in range(len(chunks))],explanation=' → '.join(chunks)),
        ]
        for position,q in enumerate(quiz,1):q.update(id=f'{lid}-q{position}',difficulty='beginner',category=module,source='THANA KOREAN · foundation-v1 · original authored exercise')
        references=[]
        if legacy_id:
            old_lesson,old_question=preserved[legacy_id];q=copy.deepcopy(old_question)
            q.update(type='choice',difficulty='beginner',category=module,source='THANA KOREAN · preserved lesson '+old_lesson['id']+' · question '+legacy_id,explanation='ຄຳຕອບ: '+q['options'][q['answer']])
            quiz.append(q);references=[dict(lesson=old_lesson['id'],question=legacy_id)]
        practice=('ຝຶກໃຊ້: ປິດຄຳແປ ແລ້ວອ່ານຕົວຢ່າງ; ຂຽນຄຳຕອບຈາກຄວາມຈຳ. ກວດຄຳສັບຄືນກ່ອນເຮັດແບບຝຶກ. ສຳລັບການອອກສຽງ ໃຫ້ຝຶກກັບສຽງທີ່ກວດແລ້ວພາຍຫຼັງ.' if ko else '스스로 연습: 번역을 가리고 예시를 읽은 뒤 기억해서 써 보세요. 틀린 문제는 단어와 설명을 확인하고 다시 풉니다. 실제 발음은 검토된 음성과 함께 별도로 연습하세요.')
        texts=[NOTICES[language],('ຄຳອະທິບາຍ\n' if ko else '핵심 설명\n')+rule,('ຄຳສັບ/ຮູບທີ່ຮຽນ\n' if ko else '단어·표기\n')+'\n'.join(a+' — '+b for a,b in pairs),('ຕົວຢ່າງ\n' if ko else '예시·대화\n')+example+'\n\n'+('ຝຶກຮຽງຕາມແບບ: ' if ko else '배열 연습 예시: ')+' → '.join(chunks),practice]
        result.append(dict(id=lid,course=cid,language=language,references=references,content=dict(title=f'{index:02d} · '+title,module=module,order=index,objectives=objective,blocks=[dict(type='text',value=t) for t in texts],quiz=quiz)))
    return result


def import_drafts(connection, actor, language='all'):
    """Import within caller transaction; never change existing lessons or their IDs."""
    if language not in ('all','ko','lo'):raise ValueError('Unknown curriculum language')
    languages=['ko','lo'] if language=='all' else [language]
    packs={lang:lessons(lang) for lang in languages}
    # Preflight both tracks before any write, including the second course.
    for lang,items in packs.items():
        cid,title,instruction=COURSES[lang]
        row=connection.execute('SELECT language,instruction FROM courses WHERE id=?',(cid,)).fetchone()
        if row and tuple(row)!=(lang,instruction):raise ValueError('Curriculum course ID conflicts with another language')
        for item in items:
            row=connection.execute('SELECT course FROM course_lessons WHERE id=?',(item['id'],)).fetchone()
            if row and row[0]!=cid:raise ValueError('Curriculum lesson ID conflicts with another course')
    counts={}
    for lang,items in packs.items():
        cid,title,instruction=COURSES[lang]
        description='24 ບົດ · 6 ໜ່ວຍ · ຕົວອັກສອນເຖິງການນຳໃຊ້ · ຮ່າງສຳລັບກວດ' if lang=='ko' else '24개 수업 · 6개 단원 · 문자부터 실생활까지 · 검토용 초안'
        connection.execute('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',(cid,title,lang,instruction,description))
        connection.execute('INSERT OR IGNORE INTO course_levels VALUES (?,?,?)',(cid,'beginner',1))
        connection.execute('INSERT OR IGNORE INTO course_rules VALUES (?,?)',(cid,1))
        added=0
        for item in items:
            payload=json.dumps(item['content'],ensure_ascii=False);now=time.time()
            cursor=connection.execute('INSERT OR IGNORE INTO course_lessons VALUES (?,?,?,?,?,?)',(item['id'],cid,payload,None,1,now))
            if cursor.rowcount:
                connection.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(item['id'],1,payload,actor,now));added+=1
        counts[lang]=added
    return counts


def audio_scripts():
    """Recording prompts from the preserved authored pack, never live owner edits."""
    result=[]
    for language,rows in (('ko',KOREAN),('lo',LAO)):
        for index,row in enumerate(rows,1):
            # Only target-language vocabulary, not bilingual explanations/answers.
            words=[line.split('|',1)[0].strip() for line in row[3].splitlines()]
            lid=f'{COURSES[language][0]}-{index:02d}'
            result.append(dict(id=lid+'-vocabulary',lesson=lid,language=language,
                title=f'{index:02d} · '+row[0],text='。\n'.join(words)+'。',
                requires_letter_review=index<=4,reviewed=False))
    return result
