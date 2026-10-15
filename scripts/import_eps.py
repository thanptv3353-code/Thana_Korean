"""Read-only import of public question content; never import accounts or secrets."""
import argparse, hashlib, json, pathlib, shutil
p=argparse.ArgumentParser(); p.add_argument('source'); a=p.parse_args()
src=pathlib.Path(a.source); root=pathlib.Path(__file__).resolve().parents[1]
qs=json.loads((src/'data/questions.json').read_text())
assert len({q['id'] for q in qs})==len(qs), 'Duplicate IDs'
images={p.name:p for p in src.rglob('*.png')}
for q in qs:
 assert isinstance(q['answer'],int) and 1 <= q['answer'] <= len(q['choices_ko']), 'Invalid answer'
 if q.get('image'):
  assert q['image']==pathlib.Path(q['image']).name and q['image'] in images, 'Missing image'
for name in {q['image'] for q in qs if q.get('image')}:
 shutil.copy2(images[name],root/'static/eps-images'/name)
out=root/'data/eps_questions.json'
if out.exists() and json.loads(out.read_text()) != qs: raise SystemExit('Existing import differs; review before replacing')
out.write_text(json.dumps(qs,ensure_ascii=False,indent=2))
(root/'docs/EPS_IMPORT_MANIFEST.json').write_text(json.dumps({'questions':len(qs),'images':len({q['image'] for q in qs if q.get('image')}),'source_sha256':hashlib.sha256((src/'data/questions.json').read_bytes()).hexdigest()},indent=2))
print('Imported',len(qs),'questions without accounts or secrets')
