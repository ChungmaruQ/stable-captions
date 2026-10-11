"""Fresh-install onboarding and save action, with no network requests."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app import MainWindow
from runtime_config import load_settings

APP = QApplication.instance() or QApplication([])

class OnboardingTests(unittest.TestCase):
    def window(self):
        window = MainWindow(warmup=False)
        self.addCleanup(window.close)
        return window
    def test_empty_install_does_not_start_connections(self):
        window = self.window()
        window.key.clear(); window.region.clear()
        with patch('startup_preparation.PreparationWorker') as preparation:
            window.prepare_connections()
            preparation.assert_not_called()
        self.assertIn('Azure 설정', window.ready_label.text())
    def test_save_keeps_settings_outside_program_and_enables_model(self):
        window = self.window()
        window.key.setText('dummy-speech'); window.region.setText('test-region')
        c = window.context
        c.model_key.setText('dummy-model'); c.model_endpoint.setText('https://example.openai.azure.com')
        c.deployment.setText('gpt-5-mini'); c.use_translation.setChecked(False)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'private.json'
            with patch.dict(os.environ, {'STABLE_CAPTIONS_CONFIG': str(path)}), \
                 patch('app.QMessageBox.information'), patch.object(window, 'prepare_connections') as prepare:
                window.save_azure_settings()
                self.assertEqual(load_settings()['speech']['key'], 'dummy-speech')
                self.assertEqual(load_settings()['model']['deployment'], 'gpt-5-mini')
                self.assertTrue(c.use_translation.isChecked())
                prepare.assert_called_once()
    def test_failed_save_never_preconnects(self):
        window = self.window()
        with patch('runtime_config.save_settings', side_effect=OSError('dummy')), \
             patch('app.QMessageBox.warning') as message, patch.object(window, 'prepare_connections') as prepare:
            window.save_azure_settings()
            message.assert_called_once(); prepare.assert_not_called()

if __name__ == '__main__': unittest.main()
