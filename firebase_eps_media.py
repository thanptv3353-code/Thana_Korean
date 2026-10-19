"""Inventory original EPS media without renumbering questions or losing image choices."""
import re


def inventory(source):
    questions=[];assets={};seen=set()
    def add(path,qid,usage):
        if not isinstance(path,str) or not re.fullmatch(r'(?:images|audio)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|mp3)',path):
            raise ValueError('Unsupported original media path')
        kind='audio' if path.endswith('.mp3') else 'image'
        if (path.startswith('audio/'))!=(kind=='audio'):raise ValueError('Media kind/path mismatch')
        assets.setdefault(path,dict(path=path,kind=kind,uses=[]))['uses'].append(dict(question=qid,usage=usage))
        return path
    for category in source['eps']:
        for question in category['questions']:
            qid=question['id']
            if not isinstance(qid,str) or not qid or qid in seen:raise ValueError('Duplicate or invalid original question ID')
            seen.add(qid);paths=[]
            choices=question['choices'];answer=question['correct_answer_index']
            if not isinstance(choices,list) or not 2<=len(choices)<=10 or type(answer) is not int or not 0<=answer<len(choices):raise ValueError('Invalid original answer')
            for key in ('image_url','audio_url'):
                if question.get(key):paths.append(add(question[key],qid,key))
            if question.get('choices_are_images'):
                for index,path in enumerate(choices):paths.append(add(path,qid,'choice:'+str(index)))
            questions.append(dict(id=qid,category=category['id'],assets=paths,image_choices=bool(question.get('choices_are_images'))))
    return dict(origin='https://thanakorean.com/',questions=questions,assets=list(assets.values()))
