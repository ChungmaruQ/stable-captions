"""User-owned Azure settings. Never bundle secrets with the executable."""
import json
import os
import sys
import tempfile
import warnings
from pathlib import Path

FIELDS = {'speech': ('key', 'region'), 'model': ('endpoint', 'key', 'deployment'),
          'vision': ('endpoint', 'key')}
ENVIRONMENT = {'AZURE_SPEECH_KEY': ('speech', 'key'),
               'AZURE_SPEECH_REGION': ('speech', 'region'),
               'AZURE_OPENAI_ENDPOINT': ('model', 'endpoint'),
               'AZURE_OPENAI_API_KEY': ('model', 'key'),
               'AZURE_OPENAI_DEPLOYMENT': ('model', 'deployment'),
               'AZURE_VISION_ENDPOINT': ('vision', 'endpoint'),
               'AZURE_VISION_KEY': ('vision', 'key')}


def settings_path():
    override = os.environ.get('STABLE_CAPTIONS_CONFIG')
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local')))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    return base / 'StableCaptions' / 'config.json'


def normalize(data):
    return {group: {field: str(data.get(group, {}).get(field, '') or '').strip()
                    for field in fields} for group, fields in FIELDS.items()}


def load_settings():
    settings = normalize({})
    path = settings_path()
    if path.is_file():
        try:
            settings = normalize(json.loads(path.read_text(encoding='utf-8-sig')))
        except (ValueError, TypeError, AttributeError, OSError):
            # Never include input JSON or credentials in diagnostics.
            warnings.warn('Azure settings could not be read. Re-enter and save them in the app.', RuntimeWarning)
    for name, (group, field) in ENVIRONMENT.items():
        if name in os.environ:
            settings[group][field] = os.environ[name].strip()
    return settings


def save_settings(data):
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.settings-', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(normalize(data), stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        if os.name != 'nt':
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path
