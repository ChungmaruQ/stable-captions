import unittest
from types import SimpleNamespace
from unittest.mock import patch
import threading
from PySide6.QtWidgets import QApplication
from app import MainWindow
from startup_preparation import PreparationWorker
APP = QApplication.instance() or QApplication([])
class PreparationTests(unittest.TestCase):
    def test_preparation_opens_real_connection_without_recognition(self):
        with patch('startup_preparation.PreparedSpeech') as prepared:
            prepared.return_value.open.return_value=True
            translate = unittest.mock.Mock(return_value='Hello')
            worker=PreparationWorker('koreacentral',translate,('synthetic',),key='test',silence_ms=500)
            result=[];worker.completed.connect(result.append);worker.run()
            prepared.assert_called_once_with('test','koreacentral',500)
            prepared.return_value.open.assert_called_once()
            prepared.return_value.recognizer.start_continuous_recognition_async.assert_not_called()
            self.assertEqual(result,[{'speech':True,'model':True}])
            self.assertEqual(worker.args,())
    def test_ready_only_current_active_session(self):
        w=MainWindow(warmup=False)
        w.session_number=3
        w.worker=SimpleNamespace(stop_event=threading.Event())
        w.speech_ready(2);self.assertNotIn('말씀하세요',w.ready_label.text())
        w.speech_ready(3);self.assertEqual(w.ready_label.text(),'준비 완료 · 말씀하세요')
        w.prepared({'speech':True,'model':True});self.assertEqual(w.ready_label.text(),'준비 완료 · 말씀하세요')
        w.worker.stop_event.set();w.ready_label.setText('중지');w.speech_ready(3);self.assertEqual(w.ready_label.text(),'중지')
        w.worker=None;w.close()
    def test_failed_preparation_does_not_claim_ready(self):
        w=MainWindow(warmup=False);w.prepared({'speech':True,'model':False})
        self.assertNotIn('준비 완료',w.ready_label.text());self.assertTrue(w.start_button.isEnabled());w.close()
