"""Explicit staff import of authored bilingual curriculum drafts."""
import io
import json
import zipfile
from flask import jsonify, request, send_file
from curriculum_pack import PACK, COURSES, import_drafts, audio_scripts


def install_curriculum(app, legacy, db, owner):
    @app.get('/api/platform/admin/curriculum-audio-scripts')
    @legacy['content_required']
    def curriculum_audio_scripts():
        return jsonify(pack=PACK,source='authored-source-pack',scripts=audio_scripts())

    @app.get('/api/platform/admin/curriculum-audio-scripts/download')
    @legacy['content_required']
    def curriculum_audio_download():
        language=request.args.get('language','all')
        if language not in ('all','ko','lo') or set(request.args)-{'language'} or len(request.args.getlist('language'))>1:
            return jsonify(error='Invalid recording script language'),400
        items=[item for item in audio_scripts() if language=='all' or item['language']==language]
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('README.txt',
                'THANA KOREAN · foundation-v1 · source vocabulary recording drafts\n'
                'ຮ່າງບົດອ່ານ; ຍັງບໍ່ມີໄຟລ໌ສຽງ. / 검토용 녹음 원고이며 음성 파일이 아닙니다.\n'
                'Source pack only; later live lesson edits are not included.\n'
                'Review vocabulary, letter names versus actual sounds, pauses and language before recording.\n'
                'Record one lesson per file. Use its stable lesson ID as filename.\n'
                'Upload through Media Studio; listen and review before publishing or attaching to a lesson.\n'
                'No provider was called; no lesson or media was changed by this export.\n')
            archive.writestr('manifest.json',json.dumps(dict(pack=PACK,source='authored-source-pack',scripts=items),ensure_ascii=False,indent=2))
            for item in items:
                archive.writestr(item['language']+'/'+item['lesson']+'.txt',item['text']+'\n')
        output.seek(0)
        response=send_file(output,mimetype='application/zip',as_attachment=True,download_name='thana-recording-scripts-'+language+'.zip')
        response.headers['Cache-Control']='private, no-store'
        return response

    @app.post('/api/platform/admin/curriculum-pack')
    @legacy['admin_required']
    def curriculum_pack_import():
        d=request.get_json(silent=True)
        if not isinstance(d,dict) or set(d)!={'pack','language'} or d['pack']!=PACK or not isinstance(d['language'],str) or d['language'] not in ('all','ko','lo'):
            return jsonify(error='Invalid curriculum pack'),400
        try:
            with db() as c:
                c.execute('BEGIN IMMEDIATE');counts=import_drafts(c,owner(),d['language'])
        except ValueError as error:return jsonify(error=str(error)),409
        return jsonify(ok=True,added=sum(counts.values()),counts=counts,courses=[COURSES[language][0] for language in counts],published_new=0)
