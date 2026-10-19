import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from firebase_curriculum import load_source
from firebase_eps_media import inventory
from scripts.collect_firebase_eps_media import collect,FixedOrigin

class FirebaseEpsMediaTests(unittest.TestCase):
    def test_all_original_ids_and_image_choice_dependencies_retained(self):
        source=load_source();manifest=inventory(source)
        self.assertEqual(len(manifest['questions']),531);self.assertEqual(len(manifest['assets']),517)
        self.assertEqual(sum(q['image_choices'] for q in manifest['questions']),30)
        self.assertEqual({q['id'] for q in manifest['questions']},{q['id'] for c in source['eps'] for q in c['questions']})
        self.assertTrue(any(use['usage']=='choice:3' for a in manifest['assets'] for use in a['uses']))
        bad=copy.deepcopy(source);bad['eps'][0]['questions'][0]['image_url']='../secret.png'
        with self.assertRaises(ValueError):inventory(bad)
        bad=copy.deepcopy(source);bad['eps'][0]['questions'][0]['correct_answer_index']=True
        with self.assertRaises(ValueError):inventory(bad)
    def test_collector_checks_bytes_retains_failures_and_never_overwrites(self):
        manifest=dict(assets=[dict(path='images/ok.png',kind='image'),dict(path='audio/bad.mp3',kind='audio')])
        class Opener:
            def open(self,url,timeout):return io.BytesIO(b'\x89PNG\r\n\x1a\nsynthetic' if url.endswith('ok.png') else b'<html>SPA fallback</html>')
        with tempfile.TemporaryDirectory() as temp,patch('scripts.collect_firebase_eps_media.urllib.request.build_opener',return_value=Opener()):
            dest=Path(temp)/'media';summary=collect(manifest,dest)
            self.assertEqual((summary['collected'],summary['failed']),(1,1))
            records=[json.loads(line) for line in (dest/'receipt.jsonl').read_text().splitlines()]
            self.assertEqual((dest/records[0]['filename']).stat().st_mode&0o777,0o600)
            self.assertEqual(records[1]['error_type'],'ValueError')
            with self.assertRaises(FileExistsError):collect(manifest,dest)
        with self.assertRaises(ValueError):FixedOrigin().redirect_request(None,None,302,'',{},'https://elsewhere.example/')
    def test_local_candidates_are_byte_preserved_and_require_review(self):
        from scripts.collect_local_firebase_media import collect_local
        from PIL import Image
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'original';(root/'images').mkdir(parents=True)
            image=root/'images/one.png';Image.new('RGB',(2,2),'white').save(image);original=image.read_bytes()
            manifest=dict(assets=[dict(path='images/one.png',kind='image'),dict(path='audio/missing.mp3',kind='audio')])
            dest=Path(temp)/'candidate';summary=collect_local(manifest,root,dest)
            self.assertEqual(summary,dict(assets=2,candidates=1,missing=1,published=0))
            receipt=json.loads((dest/'receipt.json').read_text())
            self.assertEqual(receipt[0]['status'],'candidate-needs-content-review')
            self.assertEqual((dest/receipt[0]['filename']).read_bytes(),original)
            self.assertEqual(image.read_bytes(),original)
            with self.assertRaises(FileExistsError):collect_local(manifest,root,dest)
