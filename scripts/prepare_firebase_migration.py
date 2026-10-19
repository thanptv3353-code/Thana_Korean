"""Inspect an explicit Firebase working transfer; optionally stage outside source."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_migration import inspect_transfer,stage_transfer


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('transfer',type=Path)
    parser.add_argument('--stage-db',type=Path,help='New private SQLite staging file outside the source checkout')
    args=parser.parse_args()
    try:
        if args.transfer.stat().st_size>64*1024*1024:raise ValueError('Transfer exceeds 64 MB')
        payload=json.loads(args.transfer.read_text(encoding='utf-8'))
        report=stage_transfer(payload,args.stage_db) if args.stage_db else inspect_transfer(payload)[1]
    except (ValueError,OSError,TypeError):
        parser.exit(1,'Migration transfer invalid or destination unavailable; no application data was changed.\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
