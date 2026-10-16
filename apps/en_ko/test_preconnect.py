import unittest,threading
from types import SimpleNamespace
from unittest.mock import Mock,patch
import azure.cognitiveservices.speech as sdk
from app import SpeechWorker
from test_app import FakeRecognizer,APP
class PreconnectTests(unittest.TestCase):
 def test_worker_reuses_prepared_recognizer_and_closes_it(self):
  r=FakeRecognizer();connection=SimpleNamespace(recognizer=r,audio=object(),connected=threading.Event(),close=Mock())
  connection.connected.set();w=SpeechWorker('fake','koreacentral',500,prepared=connection)
  with patch.object(sdk,'SpeechConfig'),patch.object(sdk.audio,'AudioConfig') as audio,patch.object(sdk.PhraseListGrammar,'from_recognizer'),patch.object(sdk,'SpeechRecognizer') as constructor:
   w.run();APP.processEvents();constructor.assert_not_called();audio.assert_not_called()
  self.assertTrue(r.stopped);connection.close.assert_called_once();self.assertIsNone(w.prepared_speech)
 def test_open_waits_for_connection_event(self):
  from speech_connection import PreparedSpeech
  with patch('speech_connection.make_config',return_value=(Mock(),Mock())),patch.object(sdk.audio,'AudioConfig'),patch.object(sdk,'SpeechRecognizer'),patch.object(sdk.Connection,'from_recognizer') as get:
   resource=PreparedSpeech('fake','koreacentral',500)
   get.return_value.open.side_effect=lambda _:resource.connected.set()
   self.assertTrue(resource.open());get.return_value.open.assert_called_once_with(True)
   resource.close();get.return_value.close.assert_called_once()

 def test_fixed_language_avoids_auto_detection(self):
  from speech_connection import make_config
  config,language=make_config('fake','koreacentral',500,'ko-KR')
  self.assertIsNone(language);self.assertEqual(config.speech_recognition_language,'ko-KR')
  config,language=make_config('fake','koreacentral',500,'en-US')
  self.assertIsNone(language);self.assertEqual(config.speech_recognition_language,'en-US')
  config,language=make_config('fake','koreacentral',500)
  self.assertIsNotNone(language)

 def test_source_language_remains_automatic(self):
  from app import MainWindow
  w=MainWindow(warmup=False)
  self.assertFalse(hasattr(w,'source_language'))
  self.assertEqual(w.output_language.count(),2)
  w.close()
