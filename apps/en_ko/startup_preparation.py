"""Preconnect the actual Speech recognizer; recognition starts only on user action."""
from PySide6.QtCore import QThread, Signal
from speech_connection import PreparedSpeech
class PreparationWorker(QThread):
    speech_prepared = Signal(object)
    completed = Signal(object)
    def __init__(self, region, translate, args, parent=None, key='', silence_ms=500, source_language='auto'):
        super().__init__(parent)
        self.region, self.translate, self.args = region, translate, args
        self.source_language = source_language
        self.key, self.silence_ms, self.speech = key, silence_ms, None
    def run(self):
        result = {'speech': False, 'model': False}
        try:
            self.speech = PreparedSpeech(self.key, self.region, self.silence_ms, source_language=self.source_language)
            result['speech'] = self.speech.open()
        except Exception:
            if self.speech:self.speech.close()
            self.speech = None
        resource,self.speech=self.speech,None
        if resource:self.speech_prepared.emit(resource)
        try:
            self.translate(*self.args)
            result['model'] = True
        except Exception:pass
        self.key = '';self.args = ()
        self.completed.emit(result)
