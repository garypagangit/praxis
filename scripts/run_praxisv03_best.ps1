param(
    [ValidateSet("Smoke", "Full")]
    [string]$Mode = "Smoke"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Missing virtual environment. Run .\\scripts\\setup_local.ps1 first."
}

$configMap = @{
    Smoke = Join-Path $repoRoot "configs\praxisv03-unraveled-best-local-smoke.json"
    Full = Join-Path $repoRoot "configs\praxisv03-unraveled-best-local.json"
}

$configPath = $configMap[$Mode]
$config = Get-Content -Raw $configPath | ConvertFrom-Json
$runDir = Join-Path $repoRoot ("runs\" + $config.run_name)
$logPath = Join-Path $runDir "console.log"
$cacheDir = Join-Path $runDir ".runtime-cache"
$mplConfigDir = Join-Path $cacheDir "matplotlib"
$torchHome = Join-Path $cacheDir "torch"

New-Item -ItemType Directory -Path $runDir -Force | Out-Null
New-Item -ItemType Directory -Path $mplConfigDir -Force | Out-Null
New-Item -ItemType Directory -Path $torchHome -Force | Out-Null

$env:MPLCONFIGDIR = $mplConfigDir
$env:TORCH_HOME = $torchHome
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYTHONUTF8 = "1"

Write-Host "Mode: $Mode"
Write-Host "Config: $configPath"
Write-Host "Run dir: $runDir"

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
