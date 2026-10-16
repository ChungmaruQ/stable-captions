"""macOS capture via the OS-authorized ScreenCaptureKit, excluding our controls."""
import ctypes,time
from PySide6.QtCore import QEventLoop,QTimer
from PySide6.QtGui import QImage

class CaptureError(RuntimeError):pass
class CapturePermissionError(CaptureError):pass

def _wait(start,seconds=5):
 result=[];loop=QEventLoop();poll=QTimer();timeout=QTimer();timeout.setSingleShot(True)
 def completed(value,error):result.append((value,error))
 start(completed)
 poll.timeout.connect(lambda:loop.quit() if result else None);poll.start(20)
 timeout.timeout.connect(loop.quit);timeout.start(int(seconds*1000))
 if not result:loop.exec()
 poll.stop();timeout.stop()
 if not result:raise CaptureError('ScreenCaptureKit timeout')
 value,error=result[0]
 if error is not None:
  code=int(error.code())
  if code==-3801:raise CapturePermissionError('Screen recording denied')
  raise CaptureError('ScreenCaptureKit code '+str(code))
 if value is None:raise CaptureError('ScreenCaptureKit empty result')
 return value

class MacScreenCapture:
 def __init__(self):self.content=None;self.content_at=0
 def check_access(self):
  import ScreenCaptureKit as S
  self.content=_wait(lambda cb:S.SCShareableContent.getShareableContentWithCompletionHandler_(cb));self.content_at=time.monotonic()
  return bool(self.content.displays())
 def capture(self,screen,widgets):
  import Quartz  # Register CGImageRef ownership and type bridging before callbacks.
  import ScreenCaptureKit as S
  import objc
  from AppKit import NSBitmapImageRep,NSPNGFileType
  # Window visibility and monitor arrangement can change while settings stay open.
  if self.content is None or time.monotonic()-self.content_at>2:
   self.content=_wait(lambda cb:S.SCShareableContent.getShareableContentWithCompletionHandler_(cb))
   self.content_at=time.monotonic()
  geometry=screen.geometry();displays=list(self.content.displays())
  if not displays:raise CaptureError('No displays')
  def distance(display):
   f=display.frame()
   return abs(f.origin.x-geometry.x())+abs(f.origin.y-geometry.y())+abs(f.size.width-geometry.width())+abs(f.size.height-geometry.height())
  display=min(displays,key=distance)
  if distance(display)>8:raise CaptureError('Display geometry changed')
  ids=set()
  for widget in widgets:
   if not widget.isVisible():continue
   view=objc.objc_object(c_void_p=ctypes.c_void_p(int(widget.winId())))
   window=view.window()
   if window is not None:ids.add(int(window.windowNumber()))
  excluded=[window for window in self.content.windows() if int(window.windowID()) in ids]
  content_filter=S.SCContentFilter.alloc().initWithDisplay_excludingWindows_(display,excluded)
  config=S.SCStreamConfiguration.alloc().init()
  scale=min(1280/geometry.width(),720/geometry.height())
  config.setWidth_(max(2,round(geometry.width()*scale)));config.setHeight_(max(2,round(geometry.height()*scale)));config.setShowsCursor_(False)
  def capture_bytes(done):
   def completed(image,error):
    if error is not None:done(None,error);return
    # Copy pixels while the native completion handler owns its CGImage.
    rep=NSBitmapImageRep.alloc().initWithCGImage_(image)
    data=rep.representationUsingType_properties_(NSPNGFileType,{})
    done(bytes(data),None)
   S.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(content_filter,config,completed)
  result=QImage.fromData(_wait(capture_bytes))
  if result.isNull():raise CaptureError('Invalid captured image')
  return result
