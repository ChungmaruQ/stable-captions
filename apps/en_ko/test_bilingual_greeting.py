import unittest
from event_reference import PROFILES,reference_for,prepared_translation_for
class GenericReferenceTests(unittest.TestCase):
 def test_no_bundled_speech(self):
  self.assertEqual(PROFILES,[])
  self.assertEqual(reference_for('환영합니다','Welcome'), '')
  self.assertIsNone(prepared_translation_for('환영합니다'))
