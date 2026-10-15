"""Idempotent first-run starter content setup; never import private users."""
import os,runpy,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
runpy.run_path(str(root/'scripts/seed_vocabulary.py'),run_name='__main__')
sys.argv=['seed_lao_starter.py','--publish','--database',os.environ.get('THANA_PLATFORM_DB',str(root/'data/platform.sqlite3'))]
runpy.run_path(str(root/'scripts/seed_lao_starter.py'),run_name='__main__')
