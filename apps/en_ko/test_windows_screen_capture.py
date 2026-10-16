import unittest
from unittest.mock import Mock,patch
from windows_screen_capture import capture_screen,CaptureError
class WindowsCaptureTests(unittest.TestCase):
 def test_affinity_restored_after_capture_failure(self):
  user=Mock();dwm=Mock();user.GetWindowDisplayAffinity.return_value=True;user.SetWindowDisplayAffinity.return_value=True
  widget=Mock();widget.isVisible.return_value=True;widget.isMinimized.return_value=False;widget.winId.return_value=123
  screen=Mock();screen.grabWindow.side_effect=RuntimeError('capture failed')
  with patch('windows_screen_capture._apis',return_value=(user,dwm)):
   with self.assertRaises(RuntimeError):capture_screen(screen,[widget])
  self.assertEqual(user.SetWindowDisplayAffinity.call_args_list[0].args,(123,0x11));self.assertEqual(user.SetWindowDisplayAffinity.call_args_list[-1].args,(123,0))
 def test_hidden_controls_not_changed(self):
  user=Mock();dwm=Mock();widget=Mock();widget.isVisible.return_value=False
  screen=Mock();screen.grabWindow.return_value.toImage.return_value.isNull.return_value=False
  with patch('windows_screen_capture._apis',return_value=(user,dwm)):capture_screen(screen,[widget])
  user.SetWindowDisplayAffinity.assert_not_called()
