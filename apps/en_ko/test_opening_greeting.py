import unittest
from stable_prefix import StablePrefix,norm
from opening_greeting import exact_translation
class OpeningTests(unittest.TestCase):
 def test_asr_spacing_variants(self):
  p=StablePrefix();s='존경하는 내외귀빈 여러분 그리고 일본에서'
  p.observe('u',s,'ko-KR',0);r=p.observe('u',s,'ko-KR',.31)
  self.assertEqual(exact_translation(r[1]),'Distinguished guests,')
 def test_short_greeting_without_lookahead(self):
  p=StablePrefix();self.assertIsNone(p.observe('u','안녕하세요','ko-KR',0))
  r=p.observe('u','안녕하세요','ko-KR',.31)
  self.assertEqual(r[1],'안녕하세요');self.assertEqual(exact_translation(r[1]),'Hello.')
  self.assertEqual(p.finish('u','안녕하세요.'),('',True,True))
 def test_address_keeps_later_speech(self):
  p=StablePrefix();s='존경하는 내외 귀빈 여러분 그리고 일본에서 오신 연사 여러분'
  p.observe('u',s,'ko-KR',0);r=p.observe('u',s,'ko-KR',.31)
  self.assertEqual(r[1],'존경하는 내외 귀빈 여러분')
  tail,_,ok=p.finish('u',s);self.assertTrue(ok);self.assertEqual(norm(r[1]+tail),norm(s))
 def test_unstable_or_incomplete_never_commits(self):
  for a,b in [('안녕','안녕하세요'),('안녕하세요','안녕하십니까'),('존경하는 내외 귀빈','존경하는 내외 귀빈 여러분')]:
   p=StablePrefix();p.observe('u',a,'ko-KR',0);self.assertIsNone(p.observe('u',b,'ko-KR',.31))
 def test_no_greeting_inside_other_speech(self):
  self.assertIsNone(exact_translation('안녕하세요 저는 김교수입니다'))
  p=StablePrefix();p.observe('u','그는 안녕하세요라고 말했습니다','ko-KR',0)
  self.assertIsNone(p.observe('u','그는 안녕하세요라고 말했습니다','ko-KR',.31))
 def test_fast_path_only_at_session_opening(self):
  p=StablePrefix();p.finish('first','처음 문장입니다.')
  p.observe('u','안녕하세요','ko-KR',0);self.assertIsNone(p.observe('u','안녕하세요','ko-KR',.31))
if __name__=='__main__':unittest.main()
