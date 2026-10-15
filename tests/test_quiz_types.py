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
