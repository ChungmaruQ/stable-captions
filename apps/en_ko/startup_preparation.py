"""Preconnect the actual Speech recognizer; recognition starts only on user action."""
from PySide6.QtCore import QThread, Signal
from speech_connection import PreparedSpeech
class PreparationWorker(QThread):
    completed = Signal(object)
    def __init__(self, region, translate, args, parent=None, key='', silence_ms=500):
        super().__init__(parent)
        self.region, self.translate, self.args = region, translate, args
        self.key, self.silence_ms, self.speech = key, silence_ms, None
    def run(self):
        result = {'speech': False, 'model': False}
        try:
            self.speech = PreparedSpeech(self.key, self.region, self.silence_ms)
            result['speech'] = self.speech.open()
        except Exception:
            if self.speech:self.speech.close()
            self.speech = None
        try:
            self.translate(*self.args)
            result['model'] = True
        except Exception:pass
        self.key = '';self.args = ()
        self.completed.emit(result)
