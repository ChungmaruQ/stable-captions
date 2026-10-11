"""Own a Speech SDK recognizer and its real service connection before recognition."""
import threading

def make_config(key, region, silence_ms):
    import azure.cognitiveservices.speech as speechsdk
    config = speechsdk.translation.SpeechTranslationConfig(
        subscription=key, endpoint=f'wss://{region}.stt.speech.microsoft.com/speech/universal/v2')
    config.set_property(speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode, 'Continuous')
    language_config = speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=['ko-KR', 'en-US'])
    config.add_target_language('en')
    config.set_profanity(speechsdk.ProfanityOption.Masked)
    config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
                str(silence_ms))
    return config, language_config

class PreparedSpeech:
    def __init__(self, key, region, silence_ms, audio=None):
        import azure.cognitiveservices.speech as sdk
        self.signature = (key, region, silence_ms)
        self.connected = threading.Event()
        config, language = make_config(key, region, silence_ms)
        # Constructing a recognizer does not start recognition or microphone capture.
        self.audio = audio if audio is not None else sdk.audio.AudioConfig(use_default_microphone=True)
        self.recognizer = sdk.translation.TranslationRecognizer(
            translation_config=config, audio_config=self.audio,
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
