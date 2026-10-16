"""Explicit offline activation. Dry-run by default; never prints credentials."""
import argparse,os,sys
from pathlib import Path

def activate(legacy,username,apply=False):
    if any(u.get('role')=='superadmin' for u in legacy.users.values()):raise ValueError('A Super Admin already exists; manage permissions through that account')
    user=legacy.users.get(username)
    if not user or user.get('role')!='admin' or user.get('status')!='approved':raise ValueError('Choose an existing approved administrator')
    if not str(user.get('pw','')).startswith('pbkdf2_sha256$'):raise ValueError('First update this administrator password through /account')
    if apply:
        user['role']='superadmin';user['auth_version']=user.get('auth_version',0)+1
        legacy._save(legacy.USERS_FILE,legacy.users)
    return {'username':username,'role':'superadmin','applied':apply}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--username',required=True);parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if not os.environ.get('THANA_DATA_DIR'):parser.error('Set THANA_DATA_DIR explicitly to the intended private runtime; stop the server first')
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));import app as legacy
    try:result=activate(legacy,args.username,args.apply)
    except ValueError as e:parser.error(str(e))
    print(('Activated' if result['applied'] else 'Dry-run only: would activate')+' Super Admin: '+args.username)

if __name__=='__main__':main()
