from runtime_config import load_settings
_settings = load_settings()
SPEECH_KEY = _settings['speech']['key']
SPEECH_REGION = _settings['speech']['region']
