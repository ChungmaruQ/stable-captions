import unittest,threading
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtWidgets import QApplication
from app import MainWindow
APP=QApplication.instance() or QApplication([])
class StartupStatusTests(unittest.TestCase):
 def setUp(self):self.w=MainWindow(warmup=False)
 def tearDown(self):self.w.worker=None;self.w.context.reset();self.w.close()
 def test_placeholder_is_not_caption_history_and_does_not_grow_panel(self):
  w=self.w;w.caption_mode.setCurrentIndex(3);rect=w.overlay.geometry()
  w.show_startup_status('listening')
  self.assertEqual(w.overlay.label.text(),'Listening…')
  self.assertEqual(w.overlay.current_text,'');self.assertEqual(w.overlay.history_rows,[])
  self.assertEqual(w.history.toPlainText(),'');self.assertEqual(w.overlay.geometry(),rect)
  self.assertTrue(w.overlay.label.is_status)
  w.overlay.advance_text('First real caption.');w.overlay.advance_text('Next caption.')
  self.assertFalse(w.overlay.label.is_status)
  self.assertEqual(w.overlay.label.text(),'First real caption.\nNext caption.')
  self.assertNotIn('Listening',str(w.overlay.history_rows))
 def test_listening_only_after_current_session_is_ready(self):
  w=self.w;w.session_number=4;w.worker=SimpleNamespace(stop_event=threading.Event())
  w.show_startup_status('connecting');w.speech_ready(3)
  self.assertEqual(w.overlay.label.text(),'Connecting…')
  w.speech_ready(4);self.assertEqual(w.overlay.label.text(),'Listening…')
 def test_translation_then_real_caption_replaces_status(self):
  w=self.w;w.show_startup_status('listening')
  with patch.object(w.context,'translate'):
   w.receive(w.session_number,'first','','한국어 문장입니다.')
  self.assertEqual(w.overlay.label.text(),'Translating…')
  w.deliver(w.session_number,'first','This is a caption.','한국어 문장입니다.');w.tick()
  self.assertTrue(w.first_caption_shown);self.assertEqual(w.overlay.label.text(),'This is a caption.')
  self.assertEqual(w.overlay.history_rows,['This is a caption.'])
  w.overlay.reset_text();w.tick();self.assertEqual(w.overlay.label.text(),'')
 def test_language_and_stop_error_states(self):
  w=self.w;w.output_language.setCurrentIndex(1);w.show_startup_status('listening')
  self.assertEqual(w.overlay.label.text(),'듣는 중…')
  with patch.object(w.context,'translate'):
   w.receive(w.session_number,'first','Hello everyone.','')
  self.assertEqual(w.overlay.label.text(),'번역 중…')
  w.on_error('연결 오류');self.assertEqual(w.overlay.label.text(),'연결 오류')
  w.stop();self.assertEqual(w.overlay.label.text(),'');self.assertEqual(w.startup_status,'')
 def test_stale_callbacks_cannot_change_indicator(self):
  w=self.w;w.show_startup_status('listening')
  w.receive(w.session_number-1,'stale','','오래된 발화입니다.')
  self.assertEqual(w.overlay.label.text(),'Listening…')
 def test_failed_translation_returns_to_listening(self):
  w=self.w;w.worker=SimpleNamespace(stop_event=threading.Event())
  w.show_startup_status('translating');w.tick()
  self.assertEqual(w.overlay.label.text(),'Listening…')
 def test_new_status_never_replaces_real_caption(self):
  w=self.w;w.deliver(w.session_number,'first','A real caption.','');w.tick()
  w.show_startup_status('translating')
  self.assertEqual(w.overlay.label.text(),'A real caption.')

class IdleStatusTests(unittest.TestCase):
 def setUp(self):
  self.w=MainWindow(warmup=False);self.w.worker=SimpleNamespace(stop_event=threading.Event());self.w.speech_connected=True;self.w.last_activity=100
 def tearDown(self):self.w.worker=None;self.w.close()
 def test_ten_second_threshold_and_resume_without_caption_history(self):
  w=self.w;w.first_caption_shown=True;rect=w.overlay.geometry()
  with patch('app.time.monotonic',return_value=109.9):w.expire_idle_caption()
  self.assertEqual(w.overlay.label.text(),'')
  with patch('app.time.monotonic',return_value=110):w.expire_idle_caption()
  self.assertEqual(w.overlay.label.text(),'[대기 중]');self.assertTrue(w.overlay.label.is_status)
  self.assertEqual(w.overlay.history_rows,[]);self.assertEqual(w.history.toPlainText(),'');self.assertEqual(w.overlay.geometry(),rect)
  with patch('app.time.monotonic',return_value=111):w.speech_activity(w.session_number)
  self.assertEqual(w.overlay.label.text(),'');self.assertEqual(w.startup_status,'')
 def test_no_waiting_when_disconnected_or_translation_pending(self):
  w=self.w
  with patch('app.time.monotonic',return_value=120):
   w.speech_connected=False;w.expire_idle_caption();self.assertEqual(w.overlay.label.text(),'')
   w.speech_connected=True;w.context.pending[1]={'ready':False};w.expire_idle_caption();self.assertEqual(w.overlay.label.text(),'')
   w.context.pending.clear();w.expire_idle_caption();self.assertEqual(w.overlay.label.text(),'[대기 중]')
   w.worker.stop_event.set();w.expire_idle_caption();self.assertEqual(w.overlay.label.text(),'')
 def test_stale_activity_does_not_clear_waiting(self):
  w=self.w
  with patch('app.time.monotonic',return_value=110):w.expire_idle_caption();w.speech_activity(w.session_number-1)
  self.assertEqual(w.overlay.label.text(),'[대기 중]')
