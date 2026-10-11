"""Offline validation of the readable overlay on the rightmost display."""
def run(destination):
    import sys,json,time
    from pathlib import Path
    from PySide6.QtWidgets import QApplication,QWidget,QLabel,QVBoxLayout
    from PySide6.QtCore import Qt,QTimer
    from PySide6.QtGui import QFontMetrics,QFont
    from app import MainWindow
    from mac_overlay import state,enforce
    app=QApplication.instance() or QApplication([]);app.setStyle('Fusion')
    out=Path(destination);out.mkdir(parents=True,exist_ok=True)
    w=MainWindow(warmup=False);screen=max(app.screens(),key=lambda s:s.geometry().x());rect=screen.geometry()
    w.screen_choice.setCurrentIndex(app.screens().index(screen));w.move(rect.x()+30,rect.y()+30);w.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    dual='JP-VN' in w.windowTitle();checks={}
    if dual:
        from dual_translation import encode
        text=encode([{'ja':'薬学と化学、生命科学の連携が、新しい治療法の開発につながります。','vi':'Khi dược học, hóa học và khoa học sự sống phối hợp, chúng ta có thể phát triển những phương pháp điều trị mới.'}])
    else:
        text='When pharmacy, chemistry, life sciences, clinical research and data science work together, discoveries in the laboratory can lead to new treatments for patients.'
        checks['new_default']=w.caption_mode.currentIndex()==2
        pages=w.overlay.pages(text)
        checks['lossless']=' '.join(' '.join(pages).split())==text
        checks['two_lines']=all(len(p.splitlines())<=2 for p in pages) and any(len(p.splitlines())==2 for p in pages)
        checks['fits_width']=all(QFontMetrics(w.overlay.label.font()).horizontalAdvance(line)<=w.overlay.max_text_width for p in pages for line in p.splitlines())
        text=next(p for p in pages if len(p.splitlines())==2)
    checks['background_default']=w.caption_background.currentIndex()==0
    from event_data import EVENT_DATA
    from speech_hints import build_hints
    checks['generic_context']=EVENT_DATA=={'profiles':[], 'common':'', 'event':''} and build_hints()==[] and not w.context.use_documents.isChecked()
    w.overlay.advance_text(text)
    checks['display_all_lines']=w.overlay.label.text()==text if not dual else len(w.overlay.label.rows)==2
    checks['compact_height']=w.overlay.height()<=3*(QFontMetrics(QFont('Segoe UI',w.font_size.value())).lineSpacing()+4)+12
    checks['wide']=abs(w.overlay.width()-int(rect.width()*.88))<=1
    for position in range(3):
        w.position.setCurrentIndex(position);checks['position_'+str(position)]=rect.contains(w.overlay.geometry())
    w.position.setCurrentIndex(0)
    for index,alpha in enumerate((0,25,55)):
        w.caption_background.setCurrentIndex(index);checks['background_'+str(index)]=w.overlay.label.background_alpha==alpha
    w.caption_background.setCurrentIndex(0)
    canvas=QWidget();canvas.setWindowTitle('Stable Captions · readable layout validation');canvas.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating);canvas.setWindowFlags(Qt.WindowType.FramelessWindowHint|Qt.WindowType.Tool);canvas.setGeometry(rect);canvas.setStyleSheet('background:white;color:#193a60')
    layout=QVBoxLayout(canvas);layout.setContentsMargins(50,35,50,35)
    for content in ['Natural products and drug discovery','Pharmacy · Chemistry · Life sciences','Clinical research and data science','Scientific content remains visible behind the captions']:
        label=QLabel(content);label.setStyleSheet('font-size:32px;background:white');layout.addWidget(label)
    canvas.show();w.overlay.show();enforce(w.overlay)
    def finish():
        image=w.overlay.grab().toImage();transparent=sum(image.pixelColor(x,y).alpha()==0 for x in range(0,image.width(),3) for y in range(0,image.height(),3));total=len(range(0,image.width(),3))*len(range(0,image.height(),3))
        # Font density varies by display size. Compare the same glyphs with/without
        # the filled background instead of requiring an arbitrary empty-area ratio.
        w.caption_background.setCurrentIndex(2)
        filled=w.overlay.grab().toImage()
        removed=sum(image.pixelColor(x,y).alpha()==0 and filled.pixelColor(x,y).alpha()>0
                    for x in range(0,image.width(),3) for y in range(0,image.height(),3))
        w.caption_background.setCurrentIndex(0)
        checks['background_absent']=removed>50
        native=state(w.overlay);checks['native_topmost']=(native.get('level',0)>0 and native.get('click_through',False)) if sys.platform=='darwin' else bool(w.overlay.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        w.overlay.grab().save(str(out/'caption.png'));screen.grabWindow(0).save(str(out/'presentation.png'))
        w.show();w.grab().save(str(out/'settings.png'));w.hide()
        w.overlay.reset_text();checks['clear']=w.overlay.label.text()==''
        report={'pass':all(checks.values()),'packaged':bool(getattr(sys,'frozen',False)),'checks':checks,'native':native,'screen':rect.getRect(),'geometry':w.overlay.geometry().getRect(),'transparent_fraction':round(transparent/total,3),'background_removed_samples':removed,'source':'offline layout validation; no microphone or cloud API calls'}
        (out/'layout-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
        w.close();canvas.close();app.exit(0 if report['pass'] else 1)
    QTimer.singleShot(1000,finish)
    return app.exec()
