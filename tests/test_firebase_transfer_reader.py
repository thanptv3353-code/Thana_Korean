import unittest
import urllib.parse
from scripts.read_firebase_transfer import COLLECTIONS,PROJECT,collect,value
from firebase_migration import inspect_transfer

class FirebaseTransferReaderTests(unittest.TestCase):
    def test_pagination_preserves_wire_types_and_fixed_snapshot(self):
        calls=[]
        wire={'username':{'stringValue':'synthetic'},'role':{'stringValue':'student'},'approved':{'booleanValue':True},'createdAt':{'timestampValue':'2026-10-17T00:00:00Z'},'counter':{'integerValue':'9007199254740993'},'nested':{'mapValue':{'fields':{'items':{'arrayValue':{'values':[{'nullValue':None},{'doubleValue':'NaN'}]}}}}}}
        def get(url):
            calls.append(url);parsed=urllib.parse.urlparse(url);q=urllib.parse.parse_qs(parsed.query)
            self.assertEqual(parsed.scheme,'https');self.assertEqual(parsed.hostname,'firestore.googleapis.com')
            self.assertEqual(q['readTime'],['2026-10-17T01:00:00.000001Z'])
            if parsed.path.endswith('/thana_users'):
                if 'pageToken' not in q:return {'documents':[{'name':f'projects/{PROJECT}/databases/(default)/documents/thana_users/stable_uid','fields':wire}],'nextPageToken':'second'}
                self.assertEqual(q['pageToken'],['second'])
            return {}
        payload=collect(get,'2026-10-17T01:00:00.000001Z')
        self.assertEqual(len(calls),len(COLLECTIONS)+1)
        document=payload['collections']['thana_users'][0]
        self.assertEqual(document['firestore_fields'],wire)
        self.assertEqual(document['data']['counter'],9007199254740993)
        self.assertEqual(document['data']['createdAt'],'2026-10-17T00:00:00Z')
        self.assertEqual(inspect_transfer(payload)[1]['records'],1)
        document['data']['username']='mismatch'
        with self.assertRaises(ValueError):inspect_transfer(payload)

    def test_rejects_foreign_document_paging_loop_and_limit(self):
        for get,limit in [(lambda url:{'documents':[{'name':'projects/other/databases/(default)/documents/thana_users/id','fields':{}}]},10),(lambda url:{'nextPageToken':'same'},10),(lambda url:{'documents':[{'name':f'projects/{PROJECT}/databases/(default)/documents/thana_users/id','fields':{}}]},0)]:
            with self.assertRaises(ValueError):collect(get,'2026-10-17T00:00:00Z',limit)
        with self.assertRaises(ValueError):value({'unknown':'x'})
        with self.assertRaises(ValueError):value({'stringValue':'x','booleanValue':True})
