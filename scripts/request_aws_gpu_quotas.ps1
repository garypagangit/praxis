param(
    [string]$Profile = "praxis-build",
    [string[]]$Regions = @("us-east-1"),
    [int]$GAndVtVcpu = 256,
    [int]$PVcpu = 128,
    [int]$DlVcpu = 64,
    [int]$TrnVcpu = 64,
    [int]$InfVcpu = 64,
    [switch]$Submit,
    [string]$OutputDir = "reports"
)

$ErrorActionPreference = "Stop"

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (-not (Test-Path $aws)) {
    $aws = "aws"
}

$targets = @(
    @{ Match = "Running On-Demand G and VT instances"; Desired = $GAndVtVcpu; Rationale = "Primary affordable GPU pool for g5/g6/g6e-style experiments and parallel medium runs." },
    @{ Match = "Running On-Demand P instances"; Desired = $PVcpu; Rationale = "High-end GPU pool for p4/p5-style full model and SAE/LLM jobs." },
    @{ Match = "Running On-Demand DL instances"; Desired = $DlVcpu; Rationale = "Deep Learning accelerator family if available in the account/region." },
    @{ Match = "Running On-Demand Trn instances"; Desired = $TrnVcpu; Rationale = "Trainium pool for high-throughput model training if later used." },
    @{ Match = "Running On-Demand Inf instances"; Desired = $InfVcpu; Rationale = "Inferentia pool for concurrent inference/evaluation workloads." }
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$results = @()

foreach ($region in $Regions) {
    Write-Host "Inspecting EC2 service quotas in $region using profile $Profile"
    $quotaJson = & $aws service-quotas list-service-quotas `
        --service-code ec2 `
        --region $region `
        --profile $Profile `
        --output json
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($quotaJson)) {
        throw "AWS Service Quotas lookup failed for region $region. Refresh SSO with: aws sso login --profile $Profile"
    }

    $quotas = ($quotaJson | ConvertFrom-Json).Quotas
    if (-not $quotas -or $quotas.Count -eq 0) {
        throw "AWS returned zero EC2 quotas for region $region. Do not submit requests until profile access is verified."
    }

    foreach ($target in $targets) {
        $quota = $quotas | Where-Object { $_.QuotaName -eq $target.Match } | Select-Object -First 1
        if (-not $quota) {
            $quota = $quotas | Where-Object { $_.QuotaName -like "*$($target.Match)*" } | Select-Object -First 1
        }

        if (-not $quota) {
            $results += [pscustomobject]@{
                region = $region
                quota_name = $target.Match
                quota_code = $null
                current_value = $null
                desired_value = $target.Desired
                status = "not_found"
                note = "Quota was not returned by Service Quotas for this account/region."
                rationale = $target.Rationale
            }
            continue
        }

        $current = [double]$quota.Value
        $desired = [double]$target.Desired
        if ($current -ge $desired) {
            $results += [pscustomobject]@{
                region = $region
                quota_name = $quota.QuotaName
                quota_code = $quota.QuotaCode
                current_value = $current
                desired_value = $desired
                status = "already_sufficient"
                note = "Current quota is already at or above target."
                rationale = $target.Rationale
            }
            continue
        }

        if (-not $Submit) {
            $results += [pscustomobject]@{
                region = $region
                quota_name = $quota.QuotaName
                quota_code = $quota.QuotaCode
                current_value = $current
                desired_value = $desired
                status = "would_request"
                note = "Run with -Submit to create the Service Quotas request."
                rationale = $target.Rationale
            }
            continue
        }

        try {
            Write-Host "Requesting $($quota.QuotaName) in $region from $current to $desired vCPUs"
            $requestJson = & $aws service-quotas request-service-quota-increase `
                --service-code ec2 `
                --quota-code $quota.QuotaCode `
                --desired-value $desired `
                --region $region `
                --profile $Profile `
                --output json
            $request = ($requestJson | ConvertFrom-Json).RequestedQuota
            $results += [pscustomobject]@{
                region = $region
                quota_name = $quota.QuotaName
                quota_code = $quota.QuotaCode
                current_value = $current
                desired_value = $desired
                status = "submitted"
                request_id = $request.Id
                request_status = $request.Status
                note = "Quota increase request submitted."
                rationale = $target.Rationale
            }
        } catch {
            $results += [pscustomobject]@{
                region = $region
                quota_name = $quota.QuotaName
                quota_code = $quota.QuotaCode
                current_value = $current
                desired_value = $desired
                status = "submit_failed"
                note = $_.Exception.Message
                rationale = $target.Rationale
            }
        }
    }
}

$outPath = Join-Path $OutputDir "aws_gpu_quota_request_$stamp.json"
$results | ConvertTo-Json -Depth 8 | Set-Content -Path $outPath -Encoding UTF8

Write-Host "Wrote quota request report to $outPath"
$results | Format-Table region, quota_name, current_value, desired_value, status -AutoSize
