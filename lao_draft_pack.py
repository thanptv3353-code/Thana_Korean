"""Original Korean-instruction practice drafts; teacher review required before publish."""
import json
import time

COURSE_ID = 'lao-beginner-review-v1'
NUMBER_SOURCE = 'https://www.omniglot.com/language/numbers/lao.htm'
NUMBERS = [('ໜຶ່ງ','1'),('ສອງ','2'),('ສາມ','3'),('ສີ່','4'),('ຫ້າ','5'),('ຫົກ','6'),('ເຈັດ','7'),('ແປດ','8'),('ເກົ້າ','9'),('ສິບ','10')]
NOTICE = '교사 검토 전 초안입니다. 라오어 표기·한국어 설명·정답을 검토하고 실제 음성을 추가한 뒤 게시하세요. 이 자료에는 원어민 녹음이나 발음 점수가 없습니다.'

def choice(question, options, answer, explanation):
    return dict(type='choice',question=question,options=options,answer=answer,explanation=explanation,difficulty='beginner',category='라오어 기초')

def blank(question, answer):
    return dict(type='blank',question=question,accepted=[answer],explanation='정답 표기: '+answer,difficulty='beginner',category='라오어 기초')

def matching(pairs):
    return dict(type='matching',question='라오어와 뜻을 연결하세요.',pairs=[dict(left=a,right=b) for a,b in pairs],explanation='본문의 단어와 뜻을 다시 확인하세요.',difficulty='beginner',category='라오어 기초')

def lessons():
    rows=[]
    for index,part in enumerate((NUMBERS[:5],NUMBERS[5:]),1):
        qs=[matching(part),blank(part[-1][1]+'에 해당하는 라오어를 입력하세요.',part[-1][0]),choice('다음 중 '+part[0][1]+'은 무엇인가요?',[part[2][0],part[0][0],part[1][0]],1,part[0][0]+' = '+part[0][1])]
        for q in qs:q['source']=NUMBER_SOURCE
        rows.append(('numbers-'+str(index),'숫자 '+('1–5' if index==1 else '6–10'),'숫자', '라오어 숫자 다섯 개를 구분하고 뜻과 연결할 수 있습니다.', ['\n'.join(a+' — '+b for a,b in part),'숫자와 단어를 가린 뒤 뜻을 떠올려 보세요. 이 수업에서는 수량 표현이나 분류사까지 다루지 않습니다.'],qs))
    rows.extend([
      ('school','학교와 책','생활 단어','학교와 책을 뜻하는 두 단어를 구분할 수 있습니다.', ['ໂຮງຮຽນ — 학교\nປຶ້ມ — 책','학교와 책은 서로 다른 단어입니다. 글자를 보고 의미를 떠올린 뒤 직접 입력해 보세요.'],[matching([('ໂຮງຮຽນ','학교'),('ປຶ້ມ','책')]),blank('“책”을 라오어로 입력하세요.','ປຶ້ມ'),choice('“학교”는 무엇인가요?',['ປຶ້ມ','ໂຮງຮຽນ','ນ້ຳ'],1,'ໂຮງຮຽນ은 학교입니다.')]),
      ('work-water','회사와 물','생활 단어','회사와 물에 해당하는 라오어 단어를 구분할 수 있습니다.', ['ບໍລິສັດ — 회사\nນ້ຳ — 물','두 단어를 번갈아 읽고 각각의 뜻을 확인하세요. 한국어 발음 표기만으로 라오어 소리를 판단하지 마세요.'],[matching([('ບໍລິສັດ','회사'),('ນ້ຳ','물')]),blank('“물”을 라오어로 입력하세요.','ນ້ຳ'),choice('“회사”는 무엇인가요?',['ນ້ຳ','ປຶ້ມ','ບໍລິສັດ'],2,'ບໍລິສັດ는 회사입니다.')]),
      ('courtesy-review','인사와 감사 복습','복습','인사 표현과 감사 표현을 상황에 맞게 구분할 수 있습니다.', ['ສະບາຍດີ — 안녕하세요\nຂອບໃຈ — 감사합니다','상대를 만났을 때의 인사와 도움을 받았을 때의 감사 표현을 구분해 보세요.'],[choice('누군가에게 인사할 때 알맞은 표현을 고르세요.',['ຂອບໃຈ','ສະບາຍດີ','ປຶ້ມ'],1,'ສະບາຍດີ는 기본 인사 표현입니다.'),blank('감사의 표현을 라오어로 입력하세요.','ຂອບໃຈ'),matching([('ສະບາຍດີ','안녕하세요'),('ຂອບໃຈ','감사합니다')])]),
      ('mixed-review','기초 단어 종합 복습','복습','배운 생활 단어와 숫자를 함께 복습할 수 있습니다.', ['배운 단어를 보지 않고 먼저 문제를 풀어 보세요. 틀린 문제는 정답 해설과 앞 수업의 단어 목록을 확인하세요.','이 결과는 이 자료의 연습 결과이며 공인 언어 능력이나 발음 평가가 아닙니다.'],[matching([('ໂຮງຮຽນ','학교'),('ປຶ້ມ','책'),('ນ້ຳ','물'),('ບໍລິສັດ','회사')]),dict(type='ordering',question='숫자가 작은 순서대로 단어를 배열하세요.',options=['ສາມ','ໜຶ່ງ','ສອງ'],answer=[1,2,0],explanation='1 → 2 → 3: ໜຶ່ງ → ສອງ → ສາມ',source=NUMBER_SOURCE,difficulty='beginner',category='숫자'),blank('“감사합니다”를 라오어로 입력하세요.','ຂອບໃຈ')])
    ])
    return [dict(id=COURSE_ID+'-'+key,content=dict(title=title,module=module,order=i,objectives=objective,blocks=[dict(type='text',value=text) for text in [NOTICE]+texts],quiz=quiz)) for i,(key,title,module,objective,texts,quiz) in enumerate(rows,1)]

def import_drafts(connection, actor):
    """Caller owns transaction; conflicts raise so the entire import rolls back."""
    existing=connection.execute('SELECT language,instruction FROM courses WHERE id=?',(COURSE_ID,)).fetchone()
    if existing and tuple(existing)!=('lo','ko'):raise ValueError('Draft course ID conflicts with another language')
    items=lessons()
    for item in items:
        row=connection.execute('SELECT course FROM course_lessons WHERE id=?',(item['id'],)).fetchone()
        if row and row[0]!=COURSE_ID:raise ValueError('Draft lesson ID conflicts with another course')
    connection.execute('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',(COURSE_ID,'라오어 기초 · 교사 검토용 초안','lo','ko','숫자와 생활 단어 연습 6개 초안입니다. 교사 검토 및 실제 음성 추가가 필요합니다.'))
    connection.execute('INSERT OR IGNORE INTO course_levels VALUES (?,?,?)',(COURSE_ID,'beginner',1))
    added=0
    for item in items:
        payload=json.dumps(item['content'],ensure_ascii=False)
        cursor=connection.execute('INSERT OR IGNORE INTO course_lessons VALUES (?,?,?,?,?,?)',(item['id'],COURSE_ID,payload,None,1,time.time()))
        if cursor.rowcount:
            added+=1
            connection.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?,?)',(item['id'],1,payload,actor,time.time()))
    return added
