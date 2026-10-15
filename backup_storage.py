"""Append a SQLite snapshot and audio assets to an authenticated backup ZIP."""
import json,os,sqlite3,tempfile
from pathlib import Path

def append_platform_backup(archive,base,data):
    platform=Path(os.environ.get('THANA_PLATFORM_DB',str(Path(base)/'data/platform.sqlite3')))
    if platform.exists():
        with tempfile.TemporaryDirectory() as tmp:
            snapshot=Path(tmp)/'platform.sqlite3';src=sqlite3.connect(str(platform));dest=sqlite3.connect(str(snapshot))
            try:src.backup(dest)
            finally:src.close();dest.close()
            archive.write(snapshot,'platform.sqlite3')
    media=Path(data)/'media'
    if media.exists():
        for file in media.iterdir():
            if file.is_file() and not file.is_symlink():archive.write(file,'media/'+file.name)
    receipts=Path(data)/'receipts'
    if receipts.exists():
        for file in receipts.iterdir():
            if file.is_file() and not file.is_symlink():archive.write(file,'receipts/'+file.name)
    archive.writestr('manifest.json',json.dumps({'format':2,'legacy':'users.json, lessons.json, progress.json','platform':'platform.sqlite3','media':'media/','receipts':'receipts/','contains_private_accounts':True,'session_secret_included':False},indent=2))
