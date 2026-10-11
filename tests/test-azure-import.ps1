# Offline test: the az command is replaced by a function returning synthetic data.
$ErrorActionPreference = 'Stop'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ([Guid]::NewGuid().ToString())
$oldConfig = $env:STABLE_CAPTIONS_CONFIG
$env:STABLE_CAPTIONS_CONFIG = Join-Path $temporary 'config.json'
function az {
    $global:LASTEXITCODE = 0
    if ($args -contains 'keys') { return '{"key1":"dummy-private-key"}' }
    if ($args -contains 'deployment') {
        return '[{"name":"gpt-5-mini","properties":{"model":{"name":"gpt-5-mini"}}}]'
    }
    if ($args -contains 'show') {
        return '{"location":"test-region","properties":{"endpoint":"https://example.openai.azure.com"}}'
    }
    throw 'Unexpected fake Azure command'
}
function Read-Host { return 'SAVE' }
try {
    $script = Join-Path (Split-Path -Parent $PSScriptRoot) 'scripts/import-azure-settings.ps1'
    $log = & $script -SubscriptionId fake-subscription -SpeechResourceGroup fake-group -SpeechName fake-speech -ModelResourceGroup fake-group -ModelName fake-model -Deployment gpt-5-mini 6>&1
    if (($log | Out-String) -match 'dummy-private-key') { throw 'Key was printed' }
    $data = Get-Content -Raw $env:STABLE_CAPTIONS_CONFIG | ConvertFrom-Json
    if ($data.speech.key -ne 'dummy-private-key' -or $data.speech.region -ne 'test-region' -or $data.model.deployment -ne 'gpt-5-mini') { throw 'Settings import did not preserve service fields' }
    if ($data.vision.key -ne '') { throw 'Optional Vision should remain blank' }
    Write-Host 'Offline Azure settings import test passed. No cloud calls made.'
} finally {
    $env:STABLE_CAPTIONS_CONFIG = $oldConfig
    if (Test-Path $temporary) { Remove-Item -Recurse -Force $temporary }
    Remove-Item Function:az
    Remove-Item Function:Read-Host
}
