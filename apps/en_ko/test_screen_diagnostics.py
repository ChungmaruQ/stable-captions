import json,tempfile,unittest,sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage,QColor,QPixmap
from test_app import APP
from app import MainWindow
import diagnostics
from slide_changes import SlideChangeTracker

class MetadataTests(unittest.TestCase):
 def tearDown(self):diagnostics.close()
 def test_file_never_contains_keys_or_payload(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=diagnostics.configure('EN-KO',tmp)
   diagnostics.record('capture_ready',capture_id=1,image_bytes=1234,key='SECRET',transcript='PRIVATE WORDS',image=b'PRIVATE PIXELS')
   text=p.read_text();self.assertIn('capture_ready',text)
   for secret in ('SECRET','PRIVATE WORDS','PRIVATE PIXELS'):self.assertNotIn(secret,text)
   self.assertEqual(json.loads(text.splitlines()[-1])['image_bytes'],1234)
   diagnostics.close()
 def test_request_metadata_counts_images_without_logging_them(self):
  payload={'response_format':{'json_schema':{'name':'transcript_edits'}},'messages':[{'content':[{'type':'image_url','image_url':{'url':'SECRET_IMAGE'}},{'type':'text','text':'PRIVATE WORDS'}]}]}
  m=diagnostics.request_metadata('https://test.openai.azure.com/openai/v1/chat/completions',payload)
  self.assertEqual(m,{'stage':'correction','image_count':1,'image_bytes':0})
 def test_failure_records_http_status_not_exception_text(self):
  import slide_context,requests
  response=Mock(status_code=401)
  response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=None)
  response.raise_for_status.side_effect=requests.HTTPError('SECRET_KEY and PRIVATE WORDS')
  session=Mock();session.request.return_value=response
  before=diagnostics.record('test_boundary')
  with patch('slide_context.acquire_session',return_value=session),patch('slide_context.release_session'):
   with self.assertRaises(slide_context.ServiceError):slide_context.request_json('https://test.openai.azure.com/openai/v1/chat/completions','SECRET_KEY',{'messages':[]})
  rows=diagnostics.entries_after(before)
  self.assertEqual(rows[-1]['event'],'request_failed');self.assertEqual(rows[-1]['status'],401)
  self.assertNotIn('SECRET_KEY',json.dumps(rows));self.assertNotIn('PRIVATE WORDS',json.dumps(rows))

