"""Read screen-recording permission in the caption app's own process."""
import sys,ctypes

def _api(name):
 framework=ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')
 fn=getattr(framework,name);fn.argtypes=[];fn.restype=ctypes.c_bool
 return bool(fn())

def screen_permission():
 if sys.platform!='darwin':return 'not_required'
 try:return 'granted' if _api('CGPreflightScreenCaptureAccess') else 'denied'
 except Exception:return 'unknown'

def request_screen_permission():
 if sys.platform!='darwin':return 'not_required'
 try:return 'granted' if _api('CGRequestScreenCaptureAccess') else 'denied'
 except Exception:return 'unknown'
