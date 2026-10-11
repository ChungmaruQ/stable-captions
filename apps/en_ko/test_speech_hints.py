import unittest
from unittest.mock import Mock
from speech_hints import build_hints
from app import SpeechWorker
class HintsTests(unittest.TestCase):
 def test_event_and_slide(self):
  hints=build_hints('RIPK1 ubiquitination\nNovelKinaseXYZ')
  self.assertNotIn('동국대학교',hints);self.assertIn('NovelKinaseXYZ',hints);self.assertLessEqual(len(hints),220)
 def test_disable_documents_and_clear_slide(self):
  self.assertEqual(build_hints('',documents=False),[])
  self.assertNotIn('NovelKinaseXYZ',build_hints())
 def test_bounded_and_safe(self):
  x=build_hints('fuck\n'+' '.join('Protein'+str(i) for i in range(1000)))
  self.assertNotIn('fuck',x);self.assertLessEqual(len(x),220)
 def test_replaces_and_coalesces(self):
  w=SpeechWorker('fake','region',500);g=Mock()
  w.set_hints(['old']);w.set_hints(['new']);w.apply_hints(g)
  g.clear.assert_called_once();g.addPhrase.assert_called_once_with('new')
  w.apply_hints(g);self.assertEqual(g.clear.call_count,1)
  w.set_hints([]);w.apply_hints(g);self.assertEqual(g.clear.call_count,2)
