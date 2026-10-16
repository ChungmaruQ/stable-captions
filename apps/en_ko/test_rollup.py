import os,unittest
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from PySide6.QtGui import QFontMetrics
from app import Overlay,MainWindow
class Display:
 def geometry(self):return QRect(0,0,1920,1080)
APP=QApplication.instance() or QApplication([])
class RollupTests(unittest.TestCase):
 def test_fixed_panel_and_sentence_order(self):
  o=Overlay();o.rollup=True;o.arrange(Display(),32,0);rect=o.geometry()
  old_height=3*(2*(QFontMetrics(o.label.font()).lineSpacing()+6)+12)+24
  self.assertLessEqual(rect.height(),old_height/2)
  for text in ['First sentence.','The second sentence.','Third sentence.','Fourth sentence.']:
   o.advance_text(text);self.assertEqual(o.geometry(),rect)
  self.assertNotIn('First',o.label.text());self.assertIn('second',o.label.text())
  self.assertTrue(o.label.text().endswith('Fourth sentence.'))
  self.assertEqual(o.label.slots,3);self.assertLessEqual(len(o.label.text().splitlines()),3)
  o.animate(.5);self.assertEqual(o.label.progress,.5);o.finish_animation();self.assertEqual(len(o.label.entries),3)
  before=o.label.text();o.arrange(Display(),32,0);self.assertEqual(o.label.text(),before)
  o.reset_text();self.assertEqual(o.label.text(),'');self.assertEqual(o.geometry(),rect);o.close()
 def test_long_sentence_preserves_words_and_font(self):
  o=Overlay();o.rollup=True;o.arrange(Display(),32,0)
  text='A long technical sentence with many words '*30
  pages=o.pages(text);self.assertGreater(len(pages),1)
  self.assertEqual(' '.join(' '.join(pages).split()),' '.join(text.split()))
  rect=o.geometry()
  for page in pages:
   o.advance_text(page);self.assertEqual(o.geometry(),rect);self.assertEqual(o.label.font().pointSize(),32)
  o.close()
 def test_default_and_clear(self):
  w=MainWindow(warmup=False);self.assertEqual(w.caption_mode.currentIndex(),2)
  w.overlay.advance_text('Old');w.overlay.advance_text('New');w.clear()
  self.assertFalse(w.overlay.history_rows);w.close()

 def test_two_row_history_is_lossless_and_keeps_two_line_height(self):
  w=MainWindow(warmup=False);height=w.overlay.height();w.caption_mode.setCurrentIndex(3)
  o=w.overlay;self.assertTrue(o.rollup);self.assertFalse(o.two_line);self.assertEqual(o.height(),height)
  text='This sentence remains complete while its long content is divided into readable rows. '*12
  pages=o.pages(text);self.assertEqual(' '.join(pages),' '.join(text.split()))
  for page in pages:
   o.advance_text(page);self.assertEqual(o.height(),height);self.assertEqual(o.label.slots,2)
  o.animation.stop();o.finish_animation();self.assertEqual(o.label.entries,pages[-2:])
  self.assertTrue(o.label.dim_history);o.reset_text();self.assertFalse(o.label.entries)
  w.caption_mode.setCurrentIndex(1);self.assertEqual(o.label.slots,3)
  w.caption_mode.setCurrentIndex(2);self.assertFalse(o.rollup);self.assertEqual(o.label.slots,2);w.close()
