"""Opt-in packaged-app test; prerecorded audio, optional synchronized live screen OCR."""
import sys,time,json
from pathlib import Path
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel
from PySide6.QtCore import QTimer,Qt

def run(asset_dir):
    from app import MainWindow
    import context_ui
    from caption_safety import protect_caption,flagged,OMITTED
    from event_reference import PROFILES
    root=Path(asset_dir);continuous=(root/'continuous-test.wav').exists();started=time.monotonic();app=QApplication.instance() or QApplication([])
    app.setStyle('Fusion');app.setQuitOnLastWindowClosed(False)
    screen_off=(root/'screen-off.flag').exists()
    live_path=root/'live-slides.json';slides=json.loads(live_path.read_text()) if live_path.exists() and not screen_off else [];phase=[0];replay=[None]
    report={'platform':sys.platform,'packaged':bool(getattr(sys,'frozen',False)),'timing':[],'display_times':[],'display_rows':[],'received':[],'errors':[],'captions':[],'model':[],'panel_sizes':[],'max_lines':0,'protection':{},'source':'prerecorded bilingual audio; cached slide text; microphone and live screen capture not exercised'}
    original=context_ui.translate_with_context
    def model(*args):
        t=time.monotonic()
        if slides:report.setdefault('model_slide_context',[]).append({'phase':phase[0],'slide':args[5],'image_attached':len(args)>9 and bool(args[9])})
        try:
            result=original(*args);report['model'].append({'ok':True,'seconds':round(time.monotonic()-t,3)});return result
        except Exception:
            report['model'].append({'ok':False,'seconds':round(time.monotonic()-t,3)});raise
    context_ui.translate_with_context=model
    test_screen = max(app.screens(), key=lambda screen: screen.geometry().x())
    test_index = app.screens().index(test_screen)
    report['test_screen'] = {'name': test_screen.name(), 'geometry': test_screen.geometry().getRect()}
    backdrop=QWidget();backdrop.setWindowTitle('Stable Captions · release validation');backdrop.resize(1000,620)
    backdrop.move(test_screen.geometry().topLeft())
    backdrop.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    layout=QVBoxLayout(backdrop)
    labels=[]
    default=['Natural products and drug discovery','University of California San Diego','Oceanography and pharmaceutical sciences','Biological activities and clinical effects']
    for text in (slides[0]['lines'] if slides else default):
        label=QLabel(text);label.setWordWrap(True);label.setStyleSheet('font-size:32px;padding:20px;color:#111;background:white');layout.addWidget(label);labels.append(label)
    layout.setContentsMargins(70,60,70,250)
    backdrop.setStyleSheet('background:white')
    if slides and sys.platform=='darwin':
        backdrop.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        backdrop.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);backdrop.setGeometry(test_screen.geometry());backdrop.show()
    elif slides:backdrop.showFullScreen()
    else:backdrop.show()
    w=MainWindow(warmup=True);w.screen_choice.setCurrentIndex(test_index);w.move(test_screen.geometry().topLeft());w.hide()
    if slides:
        report['source']='prerecorded bilingual audio with synchronized slides; real screen capture and Azure Vision OCR; microphone not exercised'
        report['ocr']=[]
        w.context.active=True
        def ocr_changed():
            text=w.context.preview.toPlainText()
            if text:report['ocr'].append({'phase':phase[0],'text':text,'at':time.monotonic()})
        w.context.preview.textChanged.connect(ocr_changed)
    elif not screen_off:
        w.context.timer.stop();w.context.active=True;w.context.text=(root/'slide-ocr.txt').read_text(encoding='utf-8')
    else:
        w.context.timer.stop();w.context.active=False
        report['source']='prerecorded bilingual audio; screen analysis and event documents off; real speech and model services; microphone not exercised'
    for label,en,ko in [('model_output','This is bullshit.',''),('source_mask','A translation.','****'),('english_direct','An asshole.','')]:
        w.clear();w.deliver(w.session_number,label,en,ko);w.tick()
        report['protection'][label]=w.overlay.label.text()==OMITTED and not flagged(w.history.toPlainText().replace(OMITTED,''))
    report['protection']['medical']=not protect_caption('Sex hormones and breast cancer are studied.')[2]
    report['protection']['unicode']=protect_caption('ｆｕｃｋ')[2]
    report['protection']['korean']=protect_caption('Ordinary English.','씨발')[2]
    w.clear()
    original_receive=w.receive
    def receive(session,rid,en,ko):
        report['received'].append({'rid':rid,'at':time.monotonic(),'en':en,'source':ko})
        original_receive(session,rid,en,ko)
    w.receive=receive
    original_deliver=w.deliver
    def deliver(session,rid,en,ko):
        safe_en,safe_ko,blocked=protect_caption(en,ko)
        report['captions'].append({'rid':rid,'absolute_at':time.monotonic(),'at':round(time.monotonic()-started,3),'en':safe_en,'source':safe_ko,'blocked':blocked})
        original_deliver(session,rid,en,ko)
    w.deliver=deliver
    old_advance=w.overlay.advance_text
    def advance(text):
        report['display_times'].append(time.monotonic());report['display_rows'].append({'at':time.monotonic(),'text':text});old_advance(text)
    w.overlay.advance_text=advance
    completed=False
    def finish():
        nonlocal completed
        if completed:return
        completed=True;watch.stop()
        report['preparation'] = w.preparation_result
        report['english_count']=sum(not x['source'] for x in report['captions'])
        report['korean_count']=sum(bool(x['source']) for x in report['captions'])
        report['elapsed']=round(time.monotonic()-started,2)
        report['profiles']=len(PROFILES);report['context_metrics']=list(w.context.metrics)
        report['corrected_captions']=sum(x.get('context_used',False) for x in report['context_metrics'])
        report['baseline_fallbacks']=sum(not x.get('context_used',False) for x in report['context_metrics'])
        report['pending']=len(w.queue.pending)
        report['pass']=bool(report['packaged'] and all(report['protection'].values()) and report['english_count']>=1 and report['korean_count']>=1 and not report['errors'] and any(x['ok'] for x in report['model']) and report['max_lines']<=3 and len(report['panel_sizes'])==1 and report['profiles']==0 and report['pending']==0)
        if continuous:
            events=[x for x in report['timing'] if 'duration' in x]
            begin=next((x['replay_started'] for x in report['timing'] if 'replay_started' in x),started)
            report['first_display_seconds']=round(report['display_times'][0]-begin,2) if report['display_times'] else None
            report['early_commits']=sum(bool(x.get('early')) for x in report['timing'])
            report['max_native_phrase_seconds']=round(max((x['duration'] for x in events),default=999),2)
            import wave
            with wave.open(str(root/'continuous-test.wav')) as f:duration=f.getnframes()/f.getframerate()
            report['last_display_after_audio']=round(report['display_times'][-1]-begin-duration,2) if report['display_times'] else None
            report['pass']=bool(report['pass'] and report['english_count']>=5 and report['korean_count']>=4 and sum(bool(x.get('early')) for x in report['timing'])>=8 and report['first_display_seconds']<10 and report['last_display_after_audio']<6 and not any(x.get('alignment_failed') for x in report['timing']))
        if slides:
            report['live_ocr_pass']=all(any(x['phase']==i and slide['expected'].lower() in x['text'].lower() for x in report['ocr']) for i,slide in enumerate(slides))
            report['model_received_matching_slide']=any(x['phase']==1 and slides[1]['expected'].lower() in x['slide'].lower() for x in report.get('model_slide_context',[]))
            report['pass']=report['pass'] and report['live_ocr_pass'] and report['model_received_matching_slide']
        report['image_requests'] = sum(x.get('image_attached',False) for x in report.get('model_slide_context',[]))
        report['image_results_used'] = sum(x.get('image_used',False) for x in report['context_metrics'])
        if slides: report['pass'] = report['pass'] and report['image_requests']>0 and report['image_results_used']>0
        report['hints_registered']=any(x.get('phrase_hints_count',0)>0 for x in report['timing']) and not any(x.get('phrase_hints_error') for x in report['timing'])
        report['pass']=report['pass'] and (not any(x.get('phrase_hints_error') for x in report['timing']) if screen_off else report['hints_registered'])
        if screen_off:
            from speech_hints import build_hints
            report['screen_off']=not w.context.active and not w.context.slide_image and not w.context.text
            report['pass']=report['pass'] and report['screen_off'] and not build_hints() and report['corrected_captions']>0
        if sys.platform=='darwin':
            from mac_overlay import state
            report['mac_overlay']=state(w.overlay)
            native=report['mac_overlay']
            report['pass']=report['pass'] and native['level']>=25 and native['click_through'] and not native['hides_on_deactivate'] and not native['error'] and (native['collection_behavior'] & 257)==257
        report['pass'] = report['pass'] and bool(report.get('speech_ready_seen')) and bool(report.get('preparation')) and all(report['preparation'].values())
        report['overlay_geometry'] = w.overlay.geometry().getRect()
        report['right_screen_only'] = test_screen.geometry().contains(w.overlay.geometry()) and test_screen.geometry().contains(backdrop.geometry())
        if sys.platform=='darwin': report['pass'] = report['pass'] and report['right_screen_only']
        (root/'release-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        w.stop();w.context.active=False;w.close();backdrop.close()
        def quit_ready():
            if w.worker is None and w.preparation is None and not w.context.jobs:app.quit()
            else:QTimer.singleShot(100,quit_ready)
        quit_ready()
    def observe():
        if slides and replay[0] is not None:
            elapsed=time.monotonic()-replay[0]
            target=max(i for i,slide in enumerate(slides) if elapsed>=slide['at'])
            if target!=phase[0]:
                phase[0]=target
                for label,text in zip(labels,slides[target]['lines']):label.setText(text)
        lines=w.overlay.label.text().splitlines()
        if lines:
            report['max_lines']=max(report['max_lines'],len(lines));size=[w.overlay.width(),w.overlay.height()]
            if size not in report['panel_sizes']:report['panel_sizes'].append(size)
            w.overlay.grab().save(str(root/'release-caption.png'))
        if time.monotonic()-started>10 and w.worker is None and len(report['captions'])>=2 and not w.queue.pending and not w.context.pending and not w.context.jobs and not w.context.clauses.held:finish()
    watch=QTimer();watch.timeout.connect(observe);watch.start(400)
    def start():
        if w.preparation_result is None and time.monotonic()-started<25:
            QTimer.singleShot(500,start);return
        if slides and not w.context.text:
            if time.monotonic()-started<25:QTimer.singleShot(500,start);return
            report['errors'].append('Initial live OCR not ready')
        w.start(str(root/('continuous-test.wav' if continuous else 'bilingual-test.wav')),realtime=continuous)
        if w.worker:
            w.worker.ready.connect(lambda: report.update(speech_ready_seen=True, ready_text=w.ready_label.text()))
            w.worker.failed.connect(report['errors'].append);w.worker.timing.connect(report['timing'].append)
            w.worker.timing.connect(lambda e: replay.__setitem__(0,e['replay_started']) if 'replay_started' in e else None)
        else:report['errors'].append('Audio worker did not start')
    QTimer.singleShot(1000,start);QTimer.singleShot(175000 if continuous else 90000,finish)
    app.exec();return 0 if report.get('pass') else 1
