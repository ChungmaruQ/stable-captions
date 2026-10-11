import unittest
from caption_safety import flagged,protect_caption,OMITTED
class GuardTests(unittest.TestCase):
 def test_variants_are_hidden(self):
  for text in ['fuck','FUCKING','f.u.c.k','f\u200buck','ｆｕｃｋ','sh1t','bullshit','bitch','blowjob','pornography','씨발','씨 발','개새끼','ㅅㅂ','****']:
   self.assertTrue(flagged(text),text)
   self.assertEqual(protect_caption('The source says '+text)[0],OMITTED)
 def test_scientific_terms_not_substring_filtered(self):
  for text in ['The assay measures sex hormones and breast cancer markers.', 'Analysis of renal and anal tissue.', 'Association with classical pharmacology.', 'Scunthorpe research team.', 'Cockayne syndrome is a rare disorder.','시발점에서 시작한 분석입니다.','이 약을 씹어서 복용합니다.']:
   self.assertFalse(flagged(text),text)
 def test_source_flags_safe_sounding_translation(self):
  self.assertTrue(protect_caption('An ordinary sentence.','씨발')[2])
 def test_history_and_overlay_guard_all_delivery_paths(self):
  from test_app import APP
  from app import MainWindow
  w=MainWindow(warmup=False)
  w.deliver(w.session_number,'direct','An asshole.','')
  w.tick()
  self.assertNotIn('asshole',w.history.toPlainText())
  self.assertNotIn('asshole',w.overlay.label.text())
  self.assertIn(OMITTED,' '.join(w.overlay.label.text().split()))
  w.clear();w.context.use_translation.setChecked(False)
  w.receive(w.session_number,'fallback','This is shit.','')
  w.tick();self.assertIn(OMITTED,' '.join(w.overlay.label.text().split()))
  self.assertFalse(w.context.jobs);w.close()
 def test_medical_deliver_keeps_content(self):
  en='Breast cancer can affect sex hormone levels.'
  self.assertEqual(protect_caption(en),(en,'',False))
