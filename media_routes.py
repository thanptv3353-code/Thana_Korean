"""Reusable image/audio/video assets for structured lessons."""
import io,os,secrets,wave,re
from video_media import clean_video
from PIL import Image,UnidentifiedImageError
from flask import jsonify,request,send_from_directory,render_template,redirect

def install_media(app,legacy,db,owner):
    directory=os.path.join(legacy['DATA'],'media');os.makedirs(directory,exist_ok=True)
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS media_assets (id TEXT PRIMARY KEY, title TEXT, filename TEXT, kind TEXT, published INTEGER)')
    @app.get('/media-studio')
    def media_page():
        u=legacy['current_user']()
        if not u or u.get('status')!='approved' or u.get('role') not in ('admin','superadmin','teacher'):return redirect('/admin')
        return render_template('media-studio.html')
    @app.get('/api/platform/admin/media')
    @legacy['content_required']
    def media_list():
        with db() as c:rows=c.execute('SELECT * FROM media_assets').fetchall()
        with db() as c:generated={r['asset']:dict(r) for r in c.execute('SELECT asset,text,voice,language,reviewed FROM generated_audio')}
        return jsonify(assets=[{**dict(r),'url':'/media/library/'+r['filename'],'generated':generated.get(r['id'])} for r in rows])
    @app.post('/api/platform/admin/media')
    @legacy['content_required']
    def media_upload():
        file=request.files.get('file');title=request.form.get('title','').strip()[:200]
        if not file:return jsonify(error='Select file'),400
        raw=file.read(10*1024*1024+1)
        if not raw or len(raw)>10*1024*1024:return jsonify(error='Maximum 10 MB'),400
        ext='';kind=''
        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG','JPEG') or image.width*image.height>16_000_000:raise ValueError()
                image.load();clean=io.BytesIO();image.convert('RGB').save(clean,format='JPEG',quality=90);raw=clean.getvalue();ext='jpg';kind='image'
        except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError):pass
        if not ext and raw[:4]==b'RIFF' and raw[8:12]==b'WAVE':
            try:
                with wave.open(io.BytesIO(raw),'rb') as w:
                    if w.getnframes()<1 or w.getnchannels()>2:raise ValueError()
                    if len(w.readframes(w.getnframes()))<w.getnframes()*w.getsampwidth()*w.getnchannels():raise ValueError()
                ext='wav';kind='audio'
            except (wave.Error,EOFError,ValueError):pass
        if not ext and (raw[:3]==b'ID3' or (len(raw)>2 and raw[0]==255 and raw[1]&224==224)):ext='mp3';kind='audio'
        if not ext and raw[4:8]==b'ftyp':
            try:raw=clean_video(raw);ext='mp4';kind='video'
            except BlockingIOError:return jsonify(error='Another video is being checked; retry shortly'),429
            except ValueError as e:return jsonify(error=str(e)),400
        if not ext:return jsonify(error='PNG/JPEG/MP3/WAV or H.264 MP4 only'),400
        name=secrets.token_hex(16)+'.'+ext;mid=secrets.token_urlsafe(12)
        with open(os.path.join(directory,name),'xb') as f:f.write(raw)
        with db() as c:c.execute('INSERT INTO media_assets VALUES (?,?,?,?,0)',(mid,title or 'Media',name,kind))
        return jsonify(id=mid,url='/media/library/'+name),201
    @app.post('/api/platform/admin/media/<mid>')
    @legacy['content_required']
    def media_publish(mid):
        published=(request.get_json(silent=True) or {}).get('published')
        if type(published)!=bool:return jsonify(error='Invalid state'),400
        with db() as c:
            if not c.execute('SELECT id FROM media_assets WHERE id=?',(mid,)).fetchone():return jsonify(error='Not found'),404
            generated=c.execute('SELECT reviewed FROM generated_audio WHERE asset=?',(mid,)).fetchone()
            if published and generated and not generated['reviewed']:return jsonify(error='Listen and review AI audio before publishing'),400
            c.execute('UPDATE media_assets SET published=? WHERE id=?',(int(published),mid))
        return jsonify(ok=True)
    @app.get('/media/library/<name>')
    def library_file(name):
        if not re.fullmatch(r'[0-9a-f]{32}\.(jpg|wav|mp3|mp4)',name):return jsonify(error='Not found'),404
        with db() as c:r=c.execute('SELECT published FROM media_assets WHERE filename=?',(name,)).fetchone()
        u=legacy['current_user']();staff=u and u.get('status')=='approved' and u.get('role') in ('admin','superadmin','teacher')
        if not r or (not r['published'] and not staff):return jsonify(error='Not found'),404
        mime={'jpg':'image/jpeg','wav':'audio/wav','mp3':'audio/mpeg','mp4':'video/mp4'}[name.rsplit('.',1)[1]]
        response=send_from_directory(directory,name,mimetype=mime);response.headers['X-Content-Type-Options']='nosniff';return response
