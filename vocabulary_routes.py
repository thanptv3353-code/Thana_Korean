"""Shared vocabulary, reviewed CSV import and audio assets."""
import csv,io,json,os,re,secrets,sqlite3,unicodedata,wave
from flask import jsonify,request,render_template,redirect,send_from_directory

def install_vocabulary(app,legacy,db,owner):
    media=os.path.join(legacy['DATA'],'media');os.makedirs(media,exist_ok=True)
    app.config['MAX_CONTENT_LENGTH']=12*1024*1024
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS vocabulary (id TEXT PRIMARY KEY, ko TEXT, lo TEXT, category TEXT, example_ko TEXT, example_lo TEXT, audio_ko TEXT, audio_lo TEXT, published INTEGER, UNIQUE(ko,lo))')
    def normalize(d):
        if not isinstance(d,dict):return None
        fields={k:unicodedata.normalize('NFC',d.get(k,'').strip()) for k in ('ko','lo','category','example_ko','example_lo') if isinstance(d.get(k,''),str)}
        if len(fields)!=5 or not fields['ko'] or not fields['lo'] or any(len(v)>2000 for v in fields.values()):return None
        return fields
    @app.get('/dictionary')
    def dictionary_page():return render_template('dictionary.html')
    @app.get('/vocabulary-studio')
    def vocabulary_studio():
        u=legacy['current_user']()
        if not u or u.get('role') not in ('admin','teacher') or u.get('status')!='approved':return redirect('/admin')
        return render_template('vocabulary-studio.html')
    @app.get('/api/platform/vocabulary')
    def words():
        term=request.args.get('q','').strip()[:200]
        scope=request.args.get('scope','all')
        if scope not in ('all','saved'):return jsonify(error='Invalid scope'),400
        if scope=='saved' and not owner():return jsonify(error='Login required'),401
        saved_filter=' AND EXISTS(SELECT 1 FROM saved_words s WHERE s.word=vocabulary.id AND s.owner=?)' if scope=='saved' else ''
        params=(term,term)+((owner(),) if scope=='saved' else ())
        with db() as c:rows=c.execute('SELECT * FROM vocabulary WHERE published=1 AND (instr(lower(ko),lower(?))>0 OR instr(lo,?)>0)'+saved_filter+' ORDER BY ko LIMIT 100',params).fetchall()
        return jsonify(words=[dict(r) for r in rows])
    @app.get('/api/platform/admin/vocabulary')
    @legacy['content_required']
    def admin_words():
        with db() as c:rows=c.execute('SELECT * FROM vocabulary ORDER BY ko').fetchall()
        return jsonify(words=[dict(r) for r in rows])
    @app.post('/api/platform/admin/vocabulary')
    @legacy['content_required']
    def save_word():
        d=request.get_json(silent=True) or {};fields=normalize(d);published=d.get('published',False);wid=d.get('id')
        if not fields or type(published)!=bool:return jsonify(error='Invalid vocabulary'),400
        values=[fields[k] for k in ('ko','lo','category','example_ko','example_lo')]
        try:
            with db() as c:
                if wid:
                    if not c.execute('SELECT id FROM vocabulary WHERE id=?',(wid,)).fetchone():return jsonify(error='Not found'),404
                    c.execute('UPDATE vocabulary SET ko=?,lo=?,category=?,example_ko=?,example_lo=?,published=? WHERE id=?',(*values,int(published),wid))
                else:
                    wid=secrets.token_urlsafe(12);c.execute('INSERT INTO vocabulary VALUES (?,?,?,?,?,?,?,?,?)',(wid,*values,'','',int(published)))
        except sqlite3.IntegrityError:return jsonify(error='ມີຄຳສັບນີ້ແລ້ວ / 중복 단어'),409
        return jsonify(id=wid)
    @app.post('/api/platform/admin/vocabulary/import')
    @legacy['content_required']
    def import_words():
        d=request.get_json(silent=True) or {};raw=d.get('csv');commit=d.get('commit',False)
        if not isinstance(raw,str) or len(raw)>2_000_000 or type(commit)!=bool:return jsonify(error='Invalid CSV'),400
        reader=csv.DictReader(io.StringIO(raw.lstrip('\ufeff')))
        if not reader.fieldnames or not {'ko','lo'}<=set(reader.fieldnames):return jsonify(error='CSV requires ko,lo columns'),400
        incoming=[];errors=[];duplicates=[];seen=set()
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            existing={(r['ko'],r['lo']) for r in c.execute('SELECT ko,lo FROM vocabulary')}
            for line,row in enumerate(reader,2):
                if line>1001:return jsonify(error='Maximum 1000 rows'),400
                word=normalize(row)
                if not word:errors.append({'line':line,'error':'Missing/invalid ko or lo'});continue
                key=(word['ko'],word['lo'])
                if key in seen or key in existing:duplicates.append(line);continue
                seen.add(key);incoming.append(word)
            if commit and errors:return jsonify(error='Fix all invalid rows before import',errors=errors),400
            if commit:
                for w in incoming:c.execute('INSERT INTO vocabulary VALUES (?,?,?,?,?,?,?,?,?)',(secrets.token_urlsafe(12),w['ko'],w['lo'],w['category'],w['example_ko'],w['example_lo'],'','',0))
        return jsonify(added=len(incoming) if commit else 0,ready=len(incoming),duplicates=duplicates,errors=errors,preview=incoming[:20],draft=True)
    @app.post('/api/platform/admin/vocabulary/<wid>/audio/<language>')
    @legacy['content_required']
    def upload_word_audio(wid,language):
        if language not in ('lo','ko'):return jsonify(error='Invalid language'),400
        with db() as c:
            if not c.execute('SELECT id FROM vocabulary WHERE id=?',(wid,)).fetchone():return jsonify(error='Not found'),404
        file=request.files.get('file')
        if not file:return jsonify(error='Select audio file'),400
        raw=file.read(10*1024*1024+1)
        if not raw or len(raw)>10*1024*1024:return jsonify(error='Audio limit: 10 MB'),400
        ext=''
        if raw[:4]==b'RIFF' and raw[8:12]==b'WAVE':
            try:
                with wave.open(io.BytesIO(raw),'rb') as w:
                    if w.getnframes()<1 or w.getnchannels()>2:raise ValueError()
                    if len(w.readframes(w.getnframes())) < w.getnframes()*w.getnchannels()*w.getsampwidth():raise ValueError()
                ext='wav'
            except (wave.Error,EOFError,ValueError):pass
        elif raw[:3]==b'ID3' or (len(raw)>2 and raw[0]==255 and raw[1]&224==224):ext='mp3'
        if not ext:return jsonify(error='Upload a valid WAV or MP3'),400
        name=secrets.token_hex(16)+'.'+ext;path=os.path.join(media,name)
        with open(path,'xb') as f:f.write(raw)
        url='/media/audio/'+name
        try:
            with db() as c:c.execute('UPDATE vocabulary SET audio_'+language+'=? WHERE id=?',(url,wid))
        except Exception:
            os.remove(path);raise
        return jsonify(url=url)
    @app.get('/media/audio/<name>')
    def audio_asset(name):
        if not re.fullmatch(r'[0-9a-f]{32}\.(wav|mp3)',name):return jsonify(error='Not found'),404
        url='/media/audio/'+name
        with db() as c:visible=c.execute('SELECT 1 FROM vocabulary WHERE published=1 AND (audio_ko=? OR audio_lo=?)',(url,url)).fetchone()
        u=legacy['current_user']()
        admin=u and u.get('role') in ('admin','teacher') and u.get('status')=='approved'
        if not visible and not admin:return jsonify(error='Not found'),404
        r=send_from_directory(media,name,mimetype='audio/wav' if name.endswith('.wav') else 'audio/mpeg');r.headers['X-Content-Type-Options']='nosniff';return r
