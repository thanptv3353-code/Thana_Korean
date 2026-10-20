"""Inspect a private runtime without starting Flask, creating DBs or contacting providers."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_readiness import inspect_runtime

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runtime', type=Path)
    args = parser.parse_args()
    report = inspect_runtime(args.runtime)
    print(json.dumps(report))
    # Passing offline checks is deliberately distinct from production approval.
    sys.exit(1 if report['blockers'] else 0)
