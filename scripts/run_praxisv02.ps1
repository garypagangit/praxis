$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $repoRoot "configs\praxisv02-unraveled-local.json"
$logDir = Join-Path $repoRoot "runs\praxisv02-unraveled-cpu"
$logPath = Join-Path $logDir "console.log"
$cacheDir = Join-Path $env:LocalAppData "PraxisCache\praxisv02-unraveled-cpu"
$mplConfigDir = Join-Path $cacheDir "matplotlib"
$torchHome = Join-Path $cacheDir "torch"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Missing virtual environment. Run .\\scripts\\setup_local.ps1 first."
}

New-Item -ItemType Directory -Path $logDir -Force | Out-Null
New-Item -ItemType Directory -Path $mplConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $torchHome -Force | Out-Null

$env:MPLCONFIGDIR = $mplConfigDir
$env:TORCH_HOME = $torchHome
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"

$previousErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"

& $venvPython -m praxis.train --config $configPath 2>&1 |
    ForEach-Object { $_.ToString() } |
    Tee-Object -FilePath $logPath
$exitCode = $LASTEXITCODE

$ErrorActionPreference = $previousErrorActionPreference

if ($exitCode -ne 0) {
    throw "Training command failed. See $logPath"
}

Write-Host ""
Write-Host "Console log: $logPath"
