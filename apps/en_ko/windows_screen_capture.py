"""Temporarily exclude our controls during a Windows 10 2004+ screen grab."""
import ctypes
from ctypes import wintypes

class CaptureError(RuntimeError):pass

def _apis():
 user=ctypes.WinDLL('user32',use_last_error=True)
 user.SetWindowDisplayAffinity.argtypes=[wintypes.HWND,wintypes.DWORD];user.SetWindowDisplayAffinity.restype=wintypes.BOOL
 user.GetWindowDisplayAffinity.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)];user.GetWindowDisplayAffinity.restype=wintypes.BOOL
 dwm=ctypes.WinDLL('dwmapi');dwm.DwmFlush.argtypes=[];dwm.DwmFlush.restype=ctypes.c_long
 return user,dwm

def capture_screen(screen,widgets):
 user,dwm=_apis();changed=[]
 try:
  for widget in widgets:
   if not widget.isVisible() or widget.isMinimized():continue
   hwnd=int(widget.winId());previous=wintypes.DWORD()
   if not user.GetWindowDisplayAffinity(hwnd,ctypes.byref(previous)):raise CaptureError('Cannot read window capture state')
   if not user.SetWindowDisplayAffinity(hwnd,0x11):raise CaptureError('Cannot exclude caption controls')
   changed.append((hwnd,previous.value))
  if changed:dwm.DwmFlush()
  image=screen.grabWindow(0).toImage()
  if image.isNull():raise CaptureError('Empty screen image')
  return image
 finally:
  # Restore immediately so remote desktop and other apps still see the controls.
  for hwnd,previous in reversed(changed):user.SetWindowDisplayAffinity(hwnd,previous)
  if changed:dwm.DwmFlush()
