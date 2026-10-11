import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app import MainWindow
from output_language import has_hangul,route_source
from slide_context import ServiceError
APP=QApplication.instance() or QApplication([])
class OutputLanguageTests(unittest.TestCase):
 def setUp(self):
  self.w=MainWindow(warmup=False);self.c=self.w.context
  self.c.use_documents.setChecked(False);self.c.use_speculation.setChecked(False)
 def tearDown(self):self.c.reset();self.w.close()
 def test_unicode_and_scientific_english(self):
  for s in ['한국어','한글','ㄱ','activity 활성']:self.assertTrue(has_hangul(s))
  self.assertFalse(has_hangul('β-carotene, IC₅₀ = 10 µM'))
 def test_misclassified_english_reroutes_to_translation(self):
  jobs=[];out=[]
  with patch.object(self.c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))):
   self.c.translate_unit('x','이 안에 어떤 성분이 있는지','',lambda *v:out.append(v))
   self.assertEqual(len(jobs),1);self.assertFalse(out)
   jobs[0][1]((True,'Which components it contains'))
   self.assertEqual(out[0][1],'Which components it contains')
 def test_timeout_never_falls_back_to_korean(self):
  jobs=[];out=[]
  with patch.object(self.c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))):
   self.c.translate_unit('x','어떤 성분이 있는지','',lambda *v:out.append(v))
   jobs[0][1]((False,''));self.assertFalse(out)
 def test_invalid_model_result_keeps_valid_english_baseline(self):
  self.c.active=True;self.c.text='slide';self.c.use_translation.setChecked(True);jobs=[];out=[]
  with patch.object(self.c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))):
   self.c.translate_unit('x','Biological activity','생리 활성',lambda *v:out.append(v))
   jobs[0][1]((True,'생리 활성'));self.assertEqual(out[0][1],'Biological activity')
 def test_invalid_model_retries_once(self):
  with patch('context_ui.translate_with_context',side_effect=['한글','English']) as f:
   self.assertEqual(self.c.request_translation(()),'English');self.assertEqual(f.call_count,2)
  with patch('context_ui.translate_with_context',return_value='한글') as f:
   with self.assertRaises(ServiceError):self.c.request_translation(())
   self.assertEqual(f.call_count,2)
 def test_final_display_gate(self):
  with patch.object(self.w.queue,'accept') as accept:
   self.w.deliver(self.w.session_number,'x','이 안에 어떤 컴포넌트가','')
   accept.assert_not_called()
 def test_english_bypass_preserved(self):
  out=[]
  with patch.object(self.c,'run_job') as job:
   self.c.translate_unit('x','Natural products and β-carotene','',lambda *v:out.append(v))
   job.assert_not_called();self.assertEqual(out[0][1],'Natural products and β-carotene')
if __name__=='__main__':unittest.main()
