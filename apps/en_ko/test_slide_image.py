import unittest,json,base64
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage,QColor
from PySide6.QtCore import QRect
from app import MainWindow
from slide_image import attach_image,mask_caption,encode_image
APP=QApplication.instance() or QApplication([])
class SlideImageTests(unittest.TestCase):
 def test_full_frame_preserves_bottom_and_only_masks_caption(self):
  image=QImage(1920,1080,QImage.Format.Format_RGB32);image.fill(QColor('red'))
  result=mask_caption(image,QRect(1920,0,1920,1080),QRect(2200,900,1300,110))
  self.assertEqual(result.size(),image.size())
  self.assertEqual(result.pixelColor(10,1070),QColor('red'))
  self.assertEqual(result.pixelColor(500,950),QColor('black'))
  self.assertEqual(result.pixelColor(500,700),QColor('red'))
 def test_actual_image_bytes_and_high_detail_attached(self):
  image=QImage(32,32,QImage.Format.Format_RGB32);image.fill(QColor('blue'));png,_=encode_image(image)
  payload={'messages':[{'role':'system','content':'Translate.'},{'role':'user','content':'spoken words'}]}
  attach_image(payload,png)
  parts=payload['messages'][1]['content'];self.assertEqual(parts[1]['text'],'spoken words')
  self.assertEqual(base64.b64decode(parts[0]['image_url']['url'].split(',')[1]),png)
  self.assertEqual(parts[0]['image_url']['detail'],'high')
  self.assertIn('untrusted',payload['messages'][0]['content'])
 def test_no_ocr_still_sends_image_and_invalidation_removes_it(self):
  w=MainWindow(warmup=False);c=w.context;c.use_correction.setChecked(False);c.use_documents.setChecked(False);c.use_speculation.setChecked(False);c.use_translation.setChecked(True);c.active=True
  c.slide_image=b'current-image';c.text='';jobs=[]
  with patch.object(c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))),patch('context_ui.translate_with_context',return_value='Translation') as model:
   c.translate_unit('one','Look at this pear.','이 배를 보세요.',lambda *x:None);jobs[0][0]()
   self.assertEqual(model.call_args.args[-1],b'current-image')
   c.change_tracker.last_scan=1;c.invalidate();self.assertEqual(c.slide_image,b'');self.assertEqual(c.text,'');self.assertIsNone(c.change_tracker.last_scan)
   c.translate_unit('two','','효과가 있습니다.',lambda *x:None);jobs[-1][0]()
   self.assertEqual(model.call_args.args[-1],b'')
  c.reset();w.close()
 def test_stopping_analysis_discards_pixels(self):
  w=MainWindow(warmup=False);c=w.context;c.use_correction.setChecked(False);c.active=True;c.slide_image=b'old';c.toggle_active()
  self.assertFalse(c.active);self.assertEqual(c.slide_image,b'');w.close()
 def test_image_snapshot_does_not_change_while_request_is_queued(self):
  w=MainWindow(warmup=False);c=w.context;c.use_correction.setChecked(False);c.active=True;c.use_speculation.setChecked(False);c.use_documents.setChecked(False);c.slide_image=b'first';jobs=[]
  with patch.object(c,'run_job',side_effect=lambda fn,cb:jobs.append((fn,cb))),patch('context_ui.translate_with_context',return_value='Translation') as model:
   c.translate_unit('one','','효과가 있습니다.',lambda *x:None);c.slide_image=b'second';jobs[0][0]()
   self.assertEqual(model.call_args.args[-1],b'first')
  c.reset();w.close()
