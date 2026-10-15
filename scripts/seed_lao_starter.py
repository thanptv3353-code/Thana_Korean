"""Add three authored starter lessons without replacing any existing course."""
import argparse,json,sqlite3,time,os
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--database',default=os.environ.get('THANA_PLATFORM_DB',str(Path(__file__).resolve().parents[1]/'data/platform.sqlite3')));p.add_argument('--publish',action='store_true');args=p.parse_args()
# Initialize schema through application registration, without changing legacy data.
import sys,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]));os.environ['THANA_PLATFORM_DB']=args.database
import app
items=[
 ('greetings','인사하기', ['ສະບາຍດີ — 안녕하세요.','라오어의 기본 인사 표현입니다. 상대를 만났을 때 사용할 수 있습니다.','ສະບາຍດີ를 소리 내어 읽어 보세요. 이 과정에는 아직 원어민 녹음이 포함되어 있지 않습니다.'], {'question':'“안녕하세요”에 해당하는 라오어는 무엇인가요?','options':['ສະບາຍດີ','ຂອບໃຈ','ຂ້ອຍຊື່'],'answer':0,'explanation':'ສະບາຍດີ는 기본 인사 표현입니다.'}),
 ('thanks','감사 표현', ['ຂອບໃຈ — 감사합니다 / 고마워요.','도움을 받거나 감사의 마음을 전할 때 쓰는 기본 표현입니다.','ສະບາຍດີ는 인사, ຂອບໃຈ는 감사 표현입니다. 두 표현을 구분해 보세요.'], {'question':'감사를 표현할 때 사용하는 말은 무엇인가요?','options':['ສະບາຍດີ','ຂອບໃຈ'],'answer':1,'explanation':'ຂອບໃຈ는 감사의 뜻을 전달합니다.'}),
 ('introductions','이름 소개하기', ['ຂ້ອຍຊື່ ... — 제 이름은 ...입니다.','ຂ້ອຍ는 “나/저”, ຊື່는 “이름”을 뜻합니다. 뒤에 자신의 이름을 넣어 소개할 수 있습니다.','예: ຂ້ອຍຊື່ ທານາ — 제 이름은 타나입니다.'], {'question':'자신의 이름을 소개할 때 사용하는 표현은 무엇인가요?','options':['ຂອບໃຈ','ຂ້ອຍຊື່ ...','ສະບາຍດີ'],'answer':1,'explanation':'ຂ້ອຍຊື່ 뒤에 자신의 이름을 넣습니다.'})]
with sqlite3.connect(args.database) as c:
 c.execute('INSERT OR IGNORE INTO courses VALUES (?,?,?,?,?)',('lao-starter','라오어 첫걸음 · 체험 과정','lo','ko','인사, 감사, 이름 소개를 배우는 3개 체험 수업입니다. 원어민 음성 및 확장 과정은 준비 중입니다.'))
 for i,(key,title,blocks,quiz) in enumerate(items,1):
  content=json.dumps({'title':title,'module':'일상 표현','order':i,'blocks':[{'type':'text','value':v} for v in blocks],'quiz':[quiz]},ensure_ascii=False);lid='lao-starter-'+key
  c.execute('INSERT OR IGNORE INTO course_lessons VALUES (?,?,?,?,?,?)',(lid,'lao-starter',content,content if args.publish else None,1,time.time()))
  c.execute('INSERT OR IGNORE INTO lesson_revisions VALUES (?,?,?,?,?)',(lid,1,content,'starter-authoring',time.time()))
print('Starter content added without replacing existing records:',len(items))
