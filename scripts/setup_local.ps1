param(
    [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Resolve-PythonExe {
    param(
        [string]$RequestedPath
    )

    if ($RequestedPath) {
        if (-not (Test-Path -LiteralPath $RequestedPath)) {
            throw "Python executable not found at $RequestedPath"
        }
        return $RequestedPath
    }

    $candidates = @()
    $command = Get-Command python -ErrorAction SilentlyContinue
    if ($command -and $command.Source -and $command.Source -notlike "*WindowsApps*") {
        $candidates += $command.Source
    }

    $candidates += @(
        (Join-Path $env:LocalAppData "Programs\Python\Python311\python.exe"),
        (Join-Path $env:LocalAppData "Programs\Python\Python312\python.exe"),
        (Join-Path $env:ProgramFiles "Python311\python.exe"),
        (Join-Path $env:ProgramFiles "Python312\python.exe")
    )

    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    throw "Could not find a usable Python installation. Install Python 3.11 and rerun this script."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot ".venv"
$PythonExe = Resolve-PythonExe -RequestedPath $PythonExe

Invoke-Checked -FilePath $PythonExe -Arguments @("-m", "venv", $venvPath)

$venvPython = Join-Path $venvPath "Scripts\python.exe"
foreach ($requirementsFile in @(
    "requirements-local.txt",
    "requirements.txt",
    "requirements-dev.txt"
)) {
    $requirementsPath = Join-Path $repoRoot $requirementsFile
    if (-not (Test-Path -LiteralPath $requirementsPath)) {
        continue
    }

    Invoke-Checked -FilePath $venvPython -Arguments @(
        "-m", "pip", "install", "-r", $requirementsPath
    )
}
Invoke-Checked -FilePath $venvPython -Arguments @(
    "-m", "pip", "install", "--no-build-isolation", "-e", $repoRoot
)

Write-Host ""
Write-Host "Environment ready."
Write-Host "Base Python: $PythonExe"
Write-Host "Interpreter: $venvPython"
Write-Host "Next: run .\\scripts\\run_train.ps1"
