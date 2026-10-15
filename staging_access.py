"""Optional shared access gate for a separate review deployment."""
import os,secrets
from flask import request,Response

def install_staging_access(app):
    if os.environ.get('THANA_STAGING_ENABLED')!='1':return
    username=os.environ.get('THANA_STAGING_USER','reviewer')
    password=os.environ.get('THANA_STAGING_PASSWORD','')
    if not username or ':' in username or len(password)<16:
        raise RuntimeError('Staging requires a username and a private password of at least 16 characters')
    @app.before_request
    def staging_gate():
        if request.path=='/health':return
        auth=request.authorization
        if not auth or auth.type.lower()!='basic' or not secrets.compare_digest((auth.username or '').encode(),username.encode()) or not secrets.compare_digest((auth.password or '').encode(),password.encode()):
            return Response('THANA KOREAN staging: authorized reviewers only.',401,{'WWW-Authenticate':'Basic realm="THANA KOREAN staging", charset="UTF-8"'})
    demo=os.environ.get('THANA_STAGING_DEMO')=='1'
    @app.after_request
    def staging_headers(response):
        response.headers['X-Robots-Tag']='noindex, nofollow, noarchive'
        response.headers['Cache-Control']='no-store'
        if demo and response.status_code==200 and response.mimetype=='text/html' and not response.direct_passthrough:
            body=response.get_data(as_text=True)
            marker=body.lower().find('<body')
            if marker>=0:
                end=body.find('>',marker)+1
                banner='<aside role="note" style="background:#fff3cd;color:#332600;padding:12px;text-align:center">STAGING DEMO · ສຳລັບທົດລອງເທົ່ານັ້ນ · ຂໍ້ມູນອາດຖືກລ້າງເມື່ອ restart · 테스트 전용: 재시작 시 데이터가 초기화될 수 있습니다. ຢ່າໃສ່ຂໍ້ມູນສ່ວນຕົວ / 개인정보를 입력하지 마세요.</aside>'
                response.set_data(body[:end]+banner+body[end:])
        return response
