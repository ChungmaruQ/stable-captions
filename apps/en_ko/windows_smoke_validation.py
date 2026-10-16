"""Packaged Windows UI checks without microphone or cloud usage."""
def run(destination):
 import json,sys,time,threading
 from pathlib import Path
 from types import SimpleNamespace
 from PySide6.QtWidgets import QApplication
 from PySide6.QtCore import QTimer
 from app import MainWindow
 from context_config import CONTEXT_CONFIG
 root=Path(destination);root.mkdir(parents=True,exist_ok=True)
 app=QApplication([]);app.setQuitOnLastWindowClosed(False);w=MainWindow(warmup=False)
 w.worker=SimpleNamespace(stop_event=threading.Event(),set_hints=lambda phrases:None);w.speech_connected=True;w.first_caption_shown=True;w.last_activity=time.monotonic();w.show();w.overlay.show()
 report={'platform':sys.platform,'packaged':bool(getattr(sys,'frozen',False)),'scope':'UI and controlled connected state; no actual microphone or cloud requests','model':CONTEXT_CONFIG['model']['deployment'],'checks':{}}
 def finish():
  w.expire_idle_caption();report['checks']['idle_after_ten_seconds']=w.overlay.label.text()=='[대기 중]';report['checks']['idle_not_caption_history']=not w.overlay.history_rows
  w.overlay.grab().save(str(root/'idle.png'));w.grab().save(str(root/'settings.png'))
  w.speech_activity(w.session_number);report['checks']['speech_clears_idle']=w.overlay.label.text()==''
  w.deliver(w.session_number,'smoke','This is a test caption.','테스트 자막입니다.');w.tick();report['checks']['caption_rendered']='test caption' in w.overlay.label.text()
  w.overlay.grab().save(str(root/'caption.png'));w.worker=None;w.stop();report['checks']['stop_clears_overlay']=not w.overlay.label.text()
  report['pass']=all(report['checks'].values());(root/'windows-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
  w.close();app.exit(0 if report['pass'] else 1)
 QTimer.singleShot(10500,finish)
 return app.exec()
