param(
    [Parameter(Mandatory = $true)]
    [string]$StartDate,

    [Parameter(Mandatory = $true)]
    [string]$EndDate,

    [string]$OutputRoot = "external\datasets\nvd",
    [string]$ApiKey = $env:NVD_API_KEY,
    [switch]$SyncToS3,
    [string]$BucketName = "praxis-garypagan-272615233626-us-east-1",
    [string]$Profile = "praxis-build"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$outDir = Join-Path $repoRoot $OutputRoot
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path -LiteralPath $aws)) {
    $aws = "aws"
}

if ($ApiKey) {
    $ApiKey = $ApiKey.Trim().Trim('"').Trim("'")
}

$requestedStartDate = [DateTime]::Parse($StartDate).Date
$requestedEndDate = [DateTime]::Parse($EndDate).Date
$baseUri = "https://services.nvd.nist.gov/rest/json/cves/2.0"
$pageSize = 2000
$totalFetched = 0
$writtenFiles = @()

Write-Host "Fetching NVD CVEs from $StartDate through $EndDate"
if ($ApiKey) {
    Write-Host "Using NVD API key from parameter/environment."
} else {
    Write-Host "No NVD API key detected. Public rate limits apply."
}

$windowStart = $requestedStartDate
while ($windowStart -le $requestedEndDate) {
    $windowEnd = $windowStart.AddDays(119)
    if ($windowEnd -gt $requestedEndDate) {
        $windowEnd = $requestedEndDate
    }

    $start = $windowStart.ToUniversalTime().ToString("yyyy-MM-ddT00:00:00.000")
    $end = $windowEnd.ToUniversalTime().ToString("yyyy-MM-ddT23:59:59.999")
    $startIndex = 0
    $windowFetched = 0
    $windowItems = @()

    Write-Host "Window $($windowStart.ToString('yyyy-MM-dd')) through $($windowEnd.ToString('yyyy-MM-dd'))"

    do {
        $query = "?pubStartDate=$start&pubEndDate=$end&startIndex=$startIndex&resultsPerPage=$pageSize"
        $headers = @{}
        if ($ApiKey) {
            $headers["apiKey"] = $ApiKey
        }

        $response = $null
        for ($attempt = 1; $attempt -le 6; $attempt++) {
            try {
                $response = Invoke-RestMethod -Uri "$baseUri$query" -Headers $headers
                break
            } catch {
                if ($ApiKey -and $attempt -eq 1) {
                    Write-Warning "NVD rejected the request while using an API key. Retrying this page without the key. Check that NVD_API_KEY is the exact key value with no quotes, labels, or extra spaces."
                    $headers = @{}
                } elseif ($attempt -lt 6) {
                    $sleepSeconds = 10 * $attempt
                    Write-Warning "NVD request failed on attempt $attempt. Retrying in $sleepSeconds seconds. $($_.Exception.Message)"
                    Start-Sleep -Seconds $sleepSeconds
                } else {
                    throw
                }
            }
        }

        if ($response.vulnerabilities) {
            $windowItems += $response.vulnerabilities
            $totalFetched += $response.vulnerabilities.Count
            $windowFetched += $response.vulnerabilities.Count
        }
        $total = [int]$response.totalResults
        $count = [int]$response.resultsPerPage
        Write-Host "Fetched window $windowFetched / $total; total accumulated $totalFetched"
        $startIndex += $count

        if (-not $ApiKey) {
            Start-Sleep -Seconds 6
        } else {
            Start-Sleep -Seconds 1
        }
    } while ($startIndex -lt $total)

    $safeWindowStart = $windowStart.ToString("yyyyMMdd")
    $safeWindowEnd = $windowEnd.ToString("yyyyMMdd")
    $windowFile = Join-Path $outDir "nvd-cves-$safeWindowStart-to-$safeWindowEnd.json"

    [PSCustomObject]@{
        source = "NVD CVE API 2.0"
        pubStartDate = $windowStart.ToString("yyyy-MM-dd")
        pubEndDate = $windowEnd.ToString("yyyy-MM-dd")
        totalResults = $windowItems.Count
        fetchedAtUtc = [DateTime]::UtcNow.ToString("o")
        vulnerabilities = $windowItems
    } | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $windowFile -Encoding utf8

    $writtenFiles += [PSCustomObject]@{
        file = Split-Path $windowFile -Leaf
        pubStartDate = $windowStart.ToString("yyyy-MM-dd")
        pubEndDate = $windowEnd.ToString("yyyy-MM-dd")
        totalResults = $windowItems.Count
    }
    Write-Host "Wrote $windowFile"

    $windowItems = @()
    [System.GC]::Collect()

    $windowStart = $windowEnd.AddDays(1)
}

$safeStart = $StartDate -replace "[^0-9]", ""
$safeEnd = $EndDate -replace "[^0-9]", ""
$outFile = Join-Path $outDir "nvd-cves-$safeStart-to-$safeEnd-manifest.json"

[PSCustomObject]@{
    source = "NVD CVE API 2.0"
    pubStartDate = $StartDate
    pubEndDate = $EndDate
    totalResults = $totalFetched
    fetchedAtUtc = [DateTime]::UtcNow.ToString("o")
    files = $writtenFiles
} | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $outFile -Encoding utf8

Write-Host "Wrote $outFile"

if ($SyncToS3) {
    $destination = "s3://$BucketName/datasets/nvd/raw/"
    Write-Host "Syncing to $destination"
    & $aws s3 sync $outDir $destination --profile $Profile --no-progress
    if ($LASTEXITCODE -ne 0) {
        throw "S3 sync failed for NVD"
    }
}
