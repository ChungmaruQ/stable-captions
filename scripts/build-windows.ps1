param([ValidateSet('all','en_ko','jp_vn')][string]$Variant = 'all')
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
        throw 'Install Python 3.12 x64 from https://www.python.org/downloads/windows/ (include Python Launcher), then reopen PowerShell.'
    }
    & py -3.12 -c "import struct; assert struct.calcsize('P') == 8, '64-bit Python required'"
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 is required.' }
    if (-not (Test-Path '.venv/Scripts/python.exe')) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Creating .venv failed.' }
    }
    $python = Join-Path $root '.venv/Scripts/python.exe'
    & $python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    & $python scripts/build.py --variant $Variant
    if ($LASTEXITCODE -ne 0) { throw 'Build or offline validation failed. See the first error above.' }
    Write-Host 'Finished. Both the EXE and ZIP are under dist/. Configure your own Azure services after launch.'
} finally { Pop-Location }
