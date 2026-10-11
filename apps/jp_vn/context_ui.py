from caption_cleanup import clean_sources
"""Slide OCR runs independently from the live speech recognizer."""
import sys
import threading
import time
from PySide6.QtCore import QObject, QThread, Signal, QTimer, QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage, QPainter, QColor, QPixmap
from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton, QLabel, QVBoxLayout, QCheckBox, QPlainTextEdit, QComboBox
from slide_changes import SlideChangeTracker
from speech_hints import build_hints
from utterance_units import ClauseBuffer
from speculation import Speculation
from caption_safety import flagged, protect_caption
from event_reference import PROFILES, reference_for, SlideIndex, prepared_translation_for
from slide_context import read_slide, ServiceError, azure_endpoint
from dual_translation import translate_with_context, encode, OMITTED_PAIR, unsafe


class RequestWorker(QThread):
    done = Signal(object)
    def __init__(self, fn):
        super().__init__()
        self.fn = fn
    def run(self):
        try:
            self.done.emit((True, self.fn()))
        except Exception:
            self.done.emit((False, '서비스 요청 실패 또는 시간 초과'))
        finally:
            self.fn = None


class ContextController(QObject):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.text = ''
        self.slide_image = b''
        self.image_revision = 0
        self.image_sent_count = 0
        self.slide_index = SlideIndex()
        self.metrics = []
        self.speculation = Speculation()
        self.hints_key=None
        self.active = False
        self.generation = 0
        self.session = 0
        self.jobs = set()
        self.ocr_job = None
        self.cancel = threading.Event()
        self.change_tracker = SlideChangeTracker()
        self.stable_since = 0
        self.last_sent = None
        self.next_request = 0
        self.previous = []
        self.displayed_pairs=[]
        self.clauses=ClauseBuffer()
        self.pending = {}
        self.next_id = 0
        self.owner.screen_choice.currentIndexChanged.connect(lambda _: self.reset_screen())
        self.owner.position.currentIndexChanged.connect(lambda _: self.reset_screen())
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.capture)
        self.timer.start(1000)
        self.dispatch = QTimer(self)
        self.dispatch.timeout.connect(self.sync_hints)
        self.dispatch.timeout.connect(self.flush_clause)
        self.dispatch.timeout.connect(self.flush)
        self.dispatch.timeout.connect(self.try_speculation)
        self.dispatch.start(50)
        self.dialog = QDialog(owner)
        self.dialog.setWindowTitle('슬라이드 맥락 설정')
        self.dialog.resize(680, 680)
        layout = QVBoxLayout(self.dialog)
        info = QLabel('선택한 화면 전체를 이미지로 번역 모델에 전달해 사진·도표·구조식·글자를 함께 참고합니다.\n'
                      '자막 패널만 가리며 화면 위·아래를 통째로 자르지 않습니다. 앱 설정창이 같은 화면에 보이면 캡처를 쉽니다.\n'
                      '화면 분석을 켜면 이미지가 Azure 번역 모델로 전송되고, 문자 힌트용으로 Azure Vision도 사용합니다.\n'
                      '작은 포인터 움직임은 무시하며 약 15초마다 이미지를 갱신합니다. 이미지는 메모리에만 유지합니다.\n'
                      '화면에 보이는 내용을 임의로 자막에 덧붙이지 않고 실제 발화를 우선합니다.')
        info.setWordWrap(True); layout.addWidget(info)
        form = QFormLayout(); layout.addLayout(form)
        self.vision_endpoint = QLineEdit(); self.vision_key = QLineEdit()
        self.model_endpoint = QLineEdit(); self.model_key = QLineEdit(); self.deployment = QLineEdit()
        for field in (self.vision_key, self.model_key): field.setEchoMode(QLineEdit.EchoMode.Password)
        self.vision_endpoint.setPlaceholderText('https://리소스.cognitiveservices.azure.com')
        self.model_endpoint.setPlaceholderText('https://리소스.openai.azure.com')
        for label, field in [('Vision 엔드포인트', self.vision_endpoint), ('Vision 키', self.vision_key),
                             ('번역 모델 엔드포인트', self.model_endpoint), ('번역 모델 키', self.model_key), ('모델 배포 이름', self.deployment)]:
            form.addRow(label, field)
        self.use_translation = QCheckBox('일본어 + 베트남어 번역 · 사전 자료와 슬라이드 참고')
        layout.addWidget(self.use_translation)
        self.use_speculation = QCheckBox("발화 확정 전 번역 준비 · 추가 호출 최대 2회/발화")
        self.use_speculation.setChecked(False)
        self.use_speculation.hide()
        layout.addWidget(self.use_speculation)
        try:
            from context_config import CONTEXT_CONFIG
            v, m = CONTEXT_CONFIG.get('vision', {}), CONTEXT_CONFIG.get('model', {})
            self.vision_endpoint.setText(v.get('endpoint', '')); self.vision_key.setText(v.get('key', ''))
            self.model_endpoint.setText(m.get('endpoint', '')); self.model_key.setText(m.get('key', ''))
            self.deployment.setText(m.get('deployment', ''))
            self.use_translation.setChecked(bool(m.get('key')))
        except ImportError:
            pass
        self.use_documents = QCheckBox('내장 사전 문맥 없음 · 범용 버전')
        self.use_documents.setChecked(bool(PROFILES))
        self.use_documents.setEnabled(bool(PROFILES))
        self.use_documents.hide()
        self.profile = QComboBox()
        self.profile.addItem('내장 문서 없음', 'auto')
        for p in PROFILES: self.profile.addItem(p['speaker']+' · '+p['title'],p['id'])
        self.profile.hide()
        self.profile.currentIndexChanged.connect(lambda _: self.reset())
        self.document_note = QLabel('표현 보호는 항상 켜져 있습니다. 비속어나 가려진 표현은 자막에서 생략합니다.\n행사 인사말·초록·연자 정보는 내장되어 있지 않습니다. 화면 분석은 별도로 켜세요.\n한국어·영어 모두 일본어와 베트남어로 번역합니다.')
        self.document_note.setWordWrap(True); layout.addWidget(self.document_note)
        self.toggle = QPushButton('화면 분석 시작'); self.toggle.clicked.connect(self.toggle_active); layout.addWidget(self.toggle)
        self.status = QLabel('화면 분석 꺼짐'); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.image_preview = QLabel('아직 전달할 이미지가 없습니다'); self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.image_preview.setMaximumHeight(120); layout.addWidget(self.image_preview)
        self.image_note = QLabel('이미지 미전달'); self.image_note.setWordWrap(True); layout.addWidget(self.image_note)
        self.preview = QPlainTextEdit(); self.preview.setReadOnly(True); layout.addWidget(self.preview)
        self.hints_note=QLabel('받아쓰기 용어는 번역 시작 시 자동 등록됩니다.');self.hints_note.setWordWrap(True);layout.addWidget(self.hints_note)
        self.use_translation.setChecked(True); self.use_translation.setEnabled(False)
        self.note = QLabel('화면 분석만으로 Azure 기본 번역에 맥락이 자동 적용되지는 않습니다.'); self.note.setWordWrap(True); layout.addWidget(self.note)

    def sync_hints(self):
        worker=getattr(self.owner,'worker',None)
        if worker is None:return
        key=(self.text if self.active else '',self.profile.currentData(),self.use_documents.isChecked())
        if key==self.hints_key:return
        self.hints_key=key
        worker.set_hints(build_hints(*key))

    def run_job(self, fn, callback):
        job = RequestWorker(fn)
        self.jobs.add(job)
        job.done.connect(callback)
        job.finished.connect(lambda: self.release(job))
        job.start()
        return job

    def release(self, job):
        self.jobs.discard(job)
        if self.ocr_job is job: self.ocr_job = None
        job.deleteLater()

    def reset(self):
        self.session += 1
        self.pending.clear()
        self.previous.clear()
        self.displayed_pairs.clear()
        self.clauses.reset()
        self.metrics.clear()
        self.speculation.reset()

    def toggle_active(self):
        if self.active:
            self.active = False; self.cancel.set(); self.generation += 1
            self.invalidate(); self.toggle.setText('화면 분석 시작'); self.status.setText('화면 분석 꺼짐')
            return
        try:
            azure_endpoint(self.model_endpoint.text())
            if not self.model_key.text().strip() or not self.deployment.text().strip(): raise ValueError()
            self.use_translation.setChecked(True)
        except Exception:
            self.status.setText('엔드포인트와 키, 모델 배포 이름을 확인하세요.'); return
        self.active = True; self.cancel = threading.Event(); self.last_sent = None; self.change_tracker = SlideChangeTracker()
        self.toggle.setText('화면 분석 중지'); self.status.setText('설정창과 앱을 최소화하면 발표 화면 분석을 시작합니다.')
        self.dialog.hide()
        self.owner.showMinimized()

    def capture(self):
        if not self.active: return
        screens = self.owner.screen().virtualSiblings()
        from PySide6.QtWidgets import QApplication
        screens = QApplication.screens()
        index = min(max(0, self.owner.screen_choice.currentIndex()), len(screens)-1)
        screen = screens[index]
        if self.dialog.isVisible() or (self.owner.isVisible() and not self.owner.isMinimized() and self.owner.frameGeometry().intersects(screen.geometry())):
            self.invalidate(keep_preview=True); self.image_note.setText(f'분석 일시 정지 · 마지막 이미지 표시 · 이미지 포함 번역 {self.image_sent_count}회'); self.status.setText('앱 설정창이 보여 분석을 일시 정지했습니다.'); return
        pixmap = screen.grabWindow(0)
        if pixmap.isNull():
            self.invalidate(); self.status.setText('화면 캡처를 사용할 수 없습니다.'); return
        img = pixmap.toImage()
        from slide_image import mask_caption, encode_image
        img=mask_caption(img,screen.geometry(),self.owner.overlay.frameGeometry())
        small = img.scaled(160, 90, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation).convertToFormat(QImage.Format.Format_Grayscale8)
        pixels = bytes(small.constBits())
        # Quantize to suppress small video/compositor noise.
        signature = bytes(v // 24 for v in pixels)
        now = time.monotonic()
        change = self.change_tracker.observe(signature, now)
        if change == 'changed':
            self.invalidate()
            return
        if change != 'scan' or self.ocr_job or now < self.next_request: return
        self.change_tracker.scanned(now)
        generation = self.generation
        self.next_request = now+4
        data,thumbnail=encode_image(img)
        self.slide_image=data;self.image_revision+=1
        self.image_preview.setPixmap(QPixmap.fromImage(thumbnail.scaled(320,120,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)))
        self.image_note.setText(f'현재 이미지 준비됨 · {thumbnail.width()}×{thumbnail.height()} · 다음 맥락 번역에 직접 첨부')
        endpoint,key = self.vision_endpoint.text().strip(),self.vision_key.text().strip()
        if not endpoint or not key:
            self.status.setText('이미지 준비됨 · Vision 문자 힌트는 설정하지 않았습니다')
            return
        cancel = self.cancel
        self.status.setText('슬라이드 이미지 준비됨 · 전문용어 문자 힌트 확인 중…')
        def result(value):
            if not self.active or generation != self.generation: return
            ok,text = value
            if ok:
                self.text = text
                self.slide_index.prepare(text)
                self.preview.setPlainText(self.text)
            self.status.setText('이미지 + 문자 힌트 준비됨' if ok and text else '이미지 준비됨 · 문자 힌트 없음 (그림은 번역에 전달됩니다)')
        self.ocr_job = self.run_job(lambda: read_slide(endpoint,key,data,cancel), result)

    def invalidate(self, keep_preview=False):
        self.generation += 1; self.text = ''; self.slide_image = b''; self.image_revision += 1
        self.change_tracker.last_scan = None
        if not keep_preview:
            self.preview.clear(); self.image_preview.clear(); self.image_note.setText('이미지 미전달 · 새 화면 확인 중' if self.active else '이미지 미전달')
        self.speculation.reset()

    def reset_screen(self):
        self.invalidate(); self.change_tracker=SlideChangeTracker(); self.next_request=0

    def context_key(self):
        return (tuple(self.previous), self.text, self.active, self.profile.currentData(), self.use_documents.isChecked(),
                self.use_translation.isChecked(), self.deployment.text(), self.model_endpoint.text(), self.image_revision)

    def partial(self, utterance, en, ko):
        if self.use_speculation.isChecked() and self.use_translation.isChecked() and ko.strip() and not flagged(ko) and not flagged(en):
            self.speculation.observe(utterance,ko,en,self.context_key(),time.monotonic())

    def try_speculation(self):
        if not self.use_speculation.isChecked() or not self.use_translation.isChecked():return
        c=self.speculation.ready(time.monotonic())
        if not c or c['key'][2]!=self.context_key() or len(self.jobs)>=2:return
        ko,en=c['text'],c['baseline']
        document=reference_for(ko,en,self.text,self.previous,self.profile.currentData(),screen_words=self.slide_index.prepare(self.text)) if self.use_documents.isChecked() else ''
        if not (document or (self.active and (self.text or self.slide_image))):return
        key=c['key'];self.speculation.begin(c);session=self.session
        args=(self.model_endpoint.text().strip(),self.model_key.text().strip(),self.deployment.text().strip(),ko,en,self.text,list(self.previous),document,list(self.displayed_pairs),self.slide_image if self.active else b'')
        def done(value):
            if session==self.session:self.speculation.finish(key,value)
        self.run_job(lambda:self.request_translation(args),done)

    def request_translation(self,args):
        return translate_with_context(*args)

    def flush_clause(self):
        if self.clauses.due(time.monotonic()):self.release_clause(self.clauses.pop())

    def release_clause(self,item):
        self.translate_unit(item['rid'],item['en'],item['ko'],item['deliver'],item['utterance'])

    def translate(self, rid, en, ko, deliver, utterance=None):
        en, ko = clean_sources(en, ko)
        if not (en or ko):return
        if flagged(ko) or flagged(en):
            if self.clauses.held:self.release_clause(self.clauses.pop())
            self.translate_unit(rid,en,ko,deliver,utterance);return
        for item in self.clauses.push(rid,en,ko,deliver,utterance,time.monotonic()):self.release_clause(item)

    def translate_unit(self, rid, en, ko, deliver, utterance=None):
        en, ko = clean_sources(en, ko)
        if not (en or ko):return
        started=time.monotonic(); ident=self.next_id; self.next_id+=1; session=self.session
        source=ko or en
        item={'rid':rid,'en':'','ko':ko,'deliver':deliver,'deadline':started+12.0,'started':started,'ready':False,'context_used':False}
        self.pending[ident]=item
        if unsafe(source):
            item.update(en=encode([OMITTED_PAIR]),ready=True); self.flush(); return
        document=reference_for(ko,en,self.text,self.previous,self.profile.currentData(),screen_words=self.slide_index.prepare(self.text)) if self.use_documents.isChecked() else ''
        args=(self.model_endpoint.text().strip(),self.model_key.text().strip(),self.deployment.text().strip(),ko,en,self.text,list(self.previous),document,list(self.displayed_pairs),self.slide_image if self.active else b'')
        self.previous=(self.previous+[source])[-3:]
        def result(value):
            if session!=self.session or ident not in self.pending:return
            ok,text=value; entry=self.pending[ident]
            if ok and time.monotonic()<=entry['deadline']:
                entry.update(en=text,context_used=True,image_used=bool(args[-1]))
                if args[-1]: self.image_sent_count+=1; self.image_note.setText(f'이미지 포함 번역 수신 · {self.image_sent_count}회')
            entry.update(request_seconds=time.monotonic()-started,ready=True)
            self.flush()
        item['launch']=lambda:self.run_job(lambda:self.request_translation(args),result)
        self.flush()

    def flush(self):
        for entry in self.pending.values():
            if 'launch' in entry and len(self.jobs)<3 and time.monotonic()<entry['deadline']:
                entry.pop('launch')()
        while self.pending:
            ident=next(iter(self.pending)); item=self.pending[ident]
            if not item['ready'] and time.monotonic()<item['deadline']: break
            del self.pending[ident]
            if 'started' in item:
                self.metrics.append({'wait_seconds':round(time.monotonic()-item['started'],3),
                                     'request_seconds':round(item.get('request_seconds',0),3),
                                     'context_used':item.get('context_used',False),'image_used':item.get('image_used',False),'speculative':item.get('speculative',False)})
                self.metrics=self.metrics[-200:]
            if not item['en'].strip():
                self.owner.status_label.setText('번역 응답 지연 또는 오류: 일부 자막을 표시하지 못했습니다.')
                continue
            item['deliver'](item['rid'],item['en'],item['ko'])
            self.displayed_pairs=(self.displayed_pairs+[{'source':item['ko'],'translations':item['en']}])[-2:]

    def shutdown(self):
        self.active=False; self.cancel.set(); self.invalidate(); self.reset()
        self.timer.stop(); self.dispatch.stop()
        self.dialog.close()
        # Owner must delay destruction until bounded requests have finished.
        return not self.jobs
