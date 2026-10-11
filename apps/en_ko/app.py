"""Stable Captions: commit stable speech clauses without revising displayed captions."""
import sys
import threading
import time
import re

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QSettings, QUrl, QRectF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QFont, QFontMetrics, QDesktopServices, QPainter, QPainterPath, QColor, QPen
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
    QPlainTextEdit, QMessageBox, QFileDialog,
)
from caption_cleanup import clean_fillers, idle_due
from caption_logic import CaptionQueue, split_caption, short_phrases, semantic_lines, reading_interval, sentence_pages
from context_ui import ContextController
from caption_safety import protect_caption
from stable_prefix import StablePrefix
from output_language import has_hangul
from embedded_config import SPEECH_KEY, SPEECH_REGION


class SpeechWorker(QThread):
    activity = Signal()
    ready = Signal()
    final = Signal(str, str, str)
    partial = Signal(str, str, str)
    timing = Signal(object)
    hints_status = Signal(str)
    status = Signal(str)
    failed = Signal(str)

    def __init__(self, key, region, silence_ms, wav_path=None, realtime=False, early=True, prepared=None):
        super().__init__()
        self.prepared_speech = prepared
        self.key, self.region = key, region
        self.silence_ms, self.wav_path = silence_ms, wav_path
        self.stop_event = threading.Event()
        self.realtime = realtime
        self.early = early
        self.prefix = StablePrefix()
        self.hints_lock=threading.Lock();self.pending_hints=None

    def set_hints(self, phrases):
        with self.hints_lock:self.pending_hints=tuple(phrases)

    def apply_hints(self, grammar):
        with self.hints_lock:
            phrases=self.pending_hints;self.pending_hints=None
        if phrases is None:return
        try:
            grammar.clear()
            for phrase in phrases:grammar.addPhrase(phrase)
            grammar.setWeight(1.0)
            self.hints_status.emit(f'받아쓰기 용어 {len(phrases)}개 등록 · 다음 인식 구간부터 참고')
            self.timing.emit({'phrase_hints_count':len(phrases)})
        except Exception:
            self.hints_status.emit('받아쓰기 용어 등록 실패 · 기본 인식 사용')
            self.timing.emit({'phrase_hints_error':True})

    def stop(self):
        self.stop_event.set()

    def run(self):
        recognizer = None
        try:
            import azure.cognitiveservices.speech as speechsdk
            from speech_connection import make_config
            config, language_config = make_config(self.key, self.region, self.silence_ms)
            if self.prepared_speech:
                audio = self.prepared_speech.audio
            elif self.realtime and self.wav_path:
                import wave
                wav=wave.open(self.wav_path,'rb')
                push=speechsdk.audio.PushAudioInputStream(speechsdk.audio.AudioStreamFormat(samples_per_second=wav.getframerate(),bits_per_sample=16,channels=1))
                audio=speechsdk.audio.AudioConfig(stream=push)
            else:
                audio = (speechsdk.audio.AudioConfig(filename=self.wav_path) if self.wav_path
                     else speechsdk.audio.AudioConfig(use_default_microphone=True))
            recognizer = self.prepared_speech.recognizer if self.prepared_speech else speechsdk.translation.TranslationRecognizer(
                translation_config=config, audio_config=audio,
                auto_detect_source_language_config=language_config)

            grammar=speechsdk.PhraseListGrammar.from_recognizer(recognizer)
            self.apply_hints(grammar)

            def recognizing(evt):
                if self.stop_event.is_set():return
                self.activity.emit()
                r=evt.result
                language=r.properties.get(speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult,'')
                if self.realtime and self.wav_path:
                    self.timing.emit({'partial_text':r.text,'language':language,'utterance':str(r.offset),'received':time.monotonic()})
                if self.early:
                    item=self.prefix.observe(str(r.offset),r.text,language,time.monotonic())
                    if item:
                        rid,piece,korean=item
                        self.status.emit('자동 감지: 한국어 · 안정 구절 번역' if korean else '자동 감지: 영어 · 안정 구절 표시')
                        english='' if korean else re.sub(r'\bi\b','I',piece[:1].upper()+piece[1:])
                        self.timing.emit({'early':True,'received':time.monotonic(),'utterance':str(r.offset),'piece':piece,'rid':rid})
                        self.final.emit(rid,english,piece if korean else '')
                if (language.startswith('ko') or any('가'<=c<='힣' for c in r.text)) and not self.prefix.states.get(str(r.offset),{}).get('committed'):
                    self.partial.emit(str(r.offset),r.translations.get('en',''),r.text)

            def recognized(evt):
                if self.stop_event.is_set():
                    return
                if evt.result.reason in (speechsdk.ResultReason.TranslatedSpeech, speechsdk.ResultReason.RecognizedSpeech):
                    language = evt.result.properties.get(speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult, '')
                    remaining,had_early,aligned=self.prefix.finish(str(evt.result.offset),evt.result.text)
                    if not aligned:
                        self.timing.emit({'alignment_failed':True});self.status.emit('인식 정정으로 일부 후속 자막을 연결하지 못했습니다.');return
                    if not remaining.strip():return
                    if language.startswith('en') and not has_hangul(remaining):
                        # Keep the speaker's English wording. Do not paraphrase through the model.
                        english, source = remaining, ''
                        self.status.emit('자동 감지: 영어 · 영어 원문 자막')
                    else:
                        english, source = ('' if had_early else evt.result.translations.get('en', '')), remaining
                        self.status.emit('자동 감지: 한국어 · 영어 번역 자막')
                    if english.strip() or source.strip():
                        self.timing.emit({'utterance':str(evt.result.offset),'offset':evt.result.offset/10000000,'duration':evt.result.duration/10000000,'received':time.monotonic()})
                        self.final.emit(str(evt.result.offset), english, source)

            def canceled(evt):
                if evt.reason == speechsdk.CancellationReason.Error:
                    # Never include the SDK's raw details or credentials in UI/logs.
                    code = str(getattr(evt, 'error_code', 'Unknown'))
                    self.failed.emit('Azure 연결 오류: ' + code + '\n키·지역, 인터넷, 무료 사용량을 확인하세요.')
                self.stop_event.set()

            recognizer.session_started.connect(lambda _: self.ready.emit() if not self.stop_event.is_set() else None)
            recognizer.recognized.connect(recognized)
            recognizer.recognizing.connect(recognizing)  # Internal preparation only; never shown.
            recognizer.canceled.connect(canceled)
            recognizer.session_stopped.connect(lambda _: self.stop_event.set())
            self.timing.emit({'preconnected_reused': self.prepared_speech is not None, 'connection_ready_at_start': bool(self.prepared_speech and self.prepared_speech.connected.is_set())})
            recognizer.start_continuous_recognition_async().get()
            if self.realtime and self.wav_path:
                def feed():
                    started=time.monotonic();self.timing.emit({'replay_started':started})
                    if sys.platform=='win32':
                        import winsound
                        winsound.PlaySound(self.wav_path,winsound.SND_FILENAME|winsound.SND_ASYNC)
                    frames=0
                    while not self.stop_event.is_set():
                        chunk=wav.readframes(320)
                        if not chunk:break
                        push.write(chunk);frames+=len(chunk)//2
                        self.stop_event.wait(max(0,started+frames/wav.getframerate()-time.monotonic()))
                    wav.close();push.close()
                feeder=threading.Thread(target=feed,daemon=True);feeder.start()
            while not self.stop_event.wait(.2):self.apply_hints(grammar)
        except Exception as exc:
            self.failed.emit('시작하지 못했습니다 (' + type(exc).__name__ + ').\n'
                             '마이크 권한·인터넷·키와 지역을 확인하세요.\n'
                             'DLL 오류라면 안내문의 Visual C++ 런타임을 설치하세요.')
        finally:
            if recognizer is not None:
                try:
                    recognizer.stop_continuous_recognition_async().get()
                except Exception:
                    pass
            if self.prepared_speech:self.prepared_speech.close()
            self.prepared_speech = None
            self.key = ''


