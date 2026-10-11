"""Opt-in real model check with no documents, screen capture or microphone."""
def run(destination):
    import json,sys,time
    from pathlib import Path
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QTimer,Qt
    from app import MainWindow
    from output_language import has_hangul
    from event_data import EVENT_DATA
    app=QApplication.instance() or QApplication([]);app.setStyle('Fusion')
    root=Path(destination);root.mkdir(parents=True,exist_ok=True)
    w=MainWindow(warmup=False);c=w.context;c.timer.stop()
    screen=max(app.screens(),key=lambda s:s.geometry().x())
    w.screen_choice.setCurrentIndex(app.screens().index(screen));w.move(screen.geometry().topLeft())
    w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    c.use_documents.setChecked(False);c.use_translation.setChecked(True)
    samples=[
        ('The result is constant.','실험 결과가 일관되게 나왔습니다.'),
        ('Is it effective?','효과가 있는지 확인했습니다.'),
        ('It works, but it is not proven.','효과가 있을 수 있지만 아직 입증되지 않았습니다.'),
        ('We will begin the next session in five minutes.',''),
    ]
    report={'source':'real cloud translation of fixed text; screen and microphone off',
            'packaged':bool(getattr(sys,'frozen',False)),'rows':[],'checks':{},'warmup_ok':False}
    index=[0];start=[0.0];complete=[False]
    def next_sample():
        if index[0]>=len(samples):finish();return
        start[0]=time.monotonic();baseline,source=samples[index[0]]
        c.translate_unit(str(index[0]),baseline,source,received)
    def received(rid,text,source):
        report['rows'].append({'source':source,'baseline':samples[index[0]][0],'english':text,
                               'seconds':round(time.monotonic()-start[0],3)})
        w.overlay.advance_text(w.overlay.pages(text)[0]);w.overlay.show()
        index[0]+=1;QTimer.singleShot(300,next_sample)
    def finish():
        if complete[0]:return
        complete[0]=True
        rows=report['rows'];checks=report['checks']
        checks['generic']=EVENT_DATA=={'profiles':[],'common':'','event':''}
        checks['screen_off']=not c.active and not c.text and not c.slide_image
        checks['all_delivered']=len(rows)==len(samples)
        checks['english_only']=bool(rows) and all(not has_hangul(x['english']) for x in rows)
        checks['correction_used']=len(c.metrics)==3 and all(x['context_used'] for x in c.metrics)
        checks['statement_preserved']=len(rows)>1 and '?' not in rows[1]['english']
        checks['uncertainty_preserved']=len(rows)>2 and any(t in rows[2]['english'].lower() for t in ('may','might','could')) and 'not' in rows[2]['english'].lower()
        checks['english_direct']=len(rows)>3 and rows[3]['english']==samples[3][0]
        checks['right_screen_only']=screen.geometry().contains(w.overlay.geometry())
        report['metrics']=list(c.metrics);report['pass']=all(checks.values())
        w.overlay.grab().save(str(root/'caption.png'))
        (root/'generic-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        w.close()
        def quit_ready():
            if not c.jobs:app.exit(0 if report['pass'] else 1)
            else:QTimer.singleShot(100,quit_ready)
        quit_ready()
    def warmed(value):
        report['warmup_ok']=bool(value[0]);QTimer.singleShot(0,next_sample)
    args=(c.model_endpoint.text().strip(),c.model_key.text().strip(),c.deployment.text().strip(),'안녕하세요.','','',[],'',[],b'')
    c.run_job(lambda:c.request_translation(args),warmed)
    QTimer.singleShot(30000,finish)
    return app.exec()
