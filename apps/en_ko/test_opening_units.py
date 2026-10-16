import unittest
from stable_prefix import StablePrefix,norm
class OpeningUnitTests(unittest.TestCase):
 def test_short_complete_korean_opening(self):
  p=StablePrefix();text='발표를 시작하겠습니다'
  self.assertIsNone(p.observe('u',text,'ko-KR',0))
  self.assertEqual(p.observe('u',text,'ko-KR',.31)[1],text)
  self.assertEqual(p.finish('u',text+'.'),('',True,True))
 def test_first_short_english_unit_and_no_duplicate_tail(self):
  p=StablePrefix();first='scientific names identify organisms precisely'
  p.observe('u',first,'en-US',0)
  text=first+' a scientific name contains a genus name'
  result=p.observe('u',text,'en-US',.4)
  self.assertEqual(result[1],first)
  tail,early,ok=p.finish('u',text+'.')
  self.assertTrue(early and ok);self.assertEqual(norm(result[1]+tail),norm(text))
 def test_english_greeting(self):
  p=StablePrefix();p.observe('u','good morning everyone','en-US',0)
  self.assertEqual(p.observe('u','good morning everyone today','en-US',.4)[1],'good morning everyone')
 def test_incomplete_predicate_not_cut(self):
  for text in ['today we discuss mainly a treatment for cancer','we did not see any significant changes','we study natural products and drug discovery','치료 효과가 있을 수도 있지만','이 치료는 효과가 있습니다만']:
   p=StablePrefix();p.observe('u',text,'ko-KR' if '치료' in text else 'en-US',0)
   self.assertIsNone(p.observe('u',text,'ko-KR' if '치료' in text else 'en-US',.4))
 def test_shortcut_only_first_unit(self):
  p=StablePrefix();p.finish('first','earlier source')
  p.observe('u','good morning everyone','en-US',0)
  self.assertIsNone(p.observe('u','good morning everyone','en-US',.4))
 def test_language_can_change_between_utterances(self):
  p=StablePrefix();p.observe('ko','발표를 시작하겠습니다','ko-KR',0)
  r=p.observe('ko','발표를 시작하겠습니다','ko-KR',.4);self.assertTrue(r[2])
  p.finish('ko','발표를 시작하겠습니다.')
  text='we study natural products and their biological activities because they may offer new approaches to treatment'
  p.observe('en',text,'en-US',1)
  r=p.observe('en',text,'en-US',4);self.assertIsNotNone(r);self.assertFalse(r[2])
