import unittest
from model_options import generation_options
class ModelOptionsTests(unittest.TestCase):
 def test_luna_disables_reasoning_and_uses_supported_token_parameter(self):
  self.assertEqual(generation_options('gpt-6-luna',1600,400),{'max_completion_tokens':1600,'reasoning_effort':'none'})
 def test_existing_deployments_keep_their_settings(self):
  self.assertEqual(generation_options('gpt-5-mini')['reasoning_effort'],'minimal')
  self.assertEqual(generation_options('gpt-4.1-mini'),{'max_tokens':400,'temperature':0})
