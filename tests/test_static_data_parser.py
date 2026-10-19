import unittest
from static_data_parser import parse_constants
class StaticDataParserTests(unittest.TestCase):
    def test_literal_references_spreads_unicode_and_comment_delimiters_in_strings(self):
        result=parse_constants('''// comment
const A=[{id:"original",lo:"ສະບາຍດີ",ko:"안녕하세요",url:"https://example.com/a//b"}];
const B=[...A,{value:-2,ok:true,empty:null}]; /* comment */ const C={...B[0]};'''.replace('const C={...B[0]};','const C={text:"line\\nnext",quote:\'it\\\'s\'};'))
        self.assertEqual(result['B'][0]['id'],'original');self.assertEqual(result['A'][0]['lo'],'ສະບາຍດີ')
        result['B'][0]['id']='changed';self.assertEqual(result['A'][0]['id'],'original')
        self.assertEqual(result['C']['text'],'line\nnext');self.assertEqual(result['C']['quote'],"it's")

    def test_rejects_execution_unknown_references_truncation_and_duplicate_keys(self):
        for source in ['const A=process.exit();','const A=(()=>1)();','const A=new Date();','const A=missing;','const A=[1,','const A={x:1,x:2};','const A={__proto__:{}};','const A=1; A=2;','const A=`${process.exit()}`;']:
            with self.subTest(source=source),self.assertRaises(ValueError):parse_constants(source)
