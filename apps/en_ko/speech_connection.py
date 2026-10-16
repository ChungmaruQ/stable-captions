"""Own a Speech SDK recognizer and its real service connection before recognition."""
import threading

def make_config(key, region, silence_ms, source_language='auto'):
    import azure.cognitiveservices.speech as speechsdk
    if source_language not in ('auto','ko-KR','en-US'):raise ValueError('Unsupported speech language')
    if source_language == 'auto':
        config = speechsdk.SpeechConfig(
            subscription=key, endpoint=f'wss://{region}.stt.speech.microsoft.com/speech/universal/v2')
        config.set_property(speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, 'Continuous')
        language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=['ko-KR', 'en-US'])
    else:
        config = speechsdk.SpeechConfig(subscription=key,region=region)
        config.speech_recognition_language = source_language
        language_config = None
    config.set_profanity(speechsdk.ProfanityOption.Masked)
    config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
                str(silence_ms))
    return config, language_config

class PreparedSpeech:
    def __init__(self, key, region, silence_ms, audio=None, source_language='auto'):
        import azure.cognitiveservices.speech as sdk
        self.signature = (key, region, silence_ms, source_language)
        self.connected = threading.Event()
        config, language = make_config(key, region, silence_ms, source_language)
        # Constructing a recognizer does not start recognition or microphone capture.
        self.audio = audio if audio is not None else sdk.audio.AudioConfig(use_default_microphone=True)
        self.recognizer = sdk.SpeechRecognizer(
            speech_config=config, audio_config=self.audio,
            auto_detect_source_language_config=language)
        self.connection = sdk.Connection.from_recognizer(self.recognizer)
        self.connection.connected.connect(lambda _: self.connected.set())
        self.connection.disconnected.connect(lambda _: self.connected.clear())
    def open(self):
        self.connection.open(True)
        return self.connected.wait(5)
    def close(self):
        try:self.connection.close()
        except Exception:pass
        self.signature = ()
