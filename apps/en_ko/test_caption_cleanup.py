import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app import MainWindow
from caption_cleanup import clean_fillers, clean_sources, idle_due
APP=QApplication.instance() or QApplication([])
class CleanupTests(unittest.TestCase):
 def test_only_fillers(self):
  for s in ['어.. 음.. 아..','Uh, um...','음','아!']:
   self.assertEqual(clean_fillers(s),'')
  self.assertEqual(clean_sources('Oh.','어..'),('',''))
 def test_normal_words_preserved(self):
  for s in ['아연과 음성 분석 및 어류 연구','umbrella and human albumin','We are uncertain whether it works.']:
   self.assertEqual(clean_fillers(s),s)
 def test_embedded_filler(self):
  self.assertEqual(clean_fillers('음, 아연을 어 분석했습니다.'),'아연을 분석했습니다.')
  self.assertEqual(clean_fillers('Um, we uh found activity.'),'we found activity.')
 def test_idle_deadlines(self):
  self.assertFalse(idle_due(14.9,10,8,False))
  self.assertTrue(idle_due(15,10,8,False))
  self.assertFalse(idle_due(20,10,18,False))
  self.assertFalse(idle_due(20,10,8,True))
  self.assertFalse(idle_due(20,10,8,False,21))
 def test_overlay_clears_history_and_resumes(self):
  w=MainWindow(warmup=False)
  try:
   w.overlay.rollup=True;w.overlay.advance_text('Old sentence');w.overlay.advance_text('Last sentence')
   w.last_activity=10;w.queue.shown_at=11;w.queue.next_at=12
   with patch('app.time.monotonic',return_value=16):w.expire_idle_caption()
   self.assertFalse(w.overlay.current_text);self.assertFalse(w.overlay.history_rows)
   w.overlay.advance_text('New sentence');self.assertEqual(w.overlay.history_rows,['New sentence'])
  finally:w.close()
 def test_pending_translation_prevents_clear(self):
  w=MainWindow(warmup=False)
  try:
   w.overlay.advance_text('Still reading');w.last_activity=1;w.queue.shown_at=1
   w.context.pending[0]={'ready':False}
   with patch('app.time.monotonic',return_value=20):w.expire_idle_caption()
   self.assertEqual(w.overlay.current_text,'Still reading')
   w.context.pending.clear()
  finally:w.close()
 def test_filler_does_not_trigger_translation(self):
  w=MainWindow(warmup=False)
  try:
   with patch.object(w.context,'run_job') as job:
    w.context.translate('f','Oh','어... 음...',lambda *args:self.fail('filler delivered'))
    job.assert_not_called()
  finally:w.close()
if __name__=='__main__':unittest.main()
