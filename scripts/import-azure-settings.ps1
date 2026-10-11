# Read-only Azure operations. Does not create resources or deployments.
param(
    [Parameter(Mandatory=$true)][string]$SubscriptionId,
    [Parameter(Mandatory=$true)][string]$SpeechResourceGroup,
    [Parameter(Mandatory=$true)][string]$SpeechName,
    [Parameter(Mandatory=$true)][string]$ModelResourceGroup,
    [Parameter(Mandatory=$true)][string]$ModelName,
    [Parameter(Mandatory=$true)][string]$Deployment,
    [string]$VisionResourceGroup = '',
    [string]$VisionName = ''
)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw 'Install Microsoft Azure CLI and run az login first. See docs/AZURE_SETUP.md.'
}
function Read-AzureJson([string[]]$Arguments) {
    $raw = & az @Arguments --subscription $SubscriptionId --only-show-errors --output json
    if ($LASTEXITCODE -ne 0) { throw 'Azure lookup failed. Check login, subscription, resource names and permissions.' }
    return ($raw -join "`n" | ConvertFrom-Json)
}
$speech = Read-AzureJson -Arguments @('cognitiveservices','account','show','-g',$SpeechResourceGroup,'-n',$SpeechName)
$model = Read-AzureJson -Arguments @('cognitiveservices','account','show','-g',$ModelResourceGroup,'-n',$ModelName)
$deployments = Read-AzureJson -Arguments @('cognitiveservices','account','deployment','list','-g',$ModelResourceGroup,'-n',$ModelName)
$selected = @($deployments | Where-Object { $_.name -eq $Deployment })
if ($selected.Count -ne 1) { throw 'The specified model deployment was not found. Deploy a model first.' }
if ($selected[0].properties.model.name -like 'gpt-5*' -and $Deployment -notlike 'gpt-5*') {
    throw 'For GPT-5 models, use a deployment name beginning with gpt-5 (for example gpt-5-mini). See the compatibility note.'
}
$config = @{
    speech = @{region=$speech.location; key=''}
    model = @{endpoint=$model.properties.endpoint; key=''; deployment=$Deployment}
    vision = @{endpoint=''; key=''}
}
if ($VisionName) {
    if (-not $VisionResourceGroup) { throw 'VisionResourceGroup is required with VisionName.' }
    $vision = Read-AzureJson -Arguments @('cognitiveservices','account','show','-g',$VisionResourceGroup,'-n',$VisionName)
    $config.vision.endpoint = $vision.properties.endpoint
}
$destination = Join-Path $env:LOCALAPPDATA 'StableCaptions/config.json'
if ($env:STABLE_CAPTIONS_CONFIG) { $destination = $env:STABLE_CAPTIONS_CONFIG }
Write-Host "Save this account's Speech, model and optional Vision keys to: $destination"
Write-Host 'This is a private plaintext file. Do not upload or share it. Existing saved settings will be replaced.'
if ((Read-Host 'Type SAVE to continue') -cne 'SAVE') { Write-Host 'Cancelled.'; return }
$config.speech.key = (Read-AzureJson -Arguments @('cognitiveservices','account','keys','list','-g',$SpeechResourceGroup,'-n',$SpeechName)).key1
$config.model.key = (Read-AzureJson -Arguments @('cognitiveservices','account','keys','list','-g',$ModelResourceGroup,'-n',$ModelName)).key1
if ($VisionName) {
    $config.vision.key = (Read-AzureJson -Arguments @('cognitiveservices','account','keys','list','-g',$VisionResourceGroup,'-n',$VisionName)).key1
}
$parent = Split-Path -Parent $destination
New-Item -ItemType Directory -Force $parent | Out-Null
$temporary = Join-Path $parent ([Guid]::NewGuid().ToString() + '.tmp')
try {
    [IO.File]::WriteAllText($temporary, ($config | ConvertTo-Json -Depth 4), [Text.UTF8Encoding]::new($false))
    Move-Item -Force $temporary $destination
} finally {
    if (Test-Path $temporary) { Remove-Item $temporary }
    $config = $null
}
Write-Host 'Saved. Restart Stable Captions. Keys have not been printed or embedded in the executable.'
