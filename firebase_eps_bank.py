"""Staff review bank preserving original Firebase string IDs and immutable source."""
import json
import re
import time
from firebase_eps_media import inventory


def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS firebase_eps_bank (id TEXT PRIMARY KEY,category TEXT NOT NULL,original TEXT NOT NULL,content TEXT NOT NULL,revision INTEGER NOT NULL,reviewed INTEGER NOT NULL DEFAULT 0,updated REAL NOT NULL)')

    connection.execute('CREATE TABLE IF NOT EXISTS firebase_eps_media_map (path TEXT PRIMARY KEY,asset TEXT,revision INTEGER NOT NULL)')

def import_bank(connection,source):
    manifest=inventory(source);initialize(connection);added=0
    for category in source['eps']:
        for question in category['questions']:
            encoded=json.dumps(question,ensure_ascii=False)
            added+=connection.execute('INSERT OR IGNORE INTO firebase_eps_bank VALUES (?,?,?,?,1,0,?)',(question['id'],category['id'],encoded,encoded,time.time())).rowcount
    return added


def media_paths(question):
    paths=[question[k] for k in ('image_url','audio_url') if question.get(k)]
    if question.get('choices_are_images'):paths+=question['choices']
    return paths



def media_mapping(connection):
    cursor=connection.execute('SELECT p.path,p.asset,p.revision,m.filename,m.kind,m.published,m.title FROM firebase_eps_media_map p LEFT JOIN media_assets m ON m.id=p.asset')
    keys=[column[0] for column in cursor.description]
    return {row[0]:dict(zip(keys,row)) for row in cursor}


def media_state(question,mapping):
    result=[]
    for path in dict.fromkeys(media_paths(question)):
        kind='audio' if path.startswith('audio/') else 'image';row=mapping.get(path,{})
        filename=row.get('filename') or ''
        valid=row.get('kind')==kind and bool(re.fullmatch(r'[0-9a-f]{32}\.'+('(?:mp3|wav)' if kind=='audio' else 'jpg'),filename))
        result.append(dict(path=path,kind=kind,asset=row.get('asset'),revision=row.get('revision',0),
            published=bool(valid and row.get('published')),url='/media/library/'+filename if valid else None))
    return result
