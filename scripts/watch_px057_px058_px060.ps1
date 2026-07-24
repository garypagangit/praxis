param(
    [string]$AwsProfile = "praxis-build",
    [int]$PollSeconds = 60
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $workspace
$python = Join-Path $workspace ".venv\Scripts\python.exe"
$statusDir = Join-Path $workspace "reports\run_watch"
New-Item -ItemType Directory -Path $statusDir -Force | Out-Null
$statusPath = Join-Path $statusDir "px057_px058_px060_status.json"
$logPath = Join-Path $statusDir "px057_px058_px060.log"

$px057Job = "px057-gate2-full-retry-2026-07-24-14-55-01-066"
$px057Root = Join-Path $workspace "reports\adaptive_stopping_overthinking\gate2_full_cloud_20260724"
$px057Decision = Join-Path $workspace "reports\adaptive_stopping_overthinking\gate2_full_determination_20260724\summary.json"
$px058Results = Join-Path $workspace "reports\xai_explanation_drift_intrusion\cicids2017_gate2_confirmatory_corrected_20260724\results.json"
$px058Decision = Join-Path $workspace "reports\xai_explanation_drift_intrusion\cicids2017_gate2_determination_20260724\summary.json"
$px060Results = Join-Path $workspace "reports\coed_direction_robustness\gate1_20260724\results.json"
$px060Decision = Join-Path $workspace "reports\coed_direction_robustness\gate1_determination_20260724\summary.json"

function Write-Log([string]$Message) {
    $line = "$([DateTime]::UtcNow.ToString('o')) $Message"
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
}

function Save-Status([hashtable]$State) {
    $State["updated_at_utc"] = [DateTime]::UtcNow.ToString("o")
    [System.IO.File]::WriteAllText(
        $statusPath,
        ($State | ConvertTo-Json -Depth 8),
        [System.Text.UTF8Encoding]::new($false)
    )
}

$state = @{
    px057 = "running"
    px058 = "running"
    px060 = "running"
}
Write-Log "Watcher started."

while ($true) {
    try {
        if (-not (Test-Path -LiteralPath $px060Decision)) {
            if (Test-Path -LiteralPath $px060Results) {
                Write-Log "PX-060 results detected; running independent adjudicator."
                & $python scripts\adjudicate_px060_coed_direction_robustness.py `
                    --config configs\px060_coed_direction_robustness_gate1_20260724.json `
                    --results $px060Results `
                    --repo external\coed-gnn `
                    --output-dir reports\coed_direction_robustness\gate1_determination_20260724 `
                    2>&1 | Add-Content -LiteralPath $logPath -Encoding UTF8
                if ($LASTEXITCODE -ne 0) { throw "PX-060 adjudicator failed." }
                $state["px060"] = "adjudicated"
                Write-Log "PX-060 adjudication complete."
            }
        } else {
            $state["px060"] = "adjudicated"
        }

        if (-not (Test-Path -LiteralPath $px058Decision)) {
            if (Test-Path -LiteralPath $px058Results) {
                Write-Log "PX-058 results detected; running independent adjudicator."
                & $python scripts\adjudicate_px058_xai_explanation_drift.py `
                    --config configs\px058_xai_explanation_drift_cicids2017_gate2_20260724.json `
                    --results $px058Results `
                    --manifest data\cic-ids-2017\manifest.json `
                    --output-dir reports\xai_explanation_drift_intrusion\cicids2017_gate2_determination_20260724 `
                    2>&1 | Add-Content -LiteralPath $logPath -Encoding UTF8
                if ($LASTEXITCODE -ne 0) { throw "PX-058 adjudicator failed." }
                $state["px058"] = "adjudicated"
                Write-Log "PX-058 adjudication complete."
            }
        } else {
            $state["px058"] = "adjudicated"
        }

        if (-not (Test-Path -LiteralPath $px057Decision)) {
            $description = aws sagemaker describe-training-job `
                --training-job-name $px057Job `
                --profile $AwsProfile `
                --output json | ConvertFrom-Json
            $state["px057_cloud_status"] = $description.TrainingJobStatus
            if ($description.TrainingJobStatus -eq "Completed") {
                Write-Log "PX-057 cloud job completed; retrieving model artifact."
                New-Item -ItemType Directory -Path $px057Root -Force | Out-Null
                $archive = Join-Path $px057Root "model.tar.gz"
                aws s3 cp $description.ModelArtifacts.S3ModelArtifacts $archive `
                    --profile $AwsProfile 2>&1 |
                    Add-Content -LiteralPath $logPath -Encoding UTF8
                if ($LASTEXITCODE -ne 0) { throw "PX-057 artifact download failed." }
                $extractDir = Join-Path $px057Root "extracted"
                New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
                tar -xf $archive -C $extractDir
                if ($LASTEXITCODE -ne 0) { throw "PX-057 artifact extraction failed." }
                $summary = Get-ChildItem -LiteralPath $extractDir -Recurse `
                    -Filter "summary.json" -File | Select-Object -First 1
                if (-not $summary) { throw "PX-057 summary.json absent from artifact." }
                & $python scripts\adjudicate_px057_adaptive_stopping.py `
                    --config configs\px057_adaptive_stopping_gate2_full_20260724.json `
                    --artifact-dir $summary.Directory.FullName `
                    --output-dir reports\adaptive_stopping_overthinking\gate2_full_determination_20260724 `
                    2>&1 | Add-Content -LiteralPath $logPath -Encoding UTF8
                if ($LASTEXITCODE -ne 0) { throw "PX-057 adjudicator failed." }
                $state["px057"] = "adjudicated"
                Write-Log "PX-057 adjudication complete."
            } elseif ($description.TrainingJobStatus -in @("Failed", "Stopped")) {
                $state["px057"] = "cloud_failed"
                $state["px057_failure_reason"] = $description.FailureReason
                Write-Log "PX-057 cloud job terminated: $($description.FailureReason)"
            }
        } else {
            $state["px057"] = "adjudicated"
        }

        Save-Status $state
        if (
            $state["px057"] -in @("adjudicated", "cloud_failed") -and
            $state["px058"] -eq "adjudicated" -and
            $state["px060"] -eq "adjudicated"
        ) {
            Write-Log "All watched runs reached a terminal state."
            break
        }
    } catch {
        $state["watcher_error"] = $_.Exception.Message
        Save-Status $state
        Write-Log "ERROR: $($_.Exception.Message)"
    }
    Start-Sleep -Seconds $PollSeconds
}
