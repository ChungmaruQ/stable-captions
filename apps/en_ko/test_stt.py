"""STT events have no translations field; both input languages must still route."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import azure.cognitiveservices.speech as sdk
from PySide6.QtWidgets import QApplication
from app import SpeechWorker
from speech_connection import make_config
APP=QApplication.instance() or QApplication([])
class Event:
    def __init__(self):self.callbacks=[]
    def connect(self,fn):self.callbacks.append(fn)
    def emit(self,value):
        for fn in self.callbacks:fn(value)
class Recognizer:
    def __init__(self,**kwargs):
        for name in ('recognized','recognizing','canceled','session_started','session_stopped'):setattr(self,name,Event())
    def start_continuous_recognition_async(self):
        def run():
            self.session_started.emit(None)
            for offset,language,text in [(0,'ko-KR','실험 결과가 일관됩니다.'),(10000000,'en-US','The results are consistent.')]:
                result=SimpleNamespace(text=text,offset=offset,duration=10000000,reason=sdk.ResultReason.RecognizedSpeech,properties={sdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult:language})
                self.recognizing.emit(SimpleNamespace(result=result))
                self.recognized.emit(SimpleNamespace(result=result))
            self.recognized.emit(SimpleNamespace(result=SimpleNamespace(reason=sdk.ResultReason.NoMatch)))
            self.session_stopped.emit(None)
        return SimpleNamespace(get=run)
    def stop_continuous_recognition_async(self):return SimpleNamespace(get=lambda:None)
class STTTests(unittest.TestCase):
    def test_auto_config_is_plain_stt_with_continuous_lid(self):
        config,language=make_config('fake','koreacentral',500)
        self.assertIsInstance(config,sdk.SpeechConfig)
        self.assertNotIsInstance(config,sdk.translation.SpeechTranslationConfig)
        self.assertIsNotNone(language)
        self.assertEqual(config.get_property(sdk.PropertyId.SpeechServiceConnection_LanguageIdMode),'Continuous')
    def test_bilingual_events_without_translation_property(self):
        worker=SpeechWorker('fake','koreacentral',500,early=False);rows=[];errors=[]
        worker.final.connect(lambda *row:rows.append(row));worker.failed.connect(errors.append)
        with patch.object(sdk,'SpeechRecognizer',Recognizer),patch.object(sdk.audio,'AudioConfig'),patch.object(sdk.PhraseListGrammar,'from_recognizer'),patch.object(sdk.translation,'TranslationRecognizer',side_effect=AssertionError('Translation service must not be used')):
            worker.run();APP.processEvents()
        self.assertEqual(errors,[])
        self.assertEqual(rows,[('0','','실험 결과가 일관됩니다.'),('10000000','The results are consistent.','')])
