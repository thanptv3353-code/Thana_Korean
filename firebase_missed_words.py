"""Exact-ID missed-word migration into unpublished vocabulary and private saves."""
import json


def phrase_index(source):
    """Ambiguous IDs stay unresolved; never guess by Korean text or array position."""
    candidates = {}
    def add(identity, item):
        ko, lo = item.get('ko'), item.get('lao')
        if not isinstance(identity, str) or not 1 <= len(identity) <= 100:
            return
        if not isinstance(ko, str) or not isinstance(lo, str) or not ko.strip() or not lo.strip():
            return
        fields = (ko.strip(), lo.strip(), item.get('example',''), item.get('exampleLao',''))
        if not all(isinstance(v, str) and len(v) <= 2000 for v in fields):
            return
        candidates.setdefault(identity, set()).add(fields)
    def visit(value):
        if isinstance(value, list):
            for item in value: visit(item)
        elif isinstance(value, dict):
            add(value.get('id'), value)
            for item in value.values(): visit(item)
    constants = source['constants']
    # Seasonal content has its own override namespace and is not the main review deck.
    visit({k:v for k,v in constants.items() if k != 'SEASONAL_WORKER_CATEGORIES'})
    for name, category in (('BASIC_CONSONANTS','cons'), ('DOUBLE_CONSONANTS','dcons'),
                           ('BASIC_VOWELS','vowel'), ('COMPOUND_VOWELS','cvowel'),
                           ('BATCHIM_EXAMPLES','batchim')):
        for item in constants.get(name, []):
            symbol = item.get('hangul') or item.get('syllable')
            if isinstance(symbol, str): add('hangul-'+category+'-'+symbol, item)
    return {key:next(iter(values)) for key,values in candidates.items() if len(values)==1}


def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS vocabulary (id TEXT PRIMARY KEY,ko TEXT,lo TEXT,category TEXT,example_ko TEXT,example_lo TEXT,audio_ko TEXT,audio_lo TEXT,published INTEGER,UNIQUE(ko,lo))')
    db.execute('CREATE TABLE IF NOT EXISTS saved_words (owner TEXT,word TEXT,PRIMARY KEY(owner,word))')
    db.execute('CREATE TABLE IF NOT EXISTS firebase_vocabulary_sources (word TEXT PRIMARY KEY,source TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS firebase_missed_words (owner TEXT,source_id TEXT,miss_count INTEGER NOT NULL,word TEXT,status TEXT NOT NULL,PRIMARY KEY(owner,source_id))')


def import_missed_words(db, owner, data, index):
    initialize(db)
    words = data.get('words')
    if not isinstance(words, dict):
        return dict(status='invalid-missed-words', added=0, unresolved=0)
    added = unresolved = 0
    for identity, count in words.items():
        if not isinstance(identity, str) or not identity or len(identity)>100 or type(count) is not int or not 1 <= count <= 1_000_000_000:
            unresolved += 1
            continue
        prior = db.execute('SELECT miss_count,word FROM firebase_missed_words WHERE owner=? AND source_id=?', (owner,identity)).fetchone()
        if prior:
            if not prior[1]: unresolved += 1
            # Never re-save a word the learner subsequently removed or alter its schedule.
            if count > prior[0]:
                db.execute('UPDATE firebase_missed_words SET miss_count=? WHERE owner=? AND source_id=?', (count,owner,identity))
            continue
        fields = index.get(identity)
        word = None
        status = 'unmapped-phrase'
        if fields:
            provenance = json.dumps(fields, ensure_ascii=False)
            existing = db.execute('SELECT id FROM vocabulary WHERE id=? OR (ko=? AND lo=?)', (identity,*fields[:2])).fetchall()
            source = db.execute('SELECT source FROM firebase_vocabulary_sources WHERE word=?', (identity,)).fetchone()
            if existing:
                if len(existing)==1 and existing[0][0]==identity and source and source[0]==provenance:
                    word = identity
                else: status = 'vocabulary-conflict'
            elif not source:
                db.execute('INSERT INTO vocabulary VALUES (?,?,?,?,?,?,?,?,0)', (identity,fields[0],fields[1],'Firebase · original review draft',fields[2],fields[3],'',''))
                db.execute('INSERT INTO firebase_vocabulary_sources VALUES (?,?)', (identity,provenance))
                word = identity
            else: status = 'vocabulary-conflict'
            if word:
                db.execute('INSERT OR IGNORE INTO saved_words VALUES (?,?)', (owner,word))
                status = 'imported-private-save'; added += 1
        if not word: unresolved += 1
        db.execute('INSERT INTO firebase_missed_words VALUES (?,?,?,?,?)', (owner,identity,count,word,status))
    return dict(status='imported-missed-words' if not unresolved else 'partial-missed-words-review-required', added=added, unresolved=unresolved)
