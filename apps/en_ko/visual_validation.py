"""Packaged-app test of screen pixels reaching translation without OCR text."""
import json,time,sys
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt,QTimer

def run(asset_dir):
 from app import MainWindow
 import context_ui
 root=Path(asset_dir);app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
 screen=max(app.screens(),key=lambda s:s.geometry().x())
 fixture=QWidget();fixture.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint);fixture.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);fixture.setGeometry(screen.geometry());fixture.setStyleSheet('background:white')
 layout=QVBoxLayout(fixture);label=QLabel();label.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(label)
 w=MainWindow(warmup=False);w.screen_choice.setCurrentIndex(app.screens().index(screen));w.hide();c=w.context;c.use_documents.setChecked(False);c.use_speculation.setChecked(False);c.active=True
 cases=[('pear','이 배의 표면을 보세요.'),('boat','이 배의 표면을 보세요.'),('pear','이 물질은 아직 효과가 입증되지 않았습니다.')]
 fixture_only=(root/'fixture-only').exists()
 if fixture_only:c.timer.stop()
 report={'source':'fixture pixels; live screen capture not exercised' if fixture_only else 'live screen capture', 'packaged':bool(getattr(sys,'frozen',False)),'screen':screen.geometry().getRect(),'cases':[],'image_payloads':[]}
 original=context_ui.translate_with_context
 def model(*args,**kwargs):
  report['image_payloads'].append({'image':len(args)>9 and bool(args[9]),'ocr_text':args[5]})
  return original(*args,**kwargs)
 context_ui.translate_with_context=model
 try:
  import recognition_correction
  recognition_correction.translate_with_context=model
 except ImportError:pass
 phase=[-1];waiting=[False];deadline=[0];done=[False]
 def next_case():
  phase[0]+=1
  if phase[0]>=len(cases):finish();return
  name,source=cases[phase[0]];c.reset_screen();c.reset()
  pix=QPixmap(str(root/(name+'.png')));label.setPixmap(pix.scaled(screen.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
  if fixture_only:
   from slide_image import encode_image
   c.slide_image,_=encode_image(pix.toImage());c.image_revision+=1
  waiting[0]=False;deadline[0]=time.monotonic()+18
 def observe():
  if done[0]:return
  if time.monotonic()>deadline[0]:
   report['cases'].append({'image':cases[phase[0]][0],'error':'timeout'});next_case();return
  if waiting[0] or not c.slide_image:return
  waiting[0]=True;name,source=cases[phase[0]];t=time.monotonic();index=phase[0]
  def delivered(rid,text,ko):
   if done[0] or index!=phase[0]:return
   report['cases'].append({'image':name,'source':source,'translation':text,'seconds':round(time.monotonic()-t,3),'image_used':bool(c.metrics and c.metrics[-1].get('image_used'))})
   QTimer.singleShot(200,next_case)
  c.translate_unit(str(index),'',source,delivered)
 def finish():
  if done[0]:return
  done[0]=True;watch.stop()
  rows=report['cases'];report['pass']=len(rows)==3 and all(r.get('image_used') for r in rows) and bool(report['image_payloads']) and all(x['image'] and not x['ocr_text'] for x in report['image_payloads'])
  if report['pass']:
   if 'JP-VN' in w.windowTitle():
    report['pass']=(any(x in rows[0]['translation'] for x in ['梨','果実','果物']) and any(x in rows[0]['translation'].lower() for x in ['lê','quả','trái']) and '船' in rows[1]['translation'] and any(x in rows[1]['translation'].lower() for x in ['thuyền','tàu']))
   else:report['pass']='pear' in rows[0]['translation'].lower() and 'boat' in rows[1]['translation'].lower()
  report['criterion']='Distinguish fruit from vessel using a text-free stylized image; exact cultivar/species naming is not required.'
  (root/'visual-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
  c.active=False;w.close();fixture.close()
  def quit_ready():
   if not c.jobs:app.quit()
   else:QTimer.singleShot(100,quit_ready)
  quit_ready()
 fixture.show();next_case();watch=QTimer();watch.timeout.connect(observe);watch.start(100)
 app.exec();return 0 if report['pass'] else 1
