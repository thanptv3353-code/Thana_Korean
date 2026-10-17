"""Package reviewable source and public lessons; exclude all runtime accounts."""
from pathlib import Path
import zipfile
root = Path(__file__).resolve().parents[1]
files = list(root.glob('*.py'))
files += [root / name for name in ('README.md','AGENTS.md','requirements.txt','requirements.staging.lock.txt','Dockerfile','.python-version','render.staging.yaml','.dockerignore','.env.example','.gitignore')]
for folder in ('templates','static','scripts','tests','docs','curriculum'):
    files += [p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.jpg','.png')]
# Include only public static bitmap assets, never runtime uploads.
files += [p for p in (root/'static').rglob('*') if p.is_file() and p.suffix in ('.png','.jpg')]
files += [root/'data/lessons.json',root/'data/eps_questions.json']
target = root/'SOURCE_REVIEW.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for p in sorted(set(files)):
        if p.exists() and not p.is_symlink(): archive.write(p,p.relative_to(root))
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert not any(Path(n).name in ('users.json','progress.json','secret_key','bootstrap_credentials.txt') or '.sqlite3' in n for n in archive.namelist())
    print('Source archive verified:',len(archive.namelist()),'files')
