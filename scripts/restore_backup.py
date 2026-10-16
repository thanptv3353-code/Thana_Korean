"""Validate a backup and restore only into a new/empty isolated directory."""
import argparse,json,os,re,sqlite3,tempfile,zipfile
from pathlib import Path

def restore(archive,output,apply=False):
    output=Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):raise ValueError('Output must be a new or empty directory')
    if output.is_symlink():raise ValueError('Output cannot be a symlink')
    with zipfile.ZipFile(archive) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate archive names')
        if sum(i.file_size for i in z.infolist())>256*1024*1024:raise ValueError('Archive exceeds 256 MB')
        for info in z.infolist():
            allowed=info.filename in ('users.json','lessons.json','progress.json','manifest.json','platform.sqlite3') or re.fullmatch(r'(media|receipts)/[0-9a-f]{32}\.(mp3|wav|jpg|png)',info.filename) or re.fullmatch(r'media/[0-9a-f]{32}\.mp4',info.filename)
            if not allowed or (info.external_attr>>16)&0o170000==0o120000:raise ValueError('Unexpected or unsafe archive path')
        for name,kind in [('users.json',dict),('lessons.json',list),('progress.json',dict)]:
            if name not in names or not isinstance(json.loads(z.read(name)),kind):raise ValueError('Invalid legacy backup schema')
        if 'platform.sqlite3' in names:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'validate.sqlite3';p.write_bytes(z.read('platform.sqlite3'));c=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True)
                try:
                    if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
                finally:c.close()
        if apply:
            output.mkdir(parents=True,exist_ok=True,mode=0o700)
            for name in names:
                p=output/name;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
                with os.fdopen(os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600),'wb') as f:f.write(z.read(name))
        return {'files':len(names),'applied':apply,'output':str(output.resolve())}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('archive');parser.add_argument('output');parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    try:print(json.dumps(restore(args.archive,args.output,args.apply)))
    except (ValueError,zipfile.BadZipFile,sqlite3.DatabaseError,KeyError) as e:raise SystemExit(str(e))
