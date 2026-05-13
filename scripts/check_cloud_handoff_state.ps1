param(
    [string]$Root = ""
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Root)) {
    if ($PSScriptRoot) {
        $Root = Split-Path -Parent $PSScriptRoot
    } else {
        $Root = "."
    }
}

$resolvedRoot = (Resolve-Path -LiteralPath $Root).Path
Push-Location $resolvedRoot

try {
    $required = @(
        "CLOUD_HANDOFF.md",
        "configs/experiment_cloud_handoff_registry.json",
        "reports/EXPERIMENT_FINAL_EVALUATION_20260511.md",
        "reports/EXPERIMENT_DASHBOARD.md",
        "configs/dataset_registry.json",
        "templates/experiment_handoff_manifest.template.json",
        "templates/experiment_cloud_prompt.template.md"
    )

    Write-Host "Cloud handoff state check"
    Write-Host "Root: $resolvedRoot"
    Write-Host ""

    $missing = @()
    foreach ($path in $required) {
        if (Test-Path -LiteralPath $path) {
            Write-Host "[ok]      $path"
        } else {
            Write-Host "[missing] $path"
            $missing += $path
        }
    }

    Write-Host ""
    Write-Host "Validating JSON files..."
    Get-Content -LiteralPath "configs/experiment_cloud_handoff_registry.json" -Raw | ConvertFrom-Json | Out-Null
    Get-Content -LiteralPath "templates/experiment_handoff_manifest.template.json" -Raw | ConvertFrom-Json | Out-Null
    Write-Host "[ok] JSON parsed"

    if (Get-Command git -ErrorAction SilentlyContinue) {
        Write-Host ""
        Write-Host "Git state:"
        $branch = git branch --show-current
        $head = git rev-parse --short HEAD
        Write-Host "Branch: $branch"
        Write-Host "HEAD:   $head"

        Write-Host ""
        $status = git status --porcelain
        Write-Host "Required handoff file git status:"
        foreach ($path in $required) {
            $normalizedPath = $path.Replace("\", "/")
            $matching = $status | Where-Object {
                $gitPath = $_.Substring(3).Replace("\", "/")
                ($gitPath -eq $normalizedPath) -or ($gitPath.EndsWith("/") -and $normalizedPath.StartsWith($gitPath))
            }
            if ($matching) {
                $firstMatch = @($matching)[0]
                $matchedPath = $firstMatch.Substring(3).Replace("\", "/")
                if ($matchedPath.EndsWith("/") -and $normalizedPath.StartsWith($matchedPath)) {
                    Write-Host "$firstMatch (covers $path)"
                } else {
                    Write-Host $firstMatch
                }
            } else {
                Write-Host "[clean]  $path"
            }
        }

        Write-Host ""
        Write-Host "Lightweight untracked files that cloud will not see until committed or attached:"
        $interesting = $status | Where-Object {
            $_ -match "^\?\? (CLOUD_HANDOFF\.md|templates/|reports/|configs/|scripts/|src/|tests/|cloud_jobs/)"
        }
        if ($interesting) {
            $count = @($interesting).Count
            $interesting | Select-Object -First 40 | ForEach-Object { Write-Host $_ }
            if ($count -gt 40) {
                Write-Host "... $($count - 40) more lightweight untracked path(s)"
            }
        } else {
            Write-Host "[ok] none under the standard lightweight prefixes"
        }
    }

    if ($missing.Count -gt 0) {
        throw "Missing required handoff file(s): $($missing -join ', ')"
    }
}
finally {
    Pop-Location
}
