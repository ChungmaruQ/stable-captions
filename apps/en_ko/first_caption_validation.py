"""Opt-in real-time prerecorded first-caption measurement, never live microphone."""
def run(destination):
    import sys,time,json,wave
    from pathlib import Path
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer,Qt
    from app import MainWindow
    root=Path(destination);app=QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    w=MainWindow(warmup=False);screen=max(app.screens(),key=lambda s:s.geometry().x())
    w.screen_choice.setCurrentIndex(app.screens().index(screen));w.move(screen.geometry().topLeft())
    w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    w.caption_mode.setCurrentIndex(3);w.context.use_documents.setChecked(False)
    w.context.active=False;w.context.timer.stop()
    report={'packaged':bool(getattr(sys,'frozen',False)),'source':'real-time prerecorded audio; no microphone or screen capture','samples':[]}
    clips=iter(sorted(root.glob('sample-*.wav')));current={};started=[0];done=[False]
    old_receive=w.receive
    def receive(session,rid,en,ko):
        current.setdefault('recognized_units',[]).append({'english':en,'korean':ko})
        old_receive(session,rid,en,ko)
    w.receive=receive
    old_advance=w.overlay.advance_text
    def advance(text):
        if not current.get('first_display'):
            current['first_display']=text;current['first_display_seconds']=round(time.monotonic()-started[0],3)
        current.setdefault('displayed',[]).append(text)
        old_advance(text)
    w.overlay.advance_text=advance
    def timing(event):
        if 'replay_started' in event:started[0]=event['replay_started']
        if 'partial_text' in event:
            current.setdefault('partials',[]).append(dict(event,relative=round(event['received']-started[0],3)))
            current.setdefault('first_partial_seconds',round(event['received']-started[0],3))
        if 'early' in event or 'duration' in event:
            current.setdefault('commits',[]).append(dict(event,relative=round(event['received']-started[0],3)))
    def next_sample():
        if done[0]:return
        try:path=next(clips)
        except StopIteration:finish();return
        current.clear();current.update(clip=path.name);started[0]=time.monotonic()
        current['input_mode']='auto'
        w.start(str(path),realtime=True)
        worker=w.worker
        worker.timing.connect(timing)
        worker.failed.connect(lambda error:current.update(error=error))
        # Suppress re-warmup between prerecorded tests only.
        w.prepare_connections=lambda:None
        def finished():
            ended=time.monotonic()
            def drain():
                busy=bool(w.context.jobs or w.context.pending or w.context.clauses.held or w.queue.pending)
                if busy and time.monotonic()-ended<12:
                    QTimer.singleShot(100,drain);return
                current['drained']=not busy
                report['samples'].append(dict(current));QTimer.singleShot(400,next_sample)
            drain()
        worker.finished.connect(finished)
    def finish():
        if done[0]:return
        done[0]=True
        report['pass']=len(report['samples'])>=2 and all(s.get('first_display') and not s.get('error') for s in report['samples'])
        switch=next((s for s in report['samples'] if 'switch' in s['clip']),None)
        if switch:
            units=switch.get('recognized_units',[])
            report['automatic_switch']=any(x['korean'] for x in units) and any(x['english'] and not x['korean'] for x in units)
            report['pass']=report['pass'] and report['automatic_switch']
        report['english_only']=all(not any('가'<=c<='힣' for c in text) for sample in report['samples'] for text in sample.get('displayed',[]))
        report['pass']=report['pass'] and report['english_only']
        (root/'first-caption-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        w.close()
        def quit_ready():
            if not w.context.jobs and w.worker is None:app.exit(0 if report['pass'] else 1)
            else:QTimer.singleShot(100,quit_ready)
        quit_ready()
    QTimer.singleShot(0,next_sample);QTimer.singleShot(100000,finish)
    return app.exec()
