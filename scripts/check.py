"""Offline tests, isolated from the operator's Azure credentials."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def offline_env(path):
    env = {k: v for k, v in os.environ.items() if not k.startswith('AZURE_')}
    env.update(STABLE_CAPTIONS_CONFIG=str(path), QT_QPA_PLATFORM='offscreen')
    return env

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as temporary:
        env = offline_env(Path(temporary) / 'empty.json')
        for folder in (ROOT/'tests', ROOT/'apps/en_ko', ROOT/'apps/jp_vn'):
            subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', str(folder), '-p', 'test*.py'],
                           cwd=folder, env=env, check=True)
    print('All offline tests passed. No Azure credentials used.')
