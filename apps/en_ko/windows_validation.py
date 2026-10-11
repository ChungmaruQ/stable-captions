"""Opt-in validation on the actual Windows EXE using supplied, non-private test audio."""
import json,sys,time,math
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QPainter,QColor,QFont
from PySide6.QtWidgets import QWidget,QApplication

def run(asset_dir):
    import context_ui
    from app import MainWindow
    from event_reference import PROFILES
    root=Path(asset_dir); started=time.monotonic()
    report={'platform':sys.platform,'ocr':[],'model':[],'captions':[],'errors':[],'language_status':[]}
    original_ocr=context_ui.read_slide; original_model=context_ui.translate_with_context
    def ocr(*args):
        t=time.monotonic();text=original_ocr(*args)
        report['ocr'].append({'seconds':round(time.monotonic()-t,3),'text':text});return text
    def model(*args):
        t=time.monotonic()
        try:
            text=original_model(*args);report['model'].append({'seconds':round(time.monotonic()-t,3),'ok':True,'deployment':args[2],'output':text});return text
        except Exception:
            report['model'].append({'seconds':round(time.monotonic()-t,3),'ok':False});raise
    context_ui.read_slide=ocr;context_ui.translate_with_context=model
    app=QApplication.instance() or QApplication([]); app.setStyle('Fusion')
    class Slide(QWidget):
        def paintEvent(self,event):
            p=QPainter(self);elapsed=time.monotonic()-started
            p.fillRect(self.rect(),QColor('#f6f8fc' if elapsed<35 else '#e3edf8'))
            p.setPen(QColor('#132c46'));p.setFont(QFont('Segoe UI',34))
            p.drawText(80,110,'Scientific names / 학명')
            p.setFont(QFont('Segoe UI',25))
            lines=['Binomial nomenclature / 이명법',
                   'Genus name / 속명 + specific epithet / 종소명',
                   'Scientific names identify organisms precisely.',
                   'Latin is a dead language / 라틴어는 사어이다.',
                   'Homo sapiens, Homo erectus']
            if elapsed>=20:lines.append('The genus name begins with a capital letter.')
            if elapsed>=35:lines[0]='Slide 2: Naming rules and examples'
            for i,line in enumerate(lines):p.drawText(80,190+70*i,line)
            p.setBrush(QColor('red'));p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(int(300+160*math.sin(elapsed*2)),int(350+70*math.cos(elapsed*3)),16,16)
    slide=Slide();slide.setWindowTitle('Stable Captions validation slide');slide.showFullScreen()
    motion=QTimer();motion.timeout.connect(slide.update);motion.start(50)
    w=MainWindow();report['greeting_bilingual_pairs']=len(next(p for p in PROFILES if p['id']=='greeting').get('bilingual_pairs',[]));report['event_profiles']=len(PROFILES);report['documents_default']=w.context.use_documents.isChecked();w.showMinimized();w.context.active=True;w.context.use_translation.setChecked(True)
    report['panel_sizes']=[];report['rollup_observed']=False;report['max_caption_lines']=0
    observe=QTimer()
    def inspect_caption():
        lines=w.overlay.label.text().splitlines()
        size=[w.overlay.width(),w.overlay.height()]
        if lines and size not in report['panel_sizes']:report['panel_sizes'].append(size)
        report['max_caption_lines']=max(report['max_caption_lines'],len(lines))
        if getattr(w.overlay.label,'dim_lines',0)==1:
            report['rollup_observed']=True
            report['rollup_sample']=w.overlay.label.text()
    observe.timeout.connect(inspect_caption);observe.start(100)
    orig_deliver=w.deliver
    def deliver(session,rid,en,ko):
        report['captions'].append({'at':round(time.monotonic()-started,2),'id':rid,'en':en,'source':ko})
        orig_deliver(session,rid,en,ko)
    w.deliver=deliver
    def start_audio():
        w.start(str(root/'bilingual-test.wav'))
        w.worker.failed.connect(report['errors'].append)
        w.worker.status.connect(report['language_status'].append)
    QTimer.singleShot(3500,start_audio)
    def finish():
        report['native_slide_ocr']=any('Scientific names' in x['text'] for x in report['ocr'])
        report['context_metrics']=list(w.context.metrics)
        report['elapsed']=round(time.monotonic()-started,2)
        report['english_count']=sum(not x['source'] for x in report['captions'])
        report['korean_count']=sum(bool(x['source']) for x in report['captions'])
        report['pass']=bool(report['english_count'] and report['korean_count'] and len(report['ocr'])>=2 and any(x['ok'] for x in report['model']) and not report['errors'] and report['native_slide_ocr'] and report['event_profiles']==16 and report['greeting_bilingual_pairs']==21 and report['documents_default'] and report['rollup_observed'] and report['max_caption_lines']<=3 and len(report['panel_sizes'])==1)
        observe.stop();w.stop();w.context.active=False;slide.close();motion.stop()
        (root/'windows-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        w.close()
        def quit_when_safe():
            if w.worker is None and not w.context.jobs:app.quit()
            else:QTimer.singleShot(200,quit_when_safe)
        quit_when_safe()
    QTimer.singleShot(75000,finish)
    app.exec()
    return 0 if report.get('pass') else 1
