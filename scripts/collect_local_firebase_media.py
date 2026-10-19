"""Collect exact relative-path candidates from a read-only original media root."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_curriculum import load_source
from firebase_eps_media import inventory


def collect_local(manifest,source,destination):
    source=Path(source).resolve();destination=Path(destination)
    destination.mkdir(mode=0o700,exist_ok=False)
    results=[]
    for asset in manifest['assets']:
        relative=Path(asset['path']);path=(source/relative).resolve()
        if relative.is_absolute() or '..' in relative.parts or source not in path.parents:raise ValueError('Unsafe original path')
        record=dict(path=asset['path'],status='missing')
        if path.is_file():
            if path.stat().st_size>16*1024*1024:raise ValueError('Original asset too large')
            body=path.read_bytes()
            if asset['kind']=='image':
                with Image.open(io.BytesIO(body)) as image:image.verify()
            else:
                if not (body.startswith(b'ID3') or (len(body)>1 and body[0]==255 and body[1]&224==224)):raise ValueError('Unsupported audio candidate')
            filename=hashlib.sha256(asset['path'].encode()).hexdigest()+relative.suffix
            fd=os.open(destination/filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'wb') as output:output.write(body)
            record.update(status='candidate-needs-content-review',filename=filename,bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        results.append(record)
    fd=os.open(destination/'receipt.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(results,output)
    return dict(assets=len(results),candidates=sum(r['status']!='missing' for r in results),missing=sum(r['status']=='missing' for r in results),published=0)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('original_root',type=Path);p.add_argument('destination',type=Path);a=p.parse_args()
    root=Path(__file__).resolve().parents[1];parent=a.destination.parent.resolve();source=a.original_root.resolve();dest=a.destination.resolve()
    if parent==root or root in parent.parents or dest==source or source in dest.parents:p.error('Choose a private output outside source and original folders')
    print(json.dumps(collect_local(inventory(load_source()),source,a.destination)))
