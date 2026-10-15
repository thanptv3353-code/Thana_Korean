"""Production/staging launcher: validate durable paths, initialize, then Gunicorn."""
import argparse,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from deployment_config import validate_deployment

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');parser.add_argument('--init-only',action='store_true');args=parser.parse_args()
    try:settings=validate_deployment(os.environ,root)
    except ValueError as exc:raise SystemExit(str(exc))
    if args.check:print('Deployment environment valid; credentials are not displayed');return
    subprocess.run([sys.executable,str(root/'scripts/init_content.py')],cwd=root,check=True)
    if args.init_only:print('Persistent application initialization complete');return
    os.chdir(root)
    os.execvp('gunicorn',['gunicorn','--bind','0.0.0.0:'+str(settings['port']),'--workers','1','--threads','4','--timeout','120','app:app'])
if __name__=='__main__':main()
