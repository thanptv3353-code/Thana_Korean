"""Export the complete authored text and answer key for owner review."""
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from curriculum_pack import lessons
import quiz_engine
lines=['# THANA KOREAN · ຮ່າງຫຼັກສູດ / 교육과정 검토 원고','',
 '48 lessons · 12 modules · 206 exercises (14 preserved original questions).',
 'Owner-review draft; no audio, independent teacher approval or official level certification is claimed.',
 '','## Design and sources','',
 'The sequence and new explanations/dialogues/exercises are authored for THANA KOREAN. The Korean course expands the existing lesson themes into smaller steps. Original files/IDs are preserved. Selected old questions are copied with the same IDs and answers, and their lesson references are listed below. Lao greetings, names, numbers and everyday nouns extend the existing starter and practice material.',
 '',
 '- [Online King Sejong Institute curriculum](https://www.iksi.or.kr/lms/main/curriculum.do): introductory/beginner progression reference; no textbook lessons or recordings copied.',
 '- [NIU SEAsite Lao grammar 1](https://seasite.niu.edu/lao/LaoLanguage/grammar_notes/grammar1.htm) and [grammar 2](https://seasite.niu.edu/lao/LaoLanguage/grammar_notes/grammar2.htm): cross-checks for question/negative particles and basic structures; explanations/examples here are newly authored.',
 '- [Lao alphabet](https://laolessons.com/lao-alphabet-chart/) and [Lao number reference](https://www.omniglot.com/language/numbers/lao.htm): character/number checks; no third-party audio, images or book pages imported.',
 '', 'References accessed 2026-10-17. These references do not constitute endorsement or independent review. “Best” is treated as clear, ordered, relevant existing material rather than a claim of a globally best curriculum.',
 '', '## Review and continuation','',
 'Review spelling, naturalness, explanations and accepted answers; add reviewed audio separately; preview each exercise and publish each lesson explicitly when ready. Intermediate/advanced Korean, full TOPIK and the full listening corpus remain separate expansions; these 48 lessons cover foundations only. Existing EPS practice/mock banks remain separate and retain their question IDs.',
 '']
for language in ('ko','lo'):
 items=lessons(language);lines+=['## '+('ພາສາເກົາຫຼີສຳລັບຄົນລາວ' if language=='ko' else '한국인을 위한 라오어'),'']
 for item in items:
  d=item['content'];lines+=['### '+d['title'],'',d['module'],'','**'+d['objectives']+'**','']
  for b in d['blocks']:lines +=[b['value'],'']
  lines+=['#### ແບບຝຶກ ແລະຄຳຕອບ / 문제와 정답','']
  for i,q in enumerate(d['quiz'],1):
   lines +=[str(i)+'. '+q['question'],'']
   if q.get('type')=='matching':lines +=['   '+p['left']+' → '+p['right'] for p in q['pairs']]
   elif q.get('type')=='blank':lines +=['   '+ ' / '.join(q['accepted'])]
   else:
    lines+=['   '+str(n+1)+') '+o for n,o in enumerate(q['options'])]
    given=q['answer'];detail=quiz_engine.grade(q,given);lines+=['','   **'+detail['solution']+'**']
   lines+=['']
  for reference in item['references']:lines+=['Preserved source: '+reference['question']+' · /learn?lesson='+reference['lesson'],'']
(root/'docs/CURRICULUM_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
print('Wrote full 48-lesson review manuscript to docs/CURRICULUM_REVIEW.md')
