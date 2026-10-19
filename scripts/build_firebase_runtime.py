"""Build a NEW private runtime candidate, with all UID bindings disabled."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_runtime_candidate import build_candidate

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('transfer',type=Path);parser.add_argument('destination',type=Path);a=parser.parse_args()
    if a.transfer.stat().st_size>64*1024*1024:parser.error('Transfer exceeds 64 MB')
    print(json.dumps(build_candidate(json.loads(a.transfer.read_text(encoding='utf-8')),a.destination)))
