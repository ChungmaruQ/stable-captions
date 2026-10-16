"""Offline GUI and worker tests. No real key, microphone, or Azure calls."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import azure.cognitiveservices.speech as sdk
from PySide6.QtWidgets import QApplication
from app import MainWindow, SpeechWorker

APP = QApplication.instance() or QApplication([])


class Event:
    def __init__(self):
        self.callbacks = []
    def connect(self, callback):
        self.callbacks.append(callback)
    def emit(self, value):
        for callback in self.callbacks:
            callback(value)


class FakeRecognizer:
    instances = []
    def __init__(self, **kwargs):
        self.recognized = Event()
        self.recognizing = Event()
        self.canceled = Event()
        self.session_started = Event()
        self.session_stopped = Event()
        self.stopped = False
        self.kwargs = kwargs
        self.instances.append(self)
    def start_continuous_recognition_async(self):
        def run():
            self.session_started.emit(None)
            self.recognizing.emit(SimpleNamespace(result=SimpleNamespace(text='중간 발화입니다', offset=0, properties={})))
            self.recognized.emit(SimpleNamespace(result=SimpleNamespace(
                reason=sdk.ResultReason.RecognizedSpeech, result_id='r1', offset=0, duration=10000000,
                text='완료된 발화.',
                properties={sdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult:'ko-KR'})))
            self.session_stopped.emit(None)
        return SimpleNamespace(get=run)
    def stop_continuous_recognition_async(self):
        def stop():
            self.stopped = True
        return SimpleNamespace(get=stop)


class AppTests(unittest.TestCase):
    def test_worker_final_only_and_cleanup(self):
        results, errors, partials = [], [], []
        worker = SpeechWorker('fake-test-key', 'koreacentral', 800)
        worker.final.connect(lambda *args: results.append(args))
        worker.partial.connect(lambda *args: partials.append(args))
        worker.failed.connect(errors.append)
        with patch.object(sdk, 'SpeechConfig') as config, \
             patch.object(sdk.audio, 'AudioConfig'), \
             patch.object(sdk.PhraseListGrammar, 'from_recognizer'), \
             patch.object(sdk, 'SpeechRecognizer', FakeRecognizer):
            worker.start()
            self.assertTrue(worker.wait(3000))
            APP.processEvents()
            config.return_value.set_property.assert_any_call(sdk.PropertyId.SpeechServiceConnection_LanguageIdMode, 'Continuous')
            config.return_value.set_profanity.assert_called_once_with(sdk.ProfanityOption.Masked)
        self.assertEqual(results, [('0', '', '완료된 발화.')])
        self.assertEqual(errors, [])
        self.assertIn('auto_detect_source_language_config', FakeRecognizer.instances[-1].kwargs)
        self.assertTrue(FakeRecognizer.instances[-1].stopped)
        self.assertEqual(partials, [('0', '', '중간 발화입니다')])
        self.assertEqual(len(FakeRecognizer.instances[-1].recognizing.callbacks), 1)
        self.assertEqual(worker.key, '')

    def test_old_session_cannot_change_display(self):
        window = MainWindow(warmup=False)
        window.context.use_documents.setChecked(False)
        window.context.use_translation.setChecked(False)
        window.session_number = 2
        window.receive(1, 'old', 'stale caption', '')
        self.assertEqual(len(window.queue.pending), 0)
        window.receive(2, 'new', 'Final caption.', '확정')
        window.tick()
        self.assertEqual(window.overlay.label.text().replace('\n', ' '), 'Final caption.')
        window.receive(2, 'new', 'rewritten', '')
        window.tick()
        self.assertEqual(window.overlay.label.text().replace('\n', ' '), 'Final caption.')
        window.close()

    def test_errors_do_not_expose_key_or_raw_exception(self):
        worker = SpeechWorker('secret-value-test', 'koreacentral', 800)
        errors=[]
        worker.failed.connect(errors.append)
        with patch.object(sdk, 'SpeechConfig', side_effect=ValueError('secret-value-test')):
            worker.start()
            self.assertTrue(worker.wait(3000))
            APP.processEvents()
        self.assertEqual(len(errors), 1)
        self.assertNotIn('secret-value-test', errors[0])


if __name__ == '__main__':
    unittest.main()

class FixedReadingPanelTests(unittest.TestCase):
    def test_short_reading_never_expands_existing_panel(self):
        w=MainWindow(warmup=False);w.caption_mode.setCurrentIndex(1);w.readable.setChecked(False);before=w.overlay.geometry().getRect();w.readable.setChecked(True)
        text='The reason for using Latin is that, because Latin is a dead language, it is more likely to remain unchanged for future generations.'
        rows=w.overlay.pages(text)
        self.assertEqual(' '.join(rows),text)
        from PySide6.QtGui import QFontMetrics
        self.assertTrue(all(QFontMetrics(w.overlay.label.font()).horizontalAdvance(x)<=w.overlay.max_text_width for x in rows))
        for row in rows:
            w.overlay.advance_text(row)
            self.assertEqual(w.overlay.geometry().getRect(),before)
            self.assertEqual(w.overlay.label.slots,3)
        w.close()
