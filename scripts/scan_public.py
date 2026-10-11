"""Conservative source check; reports file/rule only, never matching credentials.

This is a guardrail, not a substitute for reviewing the actual git diff.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = {
    'Azure-style long key': re.compile(r'(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{80,}={0,2}(?![A-Za-z0-9+/])'),
    'private key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'GitHub token': re.compile(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
    'personal home path': re.compile(r'/Us' + r'ers/(?!USERNAME\b)[^/\s]+/'),
}

def main():
    try:
        names = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
    except subprocess.CalledProcessError:
        raise SystemExit('Run git init before scanning.')
    findings = []
    for name in set(names):
        if not name: continue
        path = ROOT/name
        if path.suffix.lower() in ('.exe','.zip','.wav','.mov','.docx','.pdf'):
            findings.append((name, 'private or built asset in source tree')); continue
        try: content = path.read_text(encoding='utf-8')
        except (UnicodeError, IsADirectoryError): continue
        for label, pattern in RULES.items():
            if pattern.search(content): findings.append((name, label))
    for name, label in findings: print(f'{name}: {label}')
    if findings: raise SystemExit('Public-source scan failed; remove secrets before publishing.')
    print(f'Public-source scan passed ({len(set(names)) - 1} files). Review diff before pushing.')

if __name__ == '__main__': main()
