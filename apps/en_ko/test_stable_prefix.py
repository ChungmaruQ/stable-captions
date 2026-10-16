import unittest
from stable_prefix import StablePrefix,norm
class StablePrefixTests(unittest.TestCase):
 def observe(self,p,text,lang='en-US'):
  result=None
  for t in [0,1,4]:result=p.observe('u',text,lang,t) or result
  return result
 def test_english_no_replay_and_no_lost_tail(self):
  p=StablePrefix();text='we study natural products and their biological activities because they may offer new approaches to treatment'
  result=self.observe(p,text);self.assertIsNotNone(result)
  suffix,early,ok=p.finish('u','We study natural products and their biological activities because they may offer new approaches to treatment.')
  self.assertTrue(early and ok);self.assertEqual(norm(result[1]+suffix),norm(text))
  self.assertIsNone(p.observe('u',text,'en-US',8))
 def test_unstable_text_is_not_shown(self):
  p=StablePrefix()
  self.assertIsNone(p.observe('u','we study new drugs for cancer with researchers today','en-US',0))
  self.assertIsNone(p.observe('u','the study did not show clinical efficacy in patients','en-US',1))
  self.assertIsNone(p.observe('u','no conclusion can be drawn from the results yet','en-US',4))
 def test_korean_complete_clause(self):
  p=StablePrefix();text='오늘 발표에 참석하신 여러분을 진심으로 환영합니다 우리는 새로운 치료 방법을 연구하고 있습니다'
  r=self.observe(p,text,'ko-KR');self.assertIsNotNone(r);self.assertTrue(r[1].endswith('환영합니다'))
  tail,early,ok=p.finish('u',text+'.');self.assertTrue(ok);self.assertEqual(norm(r[1]+tail),norm(text))
 def test_final_casing_punctuation_and_spacing(self):
  p=StablePrefix();text='we work with the university of california san diego and the school of pharmacy on drug discovery'
  r=self.observe(p,text);tail,_,ok=p.finish('u','We work with the University of California, San Diego and the School of Pharmacy on drug discovery.')
  self.assertTrue(ok);self.assertEqual(norm(r[1]+tail),norm(text))
 def test_rewrite_fails_closed_without_duplicate_caption(self):
  p=StablePrefix();self.observe(p,'we study natural products and their biological activities because they may offer new approaches to treatment')
  self.assertEqual(p.finish('u','A completely unrelated result.'),('',True,False))
 def test_short_final_passes_unchanged(self):
  p=StablePrefix();p.observe('u','thank you','en-US',0)
  self.assertEqual(p.finish('u','Thank you.'),('Thank you.',False,True))

 def test_two_observations_accept_complete_korean(self):
  p=StablePrefix();text='오늘 발표에 참석하신 여러분을 진심으로 환영합니다 다음 발표를 시작하겠습니다'
  self.assertIsNone(p.observe('u',text,'ko-KR',0))
  r=p.observe('u',text,'ko-KR',.31)
  self.assertIsNotNone(r);self.assertTrue(r[1].endswith('환영합니다'))
 def test_two_observations_too_close_wait(self):
  p=StablePrefix();text='오늘 발표에 참석하신 여러분을 진심으로 환영합니다 다음 발표를 시작하겠습니다'
  p.observe('u',text,'ko-KR',0)
  self.assertIsNone(p.observe('u',text,'ko-KR',.1))
 def test_negation_tail_not_committed(self):
  p=StablePrefix();text='we found that the treatment in this experiment did not'
  p.observe('u',text,'en-US',0);r=p.observe('u',text,'en-US',3)
  self.assertTrue(r is None or ('did' not in r[1] and 'not' not in r[1]))

 def test_pair_protected_across_trailing_hold(self):
  p=StablePrefix();text='today we discuss the major role of oceanography and pharmaceutical sciences here'
  p.observe('u',text,'en-US',0);r=p.observe('u',text,'en-US',3)
  self.assertTrue(r is None or not r[1].endswith('pharmaceutical'))
 def test_no_dangling_preposition(self):
  p=StablePrefix();text='we have half of our appointment at the university of california san diego in the school of pharmacy'
  p.observe('u',text,'en-US',0);r=p.observe('u',text,'en-US',3)
  self.assertTrue(r is None or r[1].split()[-1] not in {'at','of','in','the'})

 def test_frequent_callbacks_do_not_starve_stable_greeting(self):
  p=StablePrefix();results=[]
  for t in [0,.1,.2,.31]:
   r=p.observe('u','안녕하세요','ko-KR',t)
   if r:results.append(r)
  self.assertEqual(len(results),1);self.assertEqual(results[0][1],'안녕하세요')

 def test_intervening_rewrite_resets_common_prefix(self):
  p=StablePrefix()
  for t,text in [(0,'안녕하세요'),(.1,'안녕하십니까'),(.2,'안녕하세요'),(.31,'안녕하세요')]:
   self.assertIsNone(p.observe('u',text,'ko-KR',t))
  self.assertIsNotNone(p.observe('u','안녕하세요','ko-KR',.51))

 def test_complete_first_statement_without_following_words(self):
  p=StablePrefix();text='오늘 발표에 참석하신 여러분을 진심으로 환영합니다'
  p.observe('u',text,'ko-KR',0);r=p.observe('u',text,'ko-KR',.31)
  self.assertEqual(r[1],text)
  self.assertEqual(p.finish('u',text+'.'),('',True,True))

 def test_incomplete_first_statement_still_waits(self):
  p=StablePrefix();text='오늘 발표에서는 이 치료가 효과가 있는지'
  p.observe('u',text,'ko-KR',0)
  self.assertIsNone(p.observe('u',text,'ko-KR',.31))

 def test_first_english_clause_earlier_but_keeps_tail(self):
  p=StablePrefix();text='we study natural products and their biological activities because they may offer new approaches to treatment'
  p.observe('u',text,'en-US',0);r=p.observe('u',text,'en-US',1.3)
  self.assertIsNotNone(r)
  tail,early,ok=p.finish('u',text);self.assertTrue(early and ok)
  self.assertEqual(norm(r[1]+tail),norm(text))