class CaptionLabel(QLabel):
    """Fixed caption positions with a separate content-width background per row."""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(QRectF(0, 6, self.width(), self.height()-12))
        fm = QFontMetrics(self.font())
        entries = getattr(self, 'entries', [])
        slots = getattr(self, 'slots', 3)
        row = getattr(self, 'row_height', 100)
        progress = getattr(self, 'progress', 1.0)
        for i, text in enumerate(entries):
            y = 6 + (slots-len(entries)+i+1-progress)*row
            age = len(entries)-1-i
            color = QColor('white') if age == 0 or not getattr(self, 'dim_history', True) else QColor('#c4ccd5' if age == 1 else '#939eac')
            painter.setFont(self.font())
            for j, line in enumerate(text.splitlines()[:1]):
                if not line.strip():continue
                text_width = fm.horizontalAdvance(line)
                x = max(24, (self.width()-text_width)/2)
                box_width = min(self.width()-24, text_width+24)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(12, 17, 24, getattr(self, 'background_alpha', 0)))
                painter.drawRoundedRect(QRectF((self.width()-box_width)/2, y,
                                               box_width, row-2), 7, 7)
                path = QPainterPath()
                path.addText(x, y+fm.ascent()+j*(fm.lineSpacing()+6), self.font(), line)
                painter.setPen(QPen(QColor(0, 0, 0, 220), 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                painter.setBrush(color)
                painter.drawPath(path)
                painter.fillPath(path, color)


class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Stable Captions — 자막')
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.WindowDoesNotAcceptFocus |
                            Qt.WindowType.WindowTransparentForInput)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.label = CaptionLabel('', self)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.font_size = 32
        self.screen_rect = QApplication.primaryScreen().geometry()
        self.position = 0
        self.max_text_width = 800
        self.rollup = False
        self.two_line = False
        self.background_alpha = 0
        self.short_chunks = True
        self.current_text = ''
        self.previous_text = ''
        self.history_rows = []
        self.animation = QVariantAnimation(self)
        self.animation.setDuration(240)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.animation.valueChanged.connect(self.animate)
        self.animation.finished.connect(self.finish_animation)
        self.show_text('')

    def animate(self, value):
        self.label.progress = float(value)
        self.label.update()

    def finish_animation(self):
        self.label.entries = self.label.entries[-self.label.slots:]
        self.label.progress = 1.0
        self.label.update()

    def arrange(self, screen, size, position):
        self.font_size, self.position = size, position
        self.screen_rect = screen.geometry()
        self.show_text(self.current_text)

    def pages(self, text):
        if self.two_line:
            return sentence_pages(text, QFontMetrics(self.label.font()).horizontalAdvance, self.max_text_width)
        if self.short_chunks:
            return semantic_lines(text, QFontMetrics(self.label.font()).horizontalAdvance, self.max_text_width)
        units = [text]
        return [line for unit in units for page in split_caption(unit, QFontMetrics(self.label.font()).horizontalAdvance,
                                              self.max_text_width) for line in page.splitlines()]

    def advance_text(self, text):
        had_previous = bool(self.current_text)
        self.previous_text = self.current_text
        self.history_rows = (self.history_rows+[text])[-4:]
        self.current_text = text
        self.render()
        if self.rollup and had_previous:
            self.label.progress = 0.0
            self.animation.start()

    def reset_text(self, text=''):
        self.animation.stop()
        self.previous_text = ''
        self.history_rows = [text] if text else []
        self.current_text = text
        self.render()

    def show_text(self, text):
        self.current_text = text
        self.render()

    def render(self):
        self.animation.stop()
        self.label.setFont(QFont('Segoe UI', self.font_size))
        fm = QFontMetrics(self.label.font())
        rect = self.screen_rect
        width = max(180, int(rect.width()*.88))
        self.max_text_width = width-48
        slots = 2 if self.two_line else (3 if self.rollup else 1)
        row_height = fm.lineSpacing()+4
        height = slots*row_height+12
        self.setGeometry(rect.x()+(rect.width()-width)//2,
                         rect.y()+(rect.height()-height)//2 if self.position == 2 else (rect.y()+24 if self.position == 1 else rect.bottom()-height-24),
                         width, height)
        self.label.setGeometry(0,0,width,height)
        source = self.history_rows if self.rollup else ([self.current_text] if self.current_text else [])
        # Normally rows are already paginated. Rewrap on a font/screen change without
        # shrinking letters or dropping words; retain the latest visible pages.
        entries = [line for text in source for page in self.pages(text) for line in page.splitlines()]
        if self.current_text and not source: entries = [line for page in self.pages(self.current_text) for line in page.splitlines()]
        self.label.entries = entries[-(slots+1):]
        self.label.slots = slots
        self.label.dim_history = self.rollup
        self.label.background_alpha = self.background_alpha
        self.label.row_height = row_height
        self.label.progress = 1.0
        visible = entries[-slots:]
        self.label.dim_lines = sum(len(x.splitlines()) for x in visible[:-1])
        self.label.setText('\n'.join(visible))
        self.label.update()


class MainWindow(QWidget):
    def __init__(self, warmup=True):
        super().__init__()
        self.setWindowTitle('Stable Captions · 한국어/영어 → 영어·한국어 자막')
        self.resize(660, 740)
        self.settings = QSettings('LocalTools', 'StableCaptions')
        self.last_activity = 0.0
        self.worker = None
        self.closing = False
        self.prepared_speech = None
        self.preparation = None
        self.preparation_result = None
        self.session_number = 0
        self.queue = CaptionQueue()
        self.overlay = Overlay()
        from mac_overlay import install
        install(self.overlay)
        root = QVBoxLayout(self)
        title = QLabel('Stable Captions')
        title.setStyleSheet('font-size: 26px; font-weight: 700;')
        root.addWidget(title)
        intro = QLabel('선택한 언어로 안정된 구절부터 자막을 표시하며, 이미 표시한 문구는 수정하지 않습니다. 현재 문장을 최대 두 줄에 함께 표시합니다. 배경과 표시 방식은 선택할 수 있습니다.')
        intro.setWordWrap(True)
        root.addWidget(intro)
        form = QFormLayout()
        self.key = QLineEdit()
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key.setText(SPEECH_KEY)
        self.key.setPlaceholderText('본인의 Azure Speech 키를 입력하세요')
        self.region = QLineEdit(SPEECH_REGION)
        form.addRow('Azure 키', self.key)
        form.addRow('지역', self.region)
        self.output_language = QComboBox()
        self.output_language.addItem('영어 · 한국어/영어 → 영어', 'en')
        self.output_language.addItem('한국어 · 한국어/영어 → 한국어', 'ko')
        self.output_language.currentIndexChanged.connect(self.change_output_language)
        form.addRow('자막 언어', self.output_language)
        self.mic_button = QPushButton('Mac 마이크 권한 설정' if sys.platform=='darwin' else 'Windows 마이크 설정 열기')
        self.mic_button.clicked.connect(self.open_mic_settings)
        form.addRow('입력: 시스템 기본 마이크', self.mic_button)
        self.screen_choice = QComboBox()
        self.refresh_screens()
        form.addRow('자막을 표시할 화면', self.screen_choice)
        self.position = QComboBox()
        self.position.addItems(['화면 아래', '화면 위', '화면 가운데'])
        form.addRow('자막 위치', self.position)
        self.caption_background = QComboBox()
        self.caption_background.addItems(['배경 없음 · 글자 테두리 (권장)', '아주 옅은 배경', '반투명 배경'])
        self.caption_background.currentIndexChanged.connect(self.change_background)
        form.addRow('자막 배경', self.caption_background)
        self.caption_mode = QComboBox()
        self.caption_mode.addItems(['현재 자막 한 줄', '프롬프터 · 최근 3줄 자막', '현재 문장 · 최대 2줄 (권장)'])
        self.caption_mode.setCurrentIndex(2)
        self.caption_mode.currentIndexChanged.connect(self.change_caption_mode)
        form.addRow('자막 표시 방식', self.caption_mode)
        self.readable = QCheckBox('문장과 의미 단위를 유지해 줄 나누기')
        self.readable.setChecked(True)
        self.readable.toggled.connect(self.change_readability)
        form.addRow('읽기 편의', self.readable)
        self.font_size = QSpinBox()
        self.font_size.setRange(16, 64)
        self.font_size.setValue(32)
        self.font_size.setSuffix(' pt')
        form.addRow('글자 크기', self.font_size)
        self.hold = QDoubleSpinBox()
        self.hold.setRange(0, 10)
        self.hold.setSingleStep(.5)
        self.hold.setValue(1.0)
        self.hold.setSuffix(' 초')
        form.addRow('최소 줄 전환 간격', self.hold)
        self.silence = QSpinBox()
        self.silence.setRange(300, 1000)
        self.silence.setSingleStep(100)
        self.silence.setValue(500)
        self.silence.setSuffix(' ms')
        form.addRow('발화 종료 대기', self.silence)
        root.addLayout(form)
        note = QLabel('마이크는 시스템 설정에서 선택 후 시작하세요. 연속 발화는 안정된 앞부분부터 표시합니다. 표시된 자막은 수정하지 않습니다.\n'
                      '시작하면 음성이 Azure로 전송됩니다. 음성은 저장하지 않습니다. 본인의 Azure 계정으로 연결합니다. 공개 배포본에는 키가 없습니다.')
        note.setWordWrap(True)
        note.setStyleSheet('color: #475569; font-size: 12px;')
        root.addWidget(note)
        row = QHBoxLayout()
        self.start_button = QPushButton('번역 시작')
        self.start_button.setStyleSheet('background: #2563eb; color: white; padding: 10px;')
        self.stop_button = QPushButton('중지')
        self.stop_button.setEnabled(False)
        self.demo_button = QPushButton('자막 미리보기 (무료)')
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.demo_button)
        root.addLayout(row)
        self.start_button.clicked.connect(lambda: self.start())
        self.stop_button.clicked.connect(self.stop)
        self.demo_button.clicked.connect(self.demo)
        row = QHBoxLayout()
        self.visible = QCheckBox('자막 창 표시')
        self.visible.setChecked(True)
        self.visible.toggled.connect(self.toggle_overlay)
        clear = QPushButton('자막·기록 지우기')
        clear.clicked.connect(self.clear)
        self.wav_button = QPushButton('WAV 파일로 번역 테스트')
        self.wav_button.clicked.connect(self.start_wav)
        row.addWidget(self.visible)
        row.addWidget(clear)
        row.addWidget(self.wav_button)
        root.addLayout(row)
        self.status_label = QLabel('대기 중 · 미리보기는 Azure에 연결하지 않습니다')
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)
        self.ready_label = QLabel('대기 · 번역 시작 후 연결 상태를 확인합니다')
        self.ready_label.setWordWrap(True)
        self.ready_label.setStyleSheet('color:#475569;font-weight:600')
        root.addWidget(self.ready_label)
        self.backlog = QLabel('표시 대기: 0문장')
        root.addWidget(self.backlog)
        root.addWidget(QLabel('이번 실행의 확정 결과 (앱 종료 시 삭제)'))
        self.history = QPlainTextEdit()
        self.history.setReadOnly(True)
        self.history.setMaximumBlockCount(300)
        root.addWidget(self.history)
        for widget in (self.screen_choice, self.position):
            widget.currentIndexChanged.connect(self.arrange)
        self.font_size.valueChanged.connect(self.arrange)
        QApplication.instance().screenAdded.connect(self.screens_changed)
        QApplication.instance().screenRemoved.connect(self.screens_changed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(100)
        self.context = ContextController(self)
        context_button = QPushButton('슬라이드 화면 분석 · 맥락 번역 설정')
        context_button.clicked.connect(self.context.dialog.show)
        root.insertWidget(2, context_button)
        save_config = QPushButton('내 Azure 설정 저장')
        save_config.clicked.connect(self.save_azure_settings)
        root.addWidget(save_config)
        self.arrange()
        if warmup:
            QTimer.singleShot(0, self.prepare_connections)

    def save_azure_settings(self):
        from runtime_config import save_settings
        c = self.context
        settings = {'speech': {'key': self.key.text().strip(), 'region': self.region.text().strip()},
                    'model': {'endpoint': c.model_endpoint.text().strip(), 'key': c.model_key.text().strip(), 'deployment': c.deployment.text().strip()},
                    'vision': {'endpoint': c.vision_endpoint.text().strip(), 'key': c.vision_key.text().strip()}}
        try:
            path = save_settings(settings)
        except Exception:
            QMessageBox.warning(self, '설정 저장 실패', '설정 폴더의 쓰기 권한을 확인하세요.'); return
        c.use_translation.setChecked(bool(settings['model']['key'] and settings['model']['deployment'] and settings['model']['endpoint']))
        QMessageBox.information(self, '설정 저장 완료', '이 PC에 설정을 저장했습니다. 파일을 공유하지 마세요.\n' + str(path))
        self.prepare_connections()

    def prepare_connections(self):
        if not self.key.text().strip() or not self.region.text().strip():
            self.ready_label.setText('본인의 Azure 설정을 입력한 뒤 저장하세요')
            return
        if self.closing or self.preparation is not None:
            return
        from startup_preparation import PreparationWorker
        from context_ui import translate_with_context
        c = self.context
        args = (c.model_endpoint.text().strip(), c.model_key.text().strip(),
                c.deployment.text().strip(), '안녕하세요.', '', '', [], '')
        self.ready_label.setText('사전 연결 준비 중 · 마이크는 아직 꺼져 있습니다')
        self.preparation = PreparationWorker(self.region.text().strip(), translate_with_context, args, self, key=self.key.text().strip(), silence_ms=self.silence.value())
        self.preparation.completed.connect(self.prepared)
        self.preparation.finished.connect(self.preparation_finished)
        self.preparation.start()

    def prepared(self, result):
        if self.preparation is not None:
            resource = self.preparation.speech
            self.preparation.speech = None
            if self.closing or self.worker is not None:
                if resource:resource.close()
            else:
                if self.prepared_speech:self.prepared_speech.close()
                self.prepared_speech = resource
        self.preparation_result = result
        if self.worker is None and not self.closing:
            self.ready_label.setText('사전 준비 완료 · 번역 시작을 누르세요' if all(result.values())
                                    else '일부 사전 연결을 확인하지 못했습니다 · 시작 시 다시 연결합니다')

    def preparation_finished(self):
        self.preparation.deleteLater()
        self.preparation = None
        if self.closing:
            self.close()

    def speech_ready(self, session):
        if session != self.session_number or self.worker is None or self.worker.stop_event.is_set():
            return
        self.ready_label.setText('준비 완료 · 말씀하세요')
        self.ready_label.setStyleSheet('color:#15803d;font-weight:700')

    def refresh_screens(self):
        self.screen_choice.clear()
        for i, screen in enumerate(QApplication.screens()):
            self.screen_choice.addItem(f'{i + 1}. {screen.name()} ({screen.size().width()}×{screen.size().height()})')

    def screens_changed(self, _screen):
        self.refresh_screens()
        self.arrange()

    def change_output_language(self, index):
        # Language changes are allowed only between sessions; drop old async replies.
        self.session_number += 1
        self.clear()
        korean = self.output_language.currentData() == 'ko'
        self.context.use_translation.setText('현재 발화와 슬라이드를 참고한 맥락 번역')
        self.status_label.setText('한국어 출력 · 한국어는 원문 표시, 영어는 한국어 번역' if korean else '영어 출력 · 영어는 원문 표시, 한국어는 영어 번역')

    def change_background(self, index):
        self.overlay.background_alpha = (0, 25, 55)[index]
        self.overlay.show_text(self.overlay.current_text)

    def change_readability(self, enabled):
        self.overlay.short_chunks = enabled
        self.overlay.show_text(self.overlay.current_text)

    def change_caption_mode(self, index):
        self.overlay.rollup = index == 1
        self.overlay.two_line = index == 2
        self.overlay.show_text(self.overlay.current_text)

    def arrange(self, *_):
        screens = QApplication.screens()
        index = max(0, min(self.screen_choice.currentIndex(), len(screens) - 1))
        self.overlay.rollup = self.caption_mode.currentIndex() == 1
        self.overlay.two_line = self.caption_mode.currentIndex() == 2
        self.overlay.arrange(screens[index], self.font_size.value(), self.position.currentIndex())

    def open_mic_settings(self):
        if sys.platform == 'win32':
            QDesktopServices.openUrl(QUrl('ms-settings:sound'))
        elif sys.platform == 'darwin':
            QDesktopServices.openUrl(QUrl('x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone'))
        else:
            QMessageBox.information(self, '기본 마이크', '시스템 사운드 설정에서 기본 입력 마이크를 선택하세요.')

    def toggle_overlay(self, visible):
        self.overlay.setVisible(visible)

    def demo(self):
        self.queue.reset()
        self.overlay.reset_text()
        self.queue.accept('preview', '자막 미리보기입니다. 확정된 자막은 다음 문장이 나올 때까지 유지됩니다.' if self.output_language.currentData() == 'ko' else 'This is a preview. Final translations stay unchanged until the next caption.')
        self.tick()
        self.visible.setChecked(True)
        self.overlay.show()

    def clear(self):
        self.queue.reset()
        self.context.reset()
        self.overlay.reset_text('')
        self.history.clear()

    def start_wav(self):
        path, _ = QFileDialog.getOpenFileName(self, '한국어/영어 WAV 선택', '', 'WAV audio (*.wav)')
        if path:
            self.start(path)

    def start(self, wav_path=None, realtime=False):
        if self.worker is not None:
            return
        key, region = self.key.text().strip(), self.region.text().strip()
        if not key or not region:
            QMessageBox.information(self, 'Azure 설정', '키와 지역을 입력하세요. Speech 리소스를 만든 지역 코드를 입력하세요.')
            return
        self.settings.setValue('region', region)
        self.context.reset()
        self.session_number += 1
        session = self.session_number
        self.queue.reset()
        self.overlay.reset_text('')
        self.arrange()
        self.overlay.setVisible(self.visible.isChecked())
        self.status_label.setText('Azure에 연결하는 중…')
        self.ready_label.setText('음성 연결 중 · 잠시 기다려주세요')
        self.ready_label.setStyleSheet('color:#92400e;font-weight:600')
        self.set_running(True)
        prepared = self.prepared_speech
        self.prepared_speech = None
        if prepared and (wav_path or prepared.signature != (key, region, self.silence.value())):
            prepared.close();prepared = None
        self.worker = SpeechWorker(key, region, self.silence.value(), wav_path, realtime=realtime, prepared=prepared)
        self.worker.activity.connect(lambda: self.speech_activity(session))
        self.worker.ready.connect(lambda: self.speech_ready(session))
        self.worker.hints_status.connect(self.context.hints_note.setText)
        self.context.hints_key=None
        self.context.sync_hints()
        self.worker.final.connect(lambda rid, en, ko: self.receive(session, rid, en, ko))
        self.worker.partial.connect(lambda uid,en,ko: self.context.partial(uid,en,ko) if session==self.session_number else None)
        self.worker.status.connect(lambda text: self.status_label.setText('음성 인식 중 · 한국어 출력' if self.output_language.currentData() == 'ko' else text))
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.worker_done)
        self.worker.start()

    def speech_activity(self, session):
        if session == self.session_number:
            self.last_activity = time.monotonic()

    def expire_idle_caption(self):
        busy = bool(self.queue.pending or self.context.pending or self.context.clauses.held)
        if idle_due(time.monotonic(), self.last_activity, self.queue.shown_at, busy, self.queue.next_at):
            self.overlay.reset_text('')
            self.queue.shown_at = None

    def receive(self, session, rid, english, korean):
        if session != self.session_number:
            return
        self.speech_activity(session)
        self.context.translate(rid, english, korean, lambda r,e,k: self.deliver(session,r,e,k), utterance=rid)

    def deliver(self, session, rid, english, korean):
        if session != self.session_number:
            return
        if self.output_language.currentData() == 'en' and has_hangul(english):
            self.status_label.setText('영어 번역을 완료하지 못해 해당 구절을 생략했습니다.')
            return
        if self.output_language.currentData() == 'ko':
            from korean_output import valid_korean_caption
            if not valid_korean_caption(english):
                self.status_label.setText('한국어 번역을 완료하지 못해 해당 구절을 생략했습니다.')
                return
        english = clean_fillers(english)
        english, korean, blocked = protect_caption(english, korean)
        if blocked and self.output_language.currentData() == 'ko':english = '[자막 생략]'
        if blocked:self.status_label.setText('표현 보호: 부적절하거나 가려진 표현이 포함된 자막을 생략했습니다.')
        if self.queue.accept(rid, english):
            self.history.appendPlainText((korean + '\n' if korean else '[입력 발화]\n') + english + '\n')

    def tick(self):
        self.expire_idle_caption()
        readable = self.readable.isChecked()
        text = self.queue.take(time.monotonic(), self.hold.value(), catch_up=self.overlay.rollup and not readable)
        if text is not None:
            self.overlay.label.setFont(QFont('Segoe UI', self.font_size.value()))
            pages = self.overlay.pages(text)
            self.queue.pending.extendleft(reversed(pages[1:]))
            self.overlay.advance_text(pages[0])
            interval = (reading_interval(pages[0], max(1.0,self.hold.value())) if readable
                        else (min(self.hold.value(),1.0) if len(self.queue.pending)>2 else self.hold.value()))
            if self.overlay.two_line:
                interval = max(self.hold.value(), min(3.0, 1.2 + len(pages[0].split()) * .08))
                if len(self.queue.pending) > 2: interval = min(interval, 2.0)
            self.queue.next_at = time.monotonic()+interval
        count = len(self.queue.pending)
        message = f'표시 대기: {count}개'
        if count > 3:
            message += (' · 읽는 시간을 유지하여 자막이 뒤따르고 있습니다.' if readable
                        else ' · 지연이 쌓이고 있습니다. 대기 자막을 빠르게 표시합니다.')
        self.backlog.setText(message)

    def stop(self):
        self.overlay.reset_text('')
        self.queue.reset()
        self.ready_label.setText('중지 중 · 말씀하세요 표시가 꺼졌습니다')
        self.ready_label.setStyleSheet('color:#475569;font-weight:600')
        self.context.reset()
        if self.worker:
            self.session_number += 1  # Ignore callbacks already in the GUI event queue.
            self.queue.pending.clear()
            self.stop_button.setEnabled(False)
            self.worker.stop()
            self.status_label.setText('마이크·Azure 연결을 중지하는 중…')

    def on_error(self, message):
        self.ready_label.setText('연결 오류 · 준비되지 않았습니다')
        self.ready_label.setStyleSheet('color:#b91c1c;font-weight:600')
        self.status_label.setText(message)

    def worker_done(self):
        self.worker.deleteLater()
        self.worker = None
        self.ready_label.setText('중지됨 · 다시 시작할 수 있습니다')
        self.ready_label.setStyleSheet('color:#475569;font-weight:600')
        self.set_running(False)
        if '오류' not in self.status_label.text() and '못했습니다' not in self.status_label.text():
            self.status_label.setText('중지됨 · 발언이 없으면 자막은 5초 후 사라집니다')
        if self.closing:
            self.close()
        else:
            QTimer.singleShot(0, self.prepare_connections)

    def set_running(self, running):
        for control in (self.start_button, self.demo_button, self.wav_button,
                        self.key, self.region, self.silence, self.mic_button, self.output_language):
            control.setEnabled(not running)
        self.stop_button.setEnabled(running)

    def closeEvent(self, event):
        self.closing = True
        if self.preparation is not None:
            event.ignore()
            if self.worker is not None: self.stop()
            return
        if self.worker is not None:
            self.closing = True
            self.stop()
            self.status_label.setText('연결 종료 후 앱이 닫힙니다…')
            event.ignore()
            return
        if not self.context.shutdown():
            event.ignore()
            QTimer.singleShot(200, self.close)
            return
        if self.prepared_speech:
            self.prepared_speech.close();self.prepared_speech = None
        self.key.clear()
        self.overlay.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI', 10))
    window = MainWindow()
    if '--right-screen' in sys.argv:
        screens = app.screens()
        screen = max(screens, key=lambda item: item.geometry().x())
        window.screen_choice.setCurrentIndex(screens.index(screen))
        area = screen.availableGeometry()
        window.move(area.x() + max(0, (area.width()-window.width())//2), area.y()+30)
        window.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-korean':
        from korean_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-generic':
        from generic_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-layout':
        from layout_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-preconnect':
        from preconnect_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-images':
        from visual_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--verify-release':
        from release_validation import run
        sys.exit(run(sys.argv[2]))
    if len(sys.argv) == 3 and sys.argv[1] == '--validate':
        from windows_validation import run
        sys.exit(run(sys.argv[2]))
    main()
