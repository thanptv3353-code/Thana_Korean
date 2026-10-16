"""Explicit private email worker. Prints counts only, never addresses or links."""
import argparse,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from email_delivery import deliver_pending
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=20);args=parser.parse_args()
    path=os.environ.get('THANA_PLATFORM_DB')
    if not path or not Path(path).is_file():raise SystemExit('Set THANA_PLATFORM_DB to the initialized private database')
    try:print(json.dumps(deliver_pending(path,args.limit)))
    except ValueError as e:raise SystemExit(str(e))
