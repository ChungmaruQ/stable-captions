"""Opt-in fixed-text checks for the contextual transcript editor; no microphone."""
def run(destination):
 import sys,json,time
 from pathlib import Path
 from PySide6.QtWidgets import QApplication
 from PySide6.QtCore import QTimer,Qt
 from app import MainWindow
 from output_language import has_hangul
 app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
 root=Path(destination);root.mkdir(parents=True,exist_ok=True)
 w=MainWindow(warmup=False);c=w.context;c.timer.stop();screen=max(app.screens(),key=lambda s:s.geometry().x())
 w.screen_choice.setCurrentIndex(app.screens().index(screen));w.move(screen.geometry().topLeft());w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
 c.use_correction.setChecked(True);c.use_speculation.setChecked(False);c.active=True
 cases=[('혁명을 사용합니다.','학명은 생물을 정확하게 지칭하는 이름입니다.'),('기술이전 수입은 40억 원이 아니라 30억 원입니다.','기술이전 수입은 40억 원입니다.'),('The genius name begins with a capital letter.','Genus name: first letter capitalized.'),('프랑스 혁명을 공부했습니다.','학명과 속명, 종소명의 표기')]
 report={'packaged':bool(getattr(sys,'frozen',False)),'source':'fixed ASR text and reference text; no microphone or live capture','rows':[]};index=[0];started=[0];done=[False]
 def next_case():
  if index[0]==len(cases):finish();return
  c.reset();source,slide=cases[index[0]];c.text=slide;started[0]=time.monotonic()
  korean=has_hangul(source)
  c.translate_unit(str(index[0]),'' if korean else source,source if korean else '',received)
 def received(rid,text,source):
  report['rows'].append({'input':cases[index[0]][0],'corrected':getattr(text,'corrected_source',source),'english':str(text),'accepted':getattr(text,'accepted_edits',[]),'rejected':getattr(text,'rejected_edits',[]),'seconds':round(time.monotonic()-started[0],3)})
  w.deliver(w.session_number,rid,text,source);w.tick();w.overlay.show();index[0]+=1;QTimer.singleShot(100,next_case)
 def finish():
  if done[0]:return
  done[0]=True;rows=report['rows']
  report['checks']={'all_cases_delivered':len(rows)==4,'english_only':bool(rows) and all(not has_hangul(x['english']) for x in rows),'numbers_source_preserved':len(rows)>1 and rows[1]['corrected']==cases[1][0],'unrelated_source_preserved':len(rows)>3 and rows[3]['corrected']==cases[3][0],'within_existing_deadline':bool(rows) and all(x['seconds']<5.5 for x in rows)}
  report['pass']=all(report['checks'].values())
  report['history']=w.history.toPlainText()
  w.show();w.grab().save(str(root/'settings.png'));w.hide();c.dialog.move(screen.geometry().topLeft());c.dialog.show();c.dialog.grab().save(str(root/'correction-option.png'));c.dialog.hide()
  (root/'correction-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  w.close()
  def quit_ready():
   if not c.jobs:app.exit(0 if report['pass'] else 1)
   else:QTimer.singleShot(100,quit_ready)
  quit_ready()
 QTimer.singleShot(0,next_case);QTimer.singleShot(45000,finish)
 return app.exec()
