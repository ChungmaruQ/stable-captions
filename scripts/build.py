"""Native platform build; offline verification is mandatory before packaging."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import zipfile
from check import ROOT, offline_env

NAMES = {'en_ko': 'StableCaptions', 'jp_vn': 'StableCaptions_JP-VN'}

def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)

def build(variant):
    name = NAMES[variant]
    source = ROOT/'apps'/variant
    output = ROOT/'dist'/variant
    output.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile',
               '--windowed', '--name', name, '--collect-all', 'azure.cognitiveservices.speech',
               '--distpath', output, '--workpath', ROOT/'build'/variant,
               '--specpath', ROOT/'build', '--paths', source, source/'app.py']
    if sys.platform == 'darwin':
        command += ['--hidden-import', 'AppKit', '--hidden-import', 'objc']
    run(command, cwd=ROOT)
    executable = output/(name + ('.exe' if sys.platform == 'win32' else ''))
    with tempfile.TemporaryDirectory() as temp:
        env = offline_env(Path(temp)/'no-credentials.json')
        # Native macOS validation checks the actual always-on-top window on the rightmost display.
        if sys.platform == 'darwin': env.pop('QT_QPA_PLATFORM', None)
        report_dir = ROOT/'reports'/variant
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir/'layout-validation.json'
        report_path.unlink(missing_ok=True)
        result = subprocess.run([str(executable), '--verify-layout', str(report_dir)], cwd=source, env=env, timeout=120)
        if not report_path.exists():
            raise RuntimeError(f'Packaged app did not produce a validation report (exit {result.returncode})')
        report = json.loads(report_path.read_text(encoding='utf-8'))
        print(json.dumps(report, ensure_ascii=True), flush=True)
        if result.returncode or not report['pass'] or not report['packaged']:
            raise RuntimeError('Packaged layout validation failed')
    if sys.platform == 'win32' and executable.read_bytes()[:2] != b'MZ':
        raise RuntimeError('Output is not a Windows executable')
    digest = hashlib.sha256(executable.read_bytes()).hexdigest()
    manifest = {'variant': variant, 'platform': platform.platform(), 'python': sys.version,
                'executable': executable.name, 'sha256': digest, 'validation': report,
                'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'dependencies': subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True).splitlines(),
                'cloud_tested': False, 'credentials_bundled': False}
    manifest_path = output/'build-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    # Never package personal settings, desktop screenshots, microphone recordings or arbitrary folders.
    archive = ROOT/'dist'/f'{name}-{platform.system()}.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in (executable, manifest_path, ROOT/'docs/QUICKSTART.md', ROOT/'LICENSE'):
            bundle.write(path, path.name)
    print(f'Built {archive.name}\nSHA256 ({executable.name}): {digest}', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['all', *NAMES], default='all')
    args = parser.parse_args()
    if sys.platform not in ('win32', 'darwin'):
        raise SystemExit('Build on Windows for EXE or macOS for a Mac executable. Cross-compilation is unsupported.')
    if sys.platform == 'win32' and platform.architecture()[0] != '64bit':
        raise SystemExit('Use 64-bit Python 3.12 on Windows.')
    run([sys.executable, ROOT/'scripts/check.py'], cwd=ROOT)
    for variant in NAMES if args.variant == 'all' else [args.variant]: build(variant)
