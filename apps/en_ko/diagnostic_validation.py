"""Packaged log verification with synthetic pixels; never captures the desktop."""
def run(destination):
 import json,time,sys
 from pathlib import Path
 from unittest.mock import patch
 from PySide6.QtWidgets import QApplication
 from PySide6.QtCore import QTimer,QRect
 from PySide6.QtGui import QImage,QPixmap,QPainter,QFont,QColor
 from app import MainWindow
 import diagnostics
 from screen_permission import screen_permission
 root=Path(destination);root.mkdir(parents=True,exist_ok=True)
 diagnostics.configure('validation',root/'logs')
 app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
 w=MainWindow(warmup=False);c=w.context;c.timer.stop();w.timer.stop();c.use_documents.setChecked(False);c.use_speculation.setChecked(False);c.active=True
 actual_permission=screen_permission();diagnostics.record('permission_checked',state=actual_permission)
 image=QImage(900,500,QImage.Format.Format_RGB32);image.fill(QColor('white'))
 painter=QPainter(image);painter.setPen(QColor('black'));painter.setFont(QFont('Arial',36));painter.drawText(60,140,'SCREEN CONTEXT TEST');painter.setFont(QFont('Arial',25));painter.drawText(60,220,'Synthetic slide for diagnostic validation.');painter.end()
 class FixtureScreen:
  def geometry(self):return QRect(0,0,900,500)
  def grabWindow(self,unused):return QPixmap.fromImage(image)
 report={'packaged':bool(getattr(sys,'frozen',False)),'scope':'synthetic pixels through capture controller, real Azure OCR and Luna requests; no desktop capture or microphone','actual_screen_permission':actual_permission,'translated':False}
 done=[False];launched=[False]
 def capture_fixture():
  with patch('mac_screen_capture.MacScreenCapture.capture',return_value=image),patch('context_ui.screen_permission',return_value='granted'),patch('PySide6.QtWidgets.QApplication.screens',return_value=[FixtureScreen()]),patch.object(c,'controls_cover',return_value=False),patch.object(c.change_tracker,'observe',side_effect=['changed','scan']):
   c.capture();c.capture()
 def received(rid,text,source):report['translated']=True;report['translation']=str(text);QTimer.singleShot(100,finish)
 def poll():
  if not launched[0] and c.text and not c.jobs:
   launched[0]=True;c.translate_unit('fixture','','화면의 내용을 확인했습니다.',received)
 def finish():
  if done[0]:return
  done[0]=True;timer.stop();c.flush_diagnostics()
  rows=diagnostics.entries_after();path=diagnostics.log_path();content=path.read_text(encoding='utf-8') if path else ''
  checks={'capture_logged':any(r['event']=='capture_ready' for r in rows),'ocr_logged':any(r['event']=='ocr_ready' for r in rows),'image_sent_to_model':any(r['event']=='request_started' and r.get('stage')=='translation' and r.get('image_count',0)>0 for r in rows),'model_response_logged':any(r['event']=='request_received' and r.get('stage')=='translation' for r in rows),'file_written':bool(content),'ui_log_populated':bool(c.diagnostics_view.toPlainText()),'translated':report['translated']}
  from context_config import CONTEXT_CONFIG
  checks['no_keys_in_log']=all(v.get('key','') not in content for v in CONTEXT_CONFIG.values() if isinstance(v,dict) and v.get('key'))
  checks['no_payload_in_log']='SCREEN CONTEXT TEST' not in content and '화면의 내용을 확인했습니다' not in content and 'data:image' not in content
  report.update(pass_=all(checks.values()),checks=checks,events=rows);report['pass']=report.pop('pass_')
  c.analysis_tabs.setCurrentIndex(1);c.dialog.ensurePolished();c.dialog.resize(700,880);c.dialog.grab().save(str(root/'analysis-log.png'))
  (root/'diagnostic-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  c.active=False;w.close()
  def quit_ready():
   if not c.jobs:diagnostics.close();app.exit(0 if report['pass'] else 1)
   else:QTimer.singleShot(100,quit_ready)
  quit_ready()
 timer=QTimer();timer.timeout.connect(poll);timer.start(100)
 QTimer.singleShot(0,capture_fixture);QTimer.singleShot(45000,finish)
 return app.exec()
