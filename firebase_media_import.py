"""Offline import of checksum-verified original images into a private draft library."""
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import time
from PIL import Image,ImageOps
from firebase_eps_bank import initialize,media_paths


def import_recovered_images(database,candidates,library,apply=False):
    database=Path(database).resolve();candidates=Path(candidates).resolve();library=Path(library).resolve()
    root=Path(__file__).resolve().parent
    originals=Path.home()/'Desktop/EPS-TOPIK BOOK/EPS TOPIK Exam'
    if library==root or root in library.parents or originals==library or originals in library.parents:raise ValueError('Do not write source/original folders')
    if library.parent!=database.parent or not database.is_file():raise ValueError('Select an initialized private runtime and its media directory')
    if not library.is_dir() or not candidates.is_dir() or library==candidates:raise ValueError('Choose existing separate candidate/library directories')
    receipt=candidates/'receipt.json'
    if receipt.stat().st_size>2*1024*1024:raise ValueError('Receipt too large')
    rows=json.loads(receipt.read_text(encoding='utf-8'))
    if not isinstance(rows,list) or len(rows)>2000:raise ValueError('Invalid media receipt')
    connection=sqlite3.connect(database);created=[];total=0
    try:
        connection.execute('BEGIN IMMEDIATE')
        tables={r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'media_assets','firebase_eps_bank'}<=tables:raise ValueError('Initialize the application and original EPS bank first')
        initialize(connection)
        connection.execute('CREATE TABLE IF NOT EXISTS firebase_recovered_images (path TEXT PRIMARY KEY,source_sha TEXT NOT NULL,asset TEXT NOT NULL,content_sha TEXT NOT NULL)')
        references={}
        for qid,content in connection.execute('SELECT id,content FROM firebase_eps_bank'):
            for path in media_paths(json.loads(content)):references.setdefault(path,[]).append(qid)
        prepared=[];seen=set();existing=0
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('path'),str) or row['path'] in seen:raise ValueError('Invalid/duplicate receipt path')
            path=row['path'];seen.add(path)
            if row.get('status')=='missing':continue
            if row.get('status')!='candidate-needs-content-review' or path not in references or not path.startswith('images/'):raise ValueError('Unsupported original image candidate')
            expected=hashlib.sha256(path.encode()).hexdigest()+Path(path).suffix
            if row.get('filename')!=expected:raise ValueError('Unexpected candidate filename')
            file=(candidates/expected).resolve()
            if file.parent!=candidates or file.stat().st_size>16*1024*1024:raise ValueError('Invalid image file')
            raw=file.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            if row.get('sha256')!=digest or type(row.get('bytes')) is not int or row['bytes']!=len(raw):raise ValueError('Candidate checksum/size mismatch')
            old=connection.execute('SELECT source_sha,asset,content_sha FROM firebase_recovered_images WHERE path=?',(path,)).fetchone()
            if old:
                if old[0]!=digest:raise ValueError('Original changed; review required')
                asset=connection.execute('SELECT filename,kind FROM media_assets WHERE id=?',(old[1],)).fetchone()
                if not asset or asset[1]!='image' or Path(asset[0]).name!=asset[0]:raise ValueError('Imported library entry missing')
                saved=library/asset[0]
                if saved.is_symlink() or not saved.is_file() or hashlib.sha256(saved.read_bytes()).hexdigest()!=old[2]:raise ValueError('Imported media changed or missing')
                existing+=1;continue
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG','JPEG') or image.width*image.height>16_000_000:raise ValueError('Image exceeds library constraints')
                image.load();oriented=ImageOps.exif_transpose(image);rgba=oriented.convert('RGBA');white=Image.new('RGBA',rgba.size,'white');white.alpha_composite(rgba);clean=io.BytesIO();white.convert('RGB').save(clean,format='JPEG',quality=90);body=clean.getvalue()
            total+=len(body)
            if len(body)>10*1024*1024 or total>128*1024*1024:raise ValueError('Import byte limit exceeded')
            token=hashlib.sha256((path+'|'+digest).encode()).hexdigest()[:32];asset_id='firebase-'+token;filename=token+'.jpg';content_sha=hashlib.sha256(body).hexdigest()
            if connection.execute('SELECT 1 FROM media_assets WHERE id=? OR filename=?',(asset_id,filename)).fetchone():raise ValueError('Existing asset identity conflict')
            target=library/filename
            if target.exists() and (target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=content_sha):raise ValueError('Existing media file conflict')
            prepared.append((path,digest,asset_id,filename,content_sha,body))
        mapped=preserved=0
        if apply:
            for path,digest,asset_id,filename,content_sha,body in prepared:
                target=library/filename
                if not target.exists():
                    descriptor=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);created.append(target)
                    with os.fdopen(descriptor,'wb') as output:output.write(body)
                connection.execute('INSERT INTO media_assets VALUES (?,?,?,?,0)',(asset_id,'EPS · '+path,filename,'image'))
                connection.execute('INSERT INTO firebase_recovered_images VALUES (?,?,?,?)',(path,digest,asset_id,content_sha))
                if connection.execute('SELECT 1 FROM firebase_eps_media_map WHERE path=?',(path,)).fetchone():preserved+=1;continue
                connection.execute('INSERT INTO firebase_eps_media_map VALUES (?,?,1)',(path,asset_id));mapped+=1
                for qid in references[path]:
                    connection.execute('UPDATE firebase_eps_bank SET reviewed=0,revision=revision+1,updated=? WHERE id=?',(time.time(),qid))
            if connection.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed')
            connection.commit()
        else:connection.rollback()
        return dict(applied=apply,new_draft_images=len(prepared),already_imported=existing,new_mappings=mapped,preserved_existing_mappings=preserved,published=0)
    except BaseException:
        connection.rollback()
        for path in created:path.unlink(missing_ok=True)
        raise
    finally:connection.close()
