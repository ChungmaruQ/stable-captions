import unittest
from utterance_units import ClauseBuffer,speech_act,normalize_source
class UnitsTests(unittest.TestCase):
 def test_question_and_statement(self):
  for t in ['효과가 있습니까?','무슨 재료인가요?','왜 이런 결과가 나왔나요?','어떻게 합니까?']:self.assertEqual(speech_act(t),'question')
  for t in ['효과가 있는지 확인했습니다.','효과가 없습니다?']:self.assertEqual(speech_act(t),'statement')
 def test_incomplete_question_marks(self):
  for t in ['여기에 색소를 조금 넣으면?','탱탱볼 제조 실험은?','여기에는 PVA와.']:self.assertEqual(speech_act(t),'continuation');self.assertNotIn('?',normalize_source(t))
 def test_merge_keeps_both_ingredients(self):
  b=ClauseBuffer();self.assertEqual(b.push('a','Here PVA and','여기에는 PVA와.',None,None,0),[])
  out=b.push('b','Two boric acids','붕산이라는 두 재료가 있는데요.',None,None,.8)
  self.assertEqual(len(out),1);self.assertEqual(out[0]['ko'],'여기에는 PVA와 붕산이라는 두 재료가 있는데요');self.assertEqual(out[0]['en'],'')
 def test_deadline_not_extended(self):
  b=ClauseBuffer();b.push('a','','여기에는 PVA와',None,None,0);b.push('b','','붕산을',None,None,1)
  self.assertTrue(b.due(1.21));self.assertEqual(b.pop()['ko'],'여기에는 PVA와 붕산을')
 def test_language_switch_flushes_first(self):
  b=ClauseBuffer();b.push('a','','PVA와',None,None,0)
  out=b.push('b','Hello','',None,None,.4);self.assertEqual([x['rid'] for x in out],['a','b'])
 def test_timeout_then_new_sentence_not_merged(self):
  b=ClauseBuffer();b.push('a','','실험은?',None,None,0)
  out=b.push('b','','감사합니다.',None,None,2);self.assertEqual(len(out),2)
 def test_reset_drops_old_session(self):
  b=ClauseBuffer();b.push('a','','실험은?',None,None,0);b.reset();self.assertIsNone(b.held)

 def test_conversational_questions_not_forced_to_statement(self):
  self.assertEqual(speech_act('사용해도 돼요?'),'unknown')
  self.assertEqual(normalize_source('효과가 있어요?'),'효과가 있어요?')
