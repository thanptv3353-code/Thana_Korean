"""Convert complete public JS data files to JSON without executing JavaScript."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from static_data_parser import parse_constants


def extract(lesson_source,eps_source):
    lessons=parse_constants(lesson_source);eps=parse_constants(eps_source)
    if not isinstance(lessons.get('DEFAULT_LESSONS'),list) or set(eps)!={'EPS_TOPIK_CATEGORIES'}:
        raise ValueError('Unexpected public curriculum schema')
    return {'source':'https://thanakorean.com/','format':'firebase-static-v1',
        'hashes':{'data.js':hashlib.sha256(lesson_source.encode()).hexdigest(),'eps-topik-data.js':hashlib.sha256(eps_source.encode()).hexdigest()},
        'constants':lessons,'eps':eps['EPS_TOPIK_CATEGORIES']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('lessons',type=Path);p.add_argument('eps',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    bundle=extract(a.lessons.read_text(encoding='utf-8'),a.eps.read_text(encoding='utf-8'))
    with a.output.open('x',encoding='utf-8') as output:json.dump(bundle,output,ensure_ascii=False,indent=1)
    print('Public source converted:',len(bundle['constants']['DEFAULT_LESSONS']),'main lessons;',sum(len(c['questions']) for c in bundle['eps']),'EPS questions')
