param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"

& $PythonExe -m venv $venvPath

$venvPython = Join-Path $venvPath "Scripts\python.exe"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r (Join-Path $repoRoot "requirements-local.txt")
& $venvPython -m pip install -r (Join-Path $repoRoot "requirements.txt")
& $venvPython -m pip install -e $repoRoot

Write-Host ""
Write-Host "Environment ready."
Write-Host "Interpreter: $venvPython"
Write-Host "Next: run .\\scripts\\run_train.ps1"
