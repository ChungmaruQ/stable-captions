"""Local-only native capture regression: no Azure and no microphone."""
def run(destination):
 import json,sys
 from pathlib import Path
 from PySide6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout
 from PySide6.QtCore import Qt,QTimer
 from PySide6.QtGui import QColor
 from mac_screen_capture import MacScreenCapture
 root=Path(destination);root.mkdir(parents=True,exist_ok=True)
 app=QApplication([]);app.setQuitOnLastWindowClosed(False);screen=max(app.screens(),key=lambda s:s.geometry().x())
 fixture=QWidget();fixture.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint);fixture.setGeometry(screen.geometry());fixture.setStyleSheet('background:#237b42')
 controls=QWidget();controls.setWindowTitle('자막 설정창 제외 검사');controls.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint);g=screen.geometry();controls.setGeometry(g.x()+g.width()//4,g.y()+g.height()//4,g.width()//2,g.height()//2);controls.setStyleSheet('background:#f030c0')
 layout=QVBoxLayout(controls);layout.addWidget(QLabel('설정창이 열려 있어도 뒤의 녹색 화면을 분석해야 합니다.\n로컬 캡처 검사 · Azure 전송 없음'))
 report={'scope':('local Windows display capture with visible controls excluded; no cloud requests' if sys.platform=='win32' else 'local ScreenCaptureKit display capture with visible controls excluded; no cloud requests'),'packaged':bool(getattr(sys,'frozen',False))}
 def check():
  try:
   image=(__import__('windows_screen_capture').capture_screen(screen,(controls,)) if sys.platform=='win32' else MacScreenCapture().capture(screen,(controls,)));image.save(str(root/'native-capture.png'))
   color=image.pixelColor(image.width()//2,image.height()//2)
   report.update(width=image.width(),height=image.height(),center_rgb=[color.red(),color.green(),color.blue()],pass_=color.green()>color.red()*1.5 and color.green()>color.blue()*1.2,controls_visible=controls.isVisible())
  except Exception as exc:report.update(error_type=type(exc).__name__,error=str(exc),pass_=False)
  report['pass']=report.pop('pass_');(root/'native-capture.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));fixture.close();controls.close();app.exit(0 if report['pass'] else 1)
 fixture.show();fixture.raise_();controls.show();controls.raise_();controls.activateWindow();QTimer.singleShot(2000,check)
 return app.exec()