class CaptureDiagnosticsTests(unittest.TestCase):
 def setUp(self):
  self.w=MainWindow(warmup=False);self.c=self.w.context;self.c.timer.stop();self.c.dispatch.stop();self.c.active=True;self.c.model_endpoint.setText('https://example.openai.azure.com');self.c.model_key.setText('dummy-model');self.c.deployment.setText('gpt-6-luna');self.c.vision_endpoint.setText('https://example.cognitiveservices.azure.com');self.c.vision_key.setText('dummy-vision')
 def tearDown(self):self.c.active=False;self.w.close()
 @unittest.skipUnless(sys.platform=='darwin','Mac native capture test')
 def test_permission_denied_is_explicit_and_does_not_capture(self):
  from mac_screen_capture import CapturePermissionError
  with patch('mac_screen_capture.MacScreenCapture.capture',side_effect=CapturePermissionError):
   self.c.capture()
  self.assertEqual(self.c.capture_state_code,'permission_denied');self.assertIn('권한',self.c.summary.text())
 def test_other_monitor_settings_do_not_pause_selected_screen(self):
  dialog=Mock();dialog.isVisible.return_value=True;dialog.isMinimized.return_value=False;dialog.frameGeometry.return_value=QRect(0,0,700,600)
  screen=Mock();screen.geometry.return_value=QRect(1920,0,1920,1080)
  with patch.object(self.c,'dialog',dialog):self.assertFalse(self.c.controls_cover(screen))
  screen.geometry.return_value=QRect(0,0,1920,1080)
  with patch.object(self.c,'dialog',dialog):self.assertTrue(self.c.controls_cover(screen))
 @unittest.skipUnless(sys.platform=='darwin','Mac native capture test')
 def test_settings_visible_do_not_stop_native_capture(self):
  image=QImage(160,90,QImage.Format.Format_RGB32);image.fill(QColor('white'))
  jobs=[]
  with patch.object(self.c,'controls_cover',return_value=True),patch('mac_screen_capture.MacScreenCapture.capture',return_value=image) as capture,patch.object(self.c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))),patch('context_ui.time.monotonic',side_effect=[0,1.1]):
   self.c.capture();self.c.capture()
  self.assertTrue(self.c.slide_image);self.assertEqual(self.c.capture_count,1)
  self.assertEqual(capture.call_args.args[1],(self.w,self.c.dialog,self.w.overlay))
  self.assertEqual(self.c.capture_state_code,'ready')
 def test_analysis_start_keeps_settings_open(self):
  self.c.active=False
  with patch.object(self.c.dialog,'hide') as hide,patch.object(self.w,'showMinimized') as minimize:
   self.c.toggle_active()
  hide.assert_not_called();minimize.assert_not_called();self.assertTrue(self.c.active)
 def test_vision_is_optional_and_image_is_kept(self):
  self.c.vision_key.clear();self.c.vision_endpoint.clear()
  image=QImage(160,90,QImage.Format.Format_RGB32);image.fill(QColor('white'))
  with patch('mac_screen_capture.MacScreenCapture.capture',return_value=image),patch('windows_screen_capture.capture_screen',return_value=image),patch.object(self.c,'run_job') as job,patch('context_ui.time.monotonic',side_effect=[0,1.1]):
   self.c.capture();self.c.capture()
  self.assertTrue(self.c.slide_image);job.assert_not_called();self.assertIn('Vision',self.c.status.text())
 def test_capture_exception_becomes_diagnostic(self):
  with patch.object(self.c,'capture_once',side_effect=ValueError('SECRET')):self.c.capture()
  self.assertEqual(self.c.capture_state_code,'capture_error')
  self.c.flush_diagnostics();self.assertNotIn('SECRET',self.c.diagnostics_view.toPlainText())
 def test_frame_to_ocr_to_ui_journal(self):
  image=QImage(160,90,QImage.Format.Format_RGB32);image.fill(QColor('white'))
  screen=Mock();screen.geometry.return_value=QRect(0,0,160,90);screen.grabWindow.return_value=QPixmap.fromImage(image)
  jobs=[]
  with patch('mac_screen_capture.MacScreenCapture.capture',return_value=image),patch('PySide6.QtWidgets.QApplication.screens',return_value=[screen]),patch.object(self.c,'controls_cover',return_value=False),patch.object(self.c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))),patch('context_ui.time.monotonic',side_effect=[0,1.1]):
   self.c.capture();self.c.capture()
  self.assertEqual(self.c.capture_count,1);self.assertTrue(self.c.slide_image)
  jobs[0][1]((True,'fixture OCR'))
  self.c.flush_diagnostics();log=self.c.diagnostics_view.toPlainText()
  self.assertIn('화면 이미지 준비',log);self.assertIn('OCR 완료',log)
  self.assertNotIn('fixture OCR',log);self.assertEqual(self.c.preview.toPlainText(),'fixture OCR')
 def test_continuous_motion_has_bounded_wait(self):
  tracker=SlideChangeTracker()
  for t in range(3):self.assertEqual(tracker.observe(bytes([t])*100,t),'changed')
  self.assertEqual(tracker.observe(bytes([3])*100,3),'scan');self.assertEqual(tracker.scan_reason,'motion')
  tracker.scanned(3)
  self.assertEqual(tracker.observe(bytes([4])*100,4),'changed')

class UsageTests(unittest.TestCase):
 def test_usage_keeps_all_billed_tokens_and_filters_content(self):
  result={'model':'gpt-6-luna-2026-09-22','choices':[{'text':'PRIVATE'}],'usage':{'prompt_tokens':3000,'completion_tokens':40,'total_tokens':3040,'prompt_tokens_details':{'cached_tokens':2000,'cache_write_tokens':100},'completion_tokens_details':{'reasoning_tokens':0}}}
  fields=diagnostics.response_usage(result)
  self.assertTrue(fields['usage_known']);self.assertEqual(fields['cached_tokens'],2000);self.assertEqual(fields['cache_write_tokens'],100)
  self.assertEqual(fields['completion_tokens'],40);self.assertNotIn('PRIVATE',str(fields))
 def test_missing_usage_is_unknown_not_zero(self):
  self.assertEqual(diagnostics.response_usage({}),{'usage_known':False})
 def test_actual_response_path_records_usage_once(self):
  import slide_context
  response=Mock(status_code=200,content=b'{}',headers={})
  response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=None)
  response.json.return_value={'usage':{'prompt_tokens':20,'completion_tokens':3}}
  session=Mock();session.request.return_value=response
  before=diagnostics.record('test_boundary')
  with patch('slide_context.acquire_session',return_value=session),patch('slide_context.release_session'):
   slide_context.request_json('https://test.openai.azure.com/openai/v1/chat/completions','SECRET',{})
  rows=[r for r in diagnostics.entries_after(before) if r['event']=='request_received']
  self.assertEqual(len(rows),1);self.assertEqual(rows[0]['prompt_tokens'],20);self.assertEqual(rows[0]['completion_tokens'],3)
