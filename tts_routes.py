"""Staff-only, opt-in Azure TTS. Generated audio stays private until reviewed."""
import hashlib,io,json,os,re,secrets,time,urllib.request,urllib.error,wave
from xml.sax.saxutils import escape
from flask import jsonify,request
VOICES={'ko-KR-SunHiNeural':('ko-KR','SunHi · 여성'), 'ko-KR-InJoonNeural':('ko-KR','InJoon · 남성'), 'lo-LA-KeomanyNeural':('lo-LA','Keomany · ຍິງ'), 'lo-LA-ChanthavongNeural':('lo-LA','Chanthavong · ຊາຍ')}
def install_tts(app,legacy,db,owner):
    with db() as c:
        c.execute('CREATE TABLE IF NOT EXISTS generated_audio (asset TEXT PRIMARY KEY, fingerprint TEXT UNIQUE, text TEXT, voice TEXT, language TEXT, created REAL, reviewed INTEGER DEFAULT 0)')
        c.execute('CREATE TABLE IF NOT EXISTS tts_usage (owner TEXT, day TEXT, count INTEGER, PRIMARY KEY(owner,day))')
    def enabled():return os.environ.get('THANA_TTS_ENABLED')=='1' and bool(os.environ.get('AZURE_SPEECH_KEY')) and bool(re.fullmatch(r'[a-z0-9]{2,40}',os.environ.get('AZURE_SPEECH_REGION','')))
    @app.get('/api/platform/admin/tts/status')
    @legacy['content_required']
    def tts_status():return jsonify(enabled=enabled(),provider='Microsoft Azure',voices=[{'id':v,'language':d[0],'label':d[1]} for v,d in VOICES.items()],max_characters=1000,daily_limit=20)
    @app.post('/api/platform/admin/tts')
    @legacy['content_required']
    def generate_audio():
        if not enabled():return jsonify(error='ຍັງບໍ່ໄດ້ຕັ້ງຄ່າ Azure TTS / Azure TTS 설정이 필요합니다'),503
        d=request.get_json(silent=True) or {};text=d.get('text');voice=d.get('voice');title=d.get('title','')
        if not isinstance(text,str) or not 1<=len(text.strip())<=1000 or any(ord(ch)<32 and ch not in '\n\t\r' for ch in text):return jsonify(error='Use 1–1000 text characters'),400
        if not isinstance(voice,str) or voice not in VOICES or d.get('consent') is not True or not isinstance(title,str) or len(title)>200:return jsonify(error='Select voice and consent to Azure synthesis'),400
        text=text.strip();language=VOICES[voice][0];fingerprint=hashlib.sha256(('azure-wav24-v1\0'+voice+'\0'+text).encode()).hexdigest()
        with db() as c:
            existing=c.execute('SELECT m.id,m.filename FROM generated_audio g JOIN media_assets m ON m.id=g.asset WHERE g.fingerprint=?',(fingerprint,)).fetchone()
            if existing and os.path.isfile(os.path.join(legacy['DATA'],'media',existing['filename'])):return jsonify(id=existing['id'],url='/media/library/'+existing['filename'],cached=True)
            if existing:return jsonify(error='Cached audio file is missing; restore the media backup'),409
            day=time.strftime('%Y-%m-%d',time.gmtime());c.execute('BEGIN IMMEDIATE');usage=c.execute('SELECT count FROM tts_usage WHERE owner=? AND day=?',(owner(),day)).fetchone()
            if usage and usage['count']>=20:return jsonify(error='Daily audio generation limit reached'),429
            c.execute('INSERT OR REPLACE INTO tts_usage VALUES (?,?,?)',(owner(),day,(usage['count'] if usage else 0)+1))
        ssml=f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{language}"><voice name="{voice}">{escape(text)}</voice></speak>'
        url='https://'+os.environ['AZURE_SPEECH_REGION']+'.tts.speech.microsoft.com/cognitiveservices/v1'
        headers={'Ocp-Apim-Subscription-Key':os.environ['AZURE_SPEECH_KEY'],'Content-Type':'application/ssml+xml','X-Microsoft-OutputFormat':'riff-24khz-16bit-mono-pcm','User-Agent':'ThanaKorean'}
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=ssml.encode(),headers=headers),timeout=45) as response:raw=response.read(10*1024*1024+1)
            if len(raw)>10*1024*1024:raise ValueError()
            with wave.open(io.BytesIO(raw),'rb') as audio:
                if audio.getnchannels()!=1 or audio.getsampwidth()!=2 or audio.getframerate()!=24000 or not 0<audio.getnframes()<=180*24000 or len(audio.readframes(audio.getnframes()))!=audio.getnframes()*2:raise ValueError()
        except (urllib.error.URLError,TimeoutError,ValueError,wave.Error,EOFError):return jsonify(error='ສ້າງສຽງບໍ່ສຳເລັດ ກວດບໍລິການ/ສຽງ/region / 음성 서비스와 지역을 확인하세요'),502
        # Recheck under a write transaction to prevent duplicate cache records.
        with db() as c:
            c.execute('BEGIN IMMEDIATE');existing=c.execute('SELECT m.id,m.filename FROM generated_audio g JOIN media_assets m ON m.id=g.asset WHERE g.fingerprint=?',(fingerprint,)).fetchone()
            if existing:return jsonify(id=existing['id'],url='/media/library/'+existing['filename'],cached=True)
            mid=secrets.token_urlsafe(12);filename=secrets.token_hex(16)+'.wav';path=os.path.join(legacy['DATA'],'media',filename)
            try:
                with open(path,'xb') as f:f.write(raw)
                c.execute('INSERT INTO media_assets VALUES (?,?,?,?,0)',(mid,'[AI] '+(title.strip() or text[:60]),filename,'audio'))
                c.execute('INSERT INTO generated_audio VALUES (?,?,?,?,?,?,0)',(mid,fingerprint,text,voice,language,time.time()))
            except Exception:
                if os.path.exists(path):os.unlink(path)
                raise
        return jsonify(id=mid,url='/media/library/'+filename,cached=False),201
    @app.post('/api/platform/admin/tts/<mid>/review')
    @legacy['content_required']
    def review_generated_audio(mid):
        if (request.get_json(silent=True) or {}).get('reviewed') is not True:return jsonify(error='Confirm that you listened and checked the pronunciation'),400
        with db() as c:
            if not c.execute('SELECT 1 FROM generated_audio WHERE asset=?',(mid,)).fetchone():return jsonify(error='Not found'),404
            c.execute('UPDATE generated_audio SET reviewed=1 WHERE asset=?',(mid,))
        return jsonify(ok=True)
