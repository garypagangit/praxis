param(
    [string]$HfCli = "$env:USERPROFILE\.venvs\praxis05\Scripts\hf.exe"
)

$ErrorActionPreference = "Stop"

if (!(Test-Path -LiteralPath $HfCli)) {
    $cmd = Get-Command hf -ErrorAction SilentlyContinue
    if ($cmd) {
        $HfCli = $cmd.Source
    } else {
        throw "HF CLI not found. Expected $HfCli or an hf command on PATH."
    }
}

Write-Host "Using HF CLI: $HfCli"
Write-Host ""

Write-Host "Checking login..."
& $HfCli auth whoami
if ($LASTEXITCODE -ne 0) {
    throw "Hugging Face CLI is not logged in. Run: $HfCli auth login"
}

$models = @(
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.2-3B-Instruct"
)

foreach ($model in $models) {
    Write-Host ""
    Write-Host "Checking gated access: $model"
    & $HfCli download $model config.json --repo-type model --dry-run
    if ($LASTEXITCODE -eq 0) {
        Write-Host "ACCESS OK: $model"
    } else {
        Write-Host "ACCESS NOT READY: $model"
    }
}
