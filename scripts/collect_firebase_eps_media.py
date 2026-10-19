"""Collect public original EPS assets privately; no app publication or source writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_eps_media import inventory

class FixedOrigin(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError('Unexpected redirect; original media not collected')


def collect(manifest,directory):
    directory=Path(directory);directory.mkdir(mode=0o700,parents=False,exist_ok=False)
    opener=urllib.request.build_opener(FixedOrigin());total=0;results=[]
    with (directory/'receipt.jsonl').open('x',encoding='utf-8') as receipt:
        os.chmod(directory/'receipt.jsonl',0o600)
        for item in manifest['assets']:
            path=item['path'];record=dict(path=path,status='failed')
            try:
                # Revalidate even if a caller supplied a handmade manifest.
                import re
                if not re.fullmatch(r'(?:images|audio)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|mp3)',path):raise ValueError('Invalid path')
                with opener.open('https://thanakorean.com/'+path,timeout=20) as response:
                    body=response.read(16*1024*1024+1)
                if not body or len(body)>16*1024*1024:raise ValueError('Asset size rejected')
                if total+len(body)>256*1024*1024:raise ValueError('Total transfer limit reached')
                image=body.startswith((b'\x89PNG\r\n\x1a\n',b'\xff\xd8\xff'))
                audio=body.startswith(b'ID3') or (len(body)>1 and body[0]==255 and body[1]&224==224)
                if not (audio if item['kind']=='audio' else image):raise ValueError('Unexpected media bytes')
                digest=hashlib.sha256(body).hexdigest();filename=hashlib.sha256(path.encode()).hexdigest()+Path(path).suffix
                fd=os.open(directory/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(fd,'wb') as output:output.write(body)
                total+=len(body);record.update(status='collected',filename=filename,sha256=digest,bytes=len(body),kind=item['kind'])
            except Exception as error:
                record['error_type']=type(error).__name__
            results.append(record);receipt.write(json.dumps(record)+'\n');receipt.flush()
            if len(results)%25==0:print('THANA_MEDIA_PROGRESS '+json.dumps(dict(processed=len(results),collected=sum(r['status']=='collected' for r in results))),flush=True)
    summary=dict(assets=len(results),collected=sum(r['status']=='collected' for r in results),failed=sum(r['status']!='collected' for r in results),bytes=total)
    print('THANA_MEDIA_RESULT '+json.dumps(summary),flush=True)
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('directory',type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];parent=a.directory.parent.resolve()
    if parent==root or root in parent.parents:p.error('Media must remain outside source')
    collect(inventory(json.loads(a.source.read_text(encoding='utf-8'))),a.directory)
