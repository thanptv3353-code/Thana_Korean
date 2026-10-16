import unittest,quiz_engine
class QuizTypesTests(unittest.TestCase):
 def test_blank_variants_and_answer_stripping(self):
  q={'type':'blank','question':'Hello?','accepted':['안녕하세요','안녕'],'explanation':'Test'}
  self.assertTrue(quiz_engine.valid(q));self.assertNotIn('accepted',quiz_engine.public(q));self.assertNotIn('explanation',quiz_engine.public(q));self.assertTrue(quiz_engine.grade(q,' 안녕하세요 ')['correct']);self.assertFalse(quiz_engine.grade(q,'wrong')['correct'])
 def test_ordering_requires_permutation(self):
  q={'type':'ordering','question':'Order','options':['학교에','갑니다','저는'],'answer':[2,0,1]}
  self.assertTrue(quiz_engine.valid(q));self.assertTrue(quiz_engine.grade(q,[2,0,1])['correct'])
  with self.assertRaises(ValueError):quiz_engine.grade(q,[0,0,1])
 def test_matching_hides_pair_mapping(self):
  q={'type':'matching','question':'Match','pairs':[{'left':'학교','right':'ໂຮງຮຽນ'},{'left':'물','right':'ນ້ຳ'}]}
  self.assertTrue(quiz_engine.valid(q));self.assertNotIn('pairs',quiz_engine.public(q));self.assertTrue(quiz_engine.grade(q,['ໂຮງຮຽນ','ນ້ຳ'])['correct']);self.assertFalse(quiz_engine.grade(q,['ນ້ຳ','ໂຮງຮຽນ'])['correct'])
 def test_metadata_all_types_and_source_privacy(self):
  qs=[{'type':'choice','question':'Choose','options':['a','b'],'answer':0},{'type':'blank','question':'Fill','accepted':['a']},{'type':'ordering','question':'Order','options':['a','b'],'answer':[1,0]},{'type':'matching','question':'Match','pairs':[{'left':'a','right':'A'},{'left':'b','right':'B'}]}]
  for base,answer in zip(qs,[0,'a',[1,0],['A','B']]):
   q={**base,'category':'ຄຳສັບ / 어휘','difficulty':'intermediate','source':'Synthetic reference <b>plain text</b>','explanation':'Reviewed explanation'}
   self.assertTrue(quiz_engine.valid(q));public=quiz_engine.public(q)
   self.assertEqual(public['category'],q['category']);self.assertEqual(public['difficulty'],'intermediate');self.assertNotIn('source',public);self.assertNotIn('explanation',public)
   result=quiz_engine.grade(q,answer);self.assertTrue(result['correct']);self.assertEqual(result['source'],q['source'])
 def test_metadata_type_and_size_limits(self):
  base={'question':'Choose','options':['a','b'],'answer':0}
  self.assertTrue(quiz_engine.valid(base))
  for key,limit in [('category',100),('source',500),('explanation',5000)]:
   self.assertTrue(quiz_engine.valid({**base,key:'a'*limit}))
   for bad in (None,[],{},123,'a'*(limit+1)):
    self.assertFalse(quiz_engine.valid({**base,key:bad}),(key,type(bad)))
  for bad in (None,[],123,'expert'):
   self.assertFalse(quiz_engine.valid({**base,'difficulty':bad}))
