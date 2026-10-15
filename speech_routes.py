"""Optional Azure short-audio recognition and Korean pronunciation assessment."""
import base64,io,json,os,re,time,urllib.request,urllib.error,wave
from flask import jsonify,request

def install_speech(app,legacy,db,owner):
    with db() as c:c.execute('CREATE TABLE IF NOT EXISTS speech_usage (owner TEXT, day TEXT, count INTEGER, PRIMARY KEY(owner,day))')
    def enabled():return os.environ.get('THANA_SPEECH_ENABLED')=='1' and bool(os.environ.get('AZURE_SPEECH_KEY')) and bool(re.fullmatch(r'[a-zA-Z0-9-]+',os.environ.get('AZURE_SPEECH_RESOURCE','')))
    @app.get('/api/platform/speech/status')
    def speech_status():return jsonify(enabled=enabled(),provider='Microsoft Azure' if enabled() else None,pronunciation_languages=['ko-KR'],recognition_languages=['ko-KR','lo-LA'])
    @app.post('/api/platform/speech')
    def assess_speech():
        if not owner():return jsonify(error='Login required'),401
        if not enabled():return jsonify(error='Speech provider is not configured'),503
        language=request.form.get('language');reference=request.form.get('reference','');consent=request.form.get('consent')
        if language not in ('ko-KR','lo-LA') or not 1<=len(reference)<=500 or consent!='true':return jsonify(error='Select language, reference text and consent'),400
        file=request.files.get('file')
        if not file:return jsonify(error='Select recorded audio'),400
        raw=file.read(1_000_001)
        if len(raw)>1_000_000:return jsonify(error='Audio is too large'),400
        try:
            with wave.open(io.BytesIO(raw),'rb') as w:
                if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=16000 or not 0<w.getnframes()<=30*16000 or len(w.readframes(w.getnframes()))!=w.getnframes()*2:raise ValueError()
        except (wave.Error,EOFError,ValueError):return jsonify(error='Use mono 16kHz PCM WAV, maximum 30 seconds'),400
        day=time.strftime('%Y-%m-%d',time.gmtime())
        with db() as c:
            c.execute('BEGIN IMMEDIATE');r=c.execute('SELECT count FROM speech_usage WHERE owner=? AND day=?',(owner(),day)).fetchone()
            if r and r['count']>=50:return jsonify(error='Daily speech limit reached'),429
            c.execute('INSERT OR REPLACE INTO speech_usage VALUES (?,?,?)',(owner(),day,(r['count'] if r else 0)+1))
        headers={'Ocp-Apim-Subscription-Key':os.environ['AZURE_SPEECH_KEY'],'Content-Type':'audio/wav; codecs=audio/pcm; samplerate=16000','Accept':'application/json'}
        if language=='ko-KR':headers['Pronunciation-Assessment']=base64.b64encode(json.dumps({'ReferenceText':reference,'GradingSystem':'HundredMark','Granularity':'Word','Dimension':'Comprehensive','EnableMiscue':True}).encode()).decode()
        url='https://'+os.environ['AZURE_SPEECH_RESOURCE']+'.cognitiveservices.azure.com/stt/speech/recognition/conversation/cognitiveservices/v1?language='+language+'&format=detailed'
        try:
            with urllib.request.urlopen(urllib.request.Request(url,data=raw,headers=headers),timeout=30) as response:d=json.load(response)
        except (urllib.error.URLError,ValueError,TimeoutError):return jsonify(error='Speech service unavailable'),502
        best=(d.get('NBest') or [{}])[0];assessment=best.get('PronunciationAssessment',best);keys=('AccuracyScore','FluencyScore','CompletenessScore','PronScore')
        scores={k:assessment[k] for k in keys if language=='ko-KR' and isinstance(assessment.get(k),(int,float))}
        return jsonify(transcript=best.get('Display',d.get('DisplayText','')),scores=scores,assessment_available=bool(scores),language=language,provider='Microsoft Azure')
