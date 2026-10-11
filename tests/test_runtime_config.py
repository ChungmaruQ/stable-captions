import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime', ROOT / 'apps/en_ko/runtime_config.py')
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'private' / 'config.json'
        self.env = patch.dict(os.environ, {'STABLE_CAPTIONS_CONFIG': str(self.path)}, clear=True)
        self.env.start()
    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()
    def test_empty_install_has_no_credentials(self):
        self.assertFalse(any(v for fields in config.load_settings().values() for v in fields.values()))
    def test_private_roundtrip_and_atomic_update(self):
        config.save_settings({'speech': {'key': 'dummy-one', 'region': 'test-region'}})
        self.assertEqual(config.load_settings()['speech']['key'], 'dummy-one')
        config.save_settings({'speech': {'key': 'dummy-two'}})
        self.assertEqual(config.load_settings()['speech']['key'], 'dummy-two')
        self.assertEqual(list(self.path.parent.glob('*.tmp')), [])
        if os.name != 'nt': self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    def test_environment_overrides_file_including_explicit_empty(self):
        config.save_settings({'speech': {'key': 'dummy'}})
        with patch.dict(os.environ, {'AZURE_SPEECH_KEY': '', 'AZURE_OPENAI_DEPLOYMENT': 'my-deployment'}):
            data = config.load_settings()
            self.assertEqual(data['speech']['key'], '')
            self.assertEqual(data['model']['deployment'], 'my-deployment')
    def test_invalid_file_never_echoes_contents(self):
        self.path.parent.mkdir()
        self.path.write_text('{private-content', encoding='utf-8')
        with self.assertWarns(RuntimeWarning) as caught:
            self.assertEqual(config.load_settings()['speech']['key'], '')
        self.assertNotIn('private-content', str(caught.warning))
    def test_both_apps_share_loader(self):
        self.assertEqual((ROOT/'apps/en_ko/runtime_config.py').read_bytes(),
                         (ROOT/'apps/jp_vn/runtime_config.py').read_bytes())
    def test_examples_and_wrappers_do_not_embed_settings(self):
        self.assertEqual(json.loads((ROOT/'config.example.json').read_text()), config.normalize({}))
        for variant in ('en_ko', 'jp_vn'):
            wrapper = (ROOT/'apps'/variant/'embedded_config.py').read_text()
            self.assertIn('load_settings()', wrapper)

if __name__ == '__main__': unittest.main()
