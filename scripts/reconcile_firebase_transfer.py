"""Write an exclusive private reconciliation plan; print only aggregate counts."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_reconciliation import reconcile_transfer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transfer',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.transfer.stat().st_size>64*1024*1024:parser.error('Input exceeds 64 MB')
    root=Path(__file__).resolve().parents[1];parent=args.output.parent.resolve()
    if parent==root or root in parent.parents:parser.error('Private output must be outside source')
    plan=reconcile_transfer(json.loads(args.transfer.read_text(encoding='utf-8')))
    fd=os.open(args.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as output:json.dump(plan,output,ensure_ascii=False,allow_nan=False)
    print(json.dumps(plan['summary']))

if __name__=='__main__':main()
