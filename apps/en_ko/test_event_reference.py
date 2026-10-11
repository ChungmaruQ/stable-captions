import unittest
from event_data import EVENT_DATA
from event_reference import reference_for
from speech_hints import build_hints
class GenericReferenceTests(unittest.TestCase):
 def test_no_event_or_default_hints(self):
  self.assertEqual(EVENT_DATA,{'profiles':[],'common':'','event':''})
  self.assertEqual(reference_for('회의입니다.','This is a meeting.'),'')
  self.assertEqual(build_hints(),[])
 def test_live_slide_hints_remain_available(self):
  self.assertIn('NovelKinaseXYZ',build_hints('NovelKinaseXYZ'))
