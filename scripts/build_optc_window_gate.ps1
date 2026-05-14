param(
    [Parameter(Mandatory=$true)]
    [string[]]$Inputs,
    [string]$OutRoot = "runs/optc-window-gate-20260514",
    [int]$Limit = 200000,
    [int]$EventsPerWindow = 5000
)

$ErrorActionPreference = "Stop"

$python = ".\.venv-diag\Scripts\python.exe"
$edges = Join-Path $OutRoot "optc_edges.jsonl"
$report = "reports/provenance_architecture/OPTC_WINDOW_GATE_20260514.md"

New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

$convertArgs = @("scripts\convert_optc_ecar_to_edges.py", "--inputs") + $Inputs + @("--output", $edges, "--limit", $Limit)
& $python @convertArgs

$windowArgs = @(
    "scripts\build_provenance_window_factory.py",
    "--edges", $edges,
    "--out-dir", $OutRoot,
    "--report", $report,
    "--events-per-window", $EventsPerWindow
)
& $python @windowArgs

Write-Host "Report written to $report"
