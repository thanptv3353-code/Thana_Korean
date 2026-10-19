"""Offline original-image draft import. Stop the target server first; dry-run default."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from firebase_media_import import import_recovered_images
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--candidates',type=Path,required=True);p.add_argument('--library',type=Path,required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
    print(json.dumps(import_recovered_images(a.database,a.candidates,a.library,a.apply)))
