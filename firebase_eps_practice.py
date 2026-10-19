"""Original EPS learner practice, isolated from the integer-ID local exam bank."""
import json
from firebase_eps_bank import media_mapping,media_state


def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_eps_publications (question TEXT PRIMARY KEY,revision INTEGER NOT NULL)')
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_eps_question_progress (owner TEXT,qid TEXT,correct INTEGER NOT NULL,attempted INTEGER NOT NULL,free_used INTEGER NOT NULL,PRIMARY KEY(owner,qid))')
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_eps_attempts (id TEXT PRIMARY KEY,owner TEXT NOT NULL,category TEXT NOT NULL,snapshot TEXT NOT NULL,created REAL NOT NULL,finished REAL,result TEXT)')
    connection.execute('CREATE UNIQUE INDEX IF NOT EXISTS firebase_eps_one_active ON firebase_eps_attempts(owner) WHERE finished IS NULL')


def unlimited(connection,user):
    if user['role'] in ('admin','superadmin','teacher'):return True
    return bool(connection.execute("SELECT 1 FROM firebase_account_bindings b JOIN firebase_scope_entitlements s ON s.uid=b.uid WHERE b.username=? AND b.enabled=1 AND s.scope='eps' AND s.granted=1",(user['username'],)).fetchone())


def available(connection,user):
    mapping=media_mapping(connection);items=[]
    for row in connection.execute('SELECT b.id,b.category,b.content FROM firebase_eps_bank b JOIN firebase_eps_publications p ON p.question=b.id AND p.revision=b.revision WHERE b.reviewed=1 ORDER BY b.category,b.id'):
        question=json.loads(row['content']);media=media_state(question,mapping)
        if any(not item['published'] for item in media):continue
        urls={item['path']:item['url'] for item in media}
        item=dict(id=row['id'],category=row['category'],question=question['question_text'],choices=[urls[path] for path in question['choices']] if question.get('choices_are_images') else question['choices'],image_choices=bool(question.get('choices_are_images')),choices_lao=question.get('choices_lao') or [],image_url=urls.get(question.get('image_url')),audio_url=urls.get(question.get('audio_url')),answer=question['correct_answer_index'],explanation=question.get('explanation_lao') or '')
        items.append(item)
    # A published listening pair must be complete before either is offered.
    pair_ids={item['id'] for item in items if item['category']=='listen_story_pair'}
    items=[item for item in items if item['category']!='listen_story_pair' or all(item['id'].rsplit('-',1)[0]+'-'+str(i) in pair_ids for i in (1,2))]
    if not unlimited(connection,user):
        used={r[0] for r in connection.execute('SELECT qid FROM firebase_eps_question_progress WHERE owner=? AND free_used=1',(user['username'],))}
        items=[item for item in items if item['id'] not in used]
    return items


def public_question(item):return {key:value for key,value in item.items() if key not in ('answer','explanation')}


def import_source_progress(connection,owner,data):
    """Merge only original per-question booleans, never fabricate attempt scores."""
    fields=('correct','attempted','freeUsed');maps=[data.get(field,{}) for field in fields]
    if any(not isinstance(value,dict) or any(not isinstance(k,str) or type(v) is not bool for k,v in value.items()) for value in maps):return dict(status='invalid-eps-history',added=0,updated=0,unknown=0)
    known={r[0] for r in connection.execute('SELECT id FROM firebase_eps_bank')};ids=set().union(*(value.keys() for value in maps));added=updated=unknown=0
    for qid in ids:
        if qid not in known:unknown+=1;continue
        values=tuple(int(value.get(qid,False)) for value in maps)
        old=connection.execute('SELECT correct,attempted,free_used FROM firebase_eps_question_progress WHERE owner=? AND qid=?',(owner,qid)).fetchone()
        if old:
            merged=tuple(max(a,b) for a,b in zip(old,values))
            if merged!=tuple(old):connection.execute('UPDATE firebase_eps_question_progress SET correct=?,attempted=?,free_used=? WHERE owner=? AND qid=?',(*merged,owner,qid));updated+=1
        else:connection.execute('INSERT INTO firebase_eps_question_progress VALUES (?,?,?,?,?)',(owner,qid,*values));added+=1
    return dict(status='imported-question-progress' if not unknown else 'partially-mapped-eps-history',added=added,updated=updated,unknown=unknown)
