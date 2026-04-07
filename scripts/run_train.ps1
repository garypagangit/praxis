$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$configPath = Join-Path $repoRoot "configs\example.json"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Missing virtual environment. Run .\\scripts\\setup_local.ps1 first."
}

& $venvPython -m praxis.train --config $configPath
