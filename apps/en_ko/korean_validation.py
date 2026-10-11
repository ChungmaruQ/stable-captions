"""Opt-in packaged Korean-output validation with fixed text and bilingual WAV."""
def run(destination):
    import json,sys,time
    from pathlib import Path
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer,Qt
    from app import MainWindow
    from korean_output import valid_korean_caption
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    app=QApplication.instance() or QApplication([]);app.setQuitOnLastWindowClosed(False)
    w=MainWindow(warmup=False);c=w.context;c.timer.stop()
    screen=max(app.screens(),key=lambda s:s.geometry().x())
    w.screen_choice.setCurrentIndex(app.screens().index(screen));w.move(screen.availableGeometry().x()+30,screen.availableGeometry().y()+30)
    w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);w.output_language.setCurrentIndex(1)
    w.position.setCurrentIndex(2);w.show()
    report={'packaged':bool(getattr(sys,'frozen',False)),'rows':[],'audio_received':[], 'audio_outputs':[], 'errors':[],'checks':{}}
    samples=[('Hello, everyone.',''),('This treatment may help, but its effectiveness has not been proven.',''),
             ('We used 5 mg of PVA.',''),('Does the treatment work?',''),
             ('','효과가 있는지 확인했습니다.'),('','효과가 있을 수 있지만 아직 입증되지는 않았습니다.')]
    index=[0];start=[0.0];done=[False];audio=[False];audio_end=[None]
    def next_sample():
        if index[0]>=len(samples):start_audio();return
        start[0]=time.monotonic();en,ko=samples[index[0]]
        c.translate(str(index[0]),en,ko,received)
    def received(rid,text,source):
        report['rows'].append({'input':samples[index[0]],'text':text,'seconds':round(time.monotonic()-start[0],3)})
        w.overlay.advance_text(w.overlay.pages(text)[0]);w.overlay.show()
        index[0]+=1;QTimer.singleShot(100,next_sample)
    original=w.deliver
    def delivered(session,rid,text,source):
        report['audio_outputs'].append({'text':text,'source':source})
        original(session,rid,text,source)
    w.deliver=delivered
    def start_audio():
        wav=root/'bilingual-test.wav'
        if not wav.exists():finish();return
        audio[0]=True;w.start(str(wav),realtime=True)
        w.worker.final.connect(lambda rid,en,ko:report['audio_received'].append({'en':en,'ko':ko}))
        w.worker.failed.connect(report['errors'].append)
        w.worker.finished.connect(lambda:audio_end.__setitem__(0,time.monotonic()))
    # Do not start another preconnection when the fixture reaches EOF.
    w.prepare_connections=lambda:None
    def poll():
        if audio[0] and audio_end[0] and not c.pending and not c.jobs and time.monotonic()-audio_end[0]>.3:finish()
    def finish():
        if done[0]:return
        done[0]=True
        rows=report['rows'];ch=report['checks']
        ch['all_text_delivered']=len(rows)==len(samples)
        ch['korean_output']=len(rows)>0 and all(valid_korean_caption(x['text']) for x in rows)
        ch['same_language_unchanged']=len(rows)==6 and rows[4]['text']==samples[4][1] and rows[5]['text']==samples[5][1]
        ch['number_unit']=len(rows)>2 and '5' in rows[2]['text'] and 'mg' in rows[2]['text'] and 'PVA' in rows[2]['text']
        ch['audio_both_languages']=any(x['ko'] for x in report['audio_received']) and any(x['en'] and not x['ko'] for x in report['audio_received'])
        ch['audio_korean_only']=bool(report['audio_outputs']) and all(valid_korean_caption(x['text']) for x in report['audio_outputs'])
        ch['no_errors']=not report['errors']
        ch['right_screen_only']=screen.geometry().contains(w.overlay.geometry())
        report['pass']=all(ch.values())
        w.overlay.advance_text('영어와 한국어 발화를 한국어 자막으로 표시합니다.');w.overlay.show()
        w.grab().save(str(root/'settings.png'));w.overlay.grab().save(str(root/'caption.png'))
        (root/'korean-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        w.close()
        def quit_ready():
            if w.worker is None and not c.jobs:app.exit(0 if report['pass'] else 1)
            else:QTimer.singleShot(100,quit_ready)
        quit_ready()
    timer=QTimer();timer.timeout.connect(poll);timer.start(100)
    QTimer.singleShot(0,next_sample);QTimer.singleShot(115000,finish)
    return app.exec()
