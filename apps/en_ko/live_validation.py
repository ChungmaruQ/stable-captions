"""Explicit opt-in packaged replay using real desktop capture and real-time STT."""
def run(destination):
 import json,time,sys,wave
 from pathlib import Path
 from PySide6.QtCore import Qt,QTimer,Signal,QObject
 from PySide6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout
 from PySide6.QtGui import QPixmap
 from app import MainWindow
 import diagnostics
 from screen_permission import screen_permission
 root=Path(destination).resolve();plan=json.loads((root/'plan.json').read_text());mode=plan['mode']
 diagnostics.configure('live-'+mode,root/'logs')
 app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
 screen=max(app.screens(),key=lambda s:s.geometry().x());w=MainWindow(warmup=False);w.hide();w.screen_choice.setCurrentIndex(app.screens().index(screen));c=w.context;c.use_documents.setChecked(False)
 fixture=QWidget();fixture.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint);fixture.setGeometry(screen.geometry());fixture.setStyleSheet('background:white');layout=QVBoxLayout(fixture);layout.setContentsMargins(0,0,0,0);label=QLabel();label.setAlignment(Qt.AlignmentFlag.AlignCenter);layout.addWidget(label)
 variant='JP-VN' if 'JP-VN' in w.windowTitle() else 'EN-KO'
 report={'mode':mode,'packaged':bool(getattr(sys,'frozen',False)),'variant':variant,'scope':'Real screen grab of displayed fixture; WAV audio pushed to Azure STT at real-time pace; microphone acoustics not tested','source':plan.get('source','Internet photos'),'audio':plan['audio'],'rows':[],'recognized':[],'errors':[],'timing':[],'permission':screen_permission(),'captured_image_checks':[],'started_at':time.time()}
 state={'phase':'capture','case':0,'start':time.monotonic(),'audio_start':None,'frame':-1,'finished':False,'case_done':None,'audio_end':None};captions=[]
 audio=str(Path(plan['audio']).resolve());duration=wave.open(audio).getnframes()/wave.open(audio).getframerate()
 def image(path):
  pix=QPixmap(str(path));label.setPixmap(pix.scaled(screen.size(),Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
 def current_image():
  if mode=='homonym':return root/(str(state['case']+1).zfill(2)+'.jpg')
  return root/'frames'/'00001.jpg'
 def snapshot(name):
  # Own validation scene only; application's screen-capture path remains unmodified.
  screen.grabWindow(0).save(str(root/(name+'.png')))
 def started_audio(event):
  report['timing'].append(event)
  if 'replay_started' in event:state['audio_start']=event['replay_started'];state['audio_end']=event['replay_started']+duration
 def recognized(uid,en,ko):report['recognized'].append({'case':state['case']+1,'source':ko or en,'uid':uid,'at':time.monotonic()})
 original_deliver=w.deliver
 def delivered(session,rid,text,source):
  report['rows'].append({'case':state['case']+1,'source':source,'caption':str(text),'at':time.monotonic(),'image_available_at_delivery':bool(c.slide_image)})
  original_deliver(session,rid,text,source)
  if mode=='homonym':state['case_done']=time.monotonic();QTimer.singleShot(150,lambda:snapshot('case-'+str(state['case']+1)))
 w.deliver=delivered
 def begin_audio():
  # Image is captured first; opening settings cannot clear it during this replay.
  state['phase']='speech';state['start']=time.monotonic();state['case_done']=None;state['audio_start']=None;state['audio_end']=None
  (root/('model-image-'+str(state['case']+1)+'.jpg')).write_bytes(c.slide_image)
  report['captured_image_checks'].append({'case':state['case']+1,'bytes':len(c.slide_image),'capture_count':c.capture_count})
  w.start(audio,realtime=True);w.hide();w.worker.timing.connect(started_audio);w.worker.final.connect(recognized);w.worker.failed.connect(lambda msg:report['errors'].append(msg))
 def next_case():
  state['case']+=1;c.reset_screen();state['phase']='capture';state['start']=time.monotonic();image(current_image())
 def finish(reason):
  if state['finished']:return
  state['finished']=True;watch.stop();c.active=False;c.timer.stop();report['legacy_permission_probe']=report['permission'];report['permission']=c.permission_state;report['reason']=reason;report['finished_at']=time.time();report['metrics']=list(c.metrics);report['history']=w.history.toPlainText();report['capture_count']=c.capture_count;report['image_sent_count']=c.image_sent_count
  if mode=='homonym':
   terms=[('pear',),('ship','boat','vessel'),('belly','abdomen','stomach')] if variant=='EN-KO' else [('梨','lê'),('船','tàu','thuyền'),('腹','bụng')]
   checks=[]
   for i,t in enumerate(terms):
    texts=[r['caption'] for r in report['rows'] if r['case']==i+1]
    checks.append(bool(texts) and any(any(term in x.lower() for term in t) for x in texts))
   report['meaning_checks']=checks;report['pass']=all(checks) and len(report['captured_image_checks'])==3 and report['permission']=='granted' and not report['errors']
  else:report['pass']=reason=='completed' and report['capture_count']>0 and len(report['rows'])>10 and not report['errors']
  (root/('live-'+variant+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
  w.stop()
  def shutdown():
   if w.worker is None and not c.jobs:
    w.close();fixture.close();diagnostics.close();app.exit(0 if report['pass'] else 1)
   else:QTimer.singleShot(200,shutdown)
  shutdown()
 def poll():
  now=time.monotonic()
  if state['finished']:return
  if state['phase']=='capture':
   if c.slide_image and not c.ocr_job:begin_audio()
   elif now-state['start']>30:finish('capture_timeout')
  elif state['phase']=='speech':
   if mode=='lecture' and state['audio_start']:
    elapsed=now-state['audio_start'];frame=min(int(elapsed*2)+1,1200)
    if frame!=state['frame']:
     state['frame']=frame;image(root/'frames'/('%05d.jpg'%frame))
    if int(elapsed)%60==0:
     (root/'progress-live.json').write_text(json.dumps({'seconds':round(elapsed,1),'captions':len(report['rows']),'captures':c.capture_count,'images_sent':c.image_sent_count,'pending':len(c.pending),'queue':len(w.queue.pending)}))
    if elapsed>=duration+8:
     snapshot('lecture-final');finish('completed')
   elif mode=='homonym':
    if state['case_done'] and now-state['case_done']>2 and w.worker is None and not c.jobs:
     if state['case']==2:finish('completed')
     else:next_case()
    elif now-state['start']>25:finish('speech_timeout')
   if now-state['start']>duration+40:finish('replay_timeout')
 fixture.show();fixture.raise_();fixture.activateWindow();image(current_image());c.active=True;diagnostics.record('analysis_started',screen_index=w.screen_choice.currentIndex())
 watch=QTimer();watch.timeout.connect(poll);watch.start(100)
 return app.exec()
