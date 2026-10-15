"""Validation and grading for choice, fill-blank, ordering and matching."""
import copy,unicodedata

def text(value):return unicodedata.normalize('NFC',value).strip().casefold()
def valid(q):
    if not isinstance(q,dict) or not isinstance(q.get('question'),str) or not q['question'].strip() or len(q['question'])>5000:return False
    kind=q.get('type','choice')
    if kind in ('choice','ordering'):
        options=q.get('options')
        if not isinstance(options,list) or not 2<=len(options)<=10 or not all(isinstance(x,str) and x.strip() and len(x)<=1000 for x in options):return False
        answer=q.get('answer')
        if kind=='choice':return type(answer)==int and 0<=answer<len(options)
        return isinstance(answer,list) and all(type(x)==int for x in answer) and sorted(answer)==list(range(len(options)))
    if kind=='blank':return isinstance(q.get('accepted'),list) and 1<=len(q['accepted'])<=10 and all(isinstance(x,str) and x.strip() and len(x)<=1000 for x in q['accepted'])
    if kind=='matching':
        pairs=q.get('pairs')
        return isinstance(pairs,list) and 2<=len(pairs)<=8 and all(isinstance(p,dict) and all(isinstance(p.get(k),str) and p[k].strip() and len(p[k])<=1000 for k in ('left','right')) for p in pairs) and len({p['right'] for p in pairs})==len(pairs)
    return False

def public(q):
    d=copy.deepcopy(q);d.pop('answer',None);d.pop('accepted',None);d.pop('explanation',None)
    if q.get('type')=='matching':d['left']=[p['left'] for p in q['pairs']];d['options']=sorted(p['right'] for p in q['pairs']);d.pop('pairs',None)
    return d

def grade(q,given):
    kind=q.get('type','choice');correct=False
    if kind=='choice':
        if given is not None and (type(given)!=int or not 0<=given<len(q['options'])):raise ValueError('Invalid choice')
        correct=given==q['answer'];solution=q['options'][q['answer']];answer=q['answer']
    elif kind=='blank':
        if given is not None and not isinstance(given,str):raise ValueError('Invalid text answer')
        correct=given is not None and text(given) in {text(a) for a in q['accepted']};solution=q['accepted'][0];answer=solution
    elif kind=='ordering':
        if given is not None and (not isinstance(given,list) or not all(type(x)==int for x in given) or sorted(given)!=list(range(len(q['options'])))):raise ValueError('Invalid word order')
        correct=given==q['answer'];solution=' '.join(q['options'][i] for i in q['answer']);answer=q['answer']
    else:
        expected=[p['right'] for p in q['pairs']]
        if given is not None and (not isinstance(given,list) or len(given)!=len(expected) or any(not isinstance(x,str) or x not in expected for x in given)):raise ValueError('Invalid matching answer')
        correct=given==expected;solution=' / '.join(p['left']+' → '+p['right'] for p in q['pairs']);answer=expected
    return {'correct':correct,'answer':answer,'solution':solution,'explanation':q.get('explanation','')}
