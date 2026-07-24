param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [string]$OutputDir = "data\cic-ids-2017",
    [string]$RetrievalUrl = "https://www.unb.ca/cic/datasets/ids-2017.html",
    [string]$Distribution = "official"
)

$ErrorActionPreference = "Stop"
$resolvedArchive = (Resolve-Path -LiteralPath $ArchivePath).Path
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $OutputDir))

if ([System.IO.Path]::GetExtension($resolvedArchive) -ne ".zip") {
    throw "Expected the official MachineLearningCSV.zip archive."
}

$signature = [System.IO.File]::ReadAllBytes($resolvedArchive)[0..3]
if (-not ($signature[0] -eq 0x50 -and $signature[1] -eq 0x4B)) {
    throw "The supplied file is not a ZIP archive. The CIC download form may have returned HTML."
}

New-Item -ItemType Directory -Path $resolvedOutput -Force | Out-Null
Expand-Archive -LiteralPath $resolvedArchive -DestinationPath $resolvedOutput -Force

$csvFiles = Get-ChildItem -LiteralPath $resolvedOutput -Recurse -Filter "*.csv" -File
if ($csvFiles.Count -lt 8) {
    throw "Expected at least eight CICIDS2017 machine-learning CSV files; found $($csvFiles.Count)."
}

$manifest = foreach ($file in $csvFiles) {
    [pscustomobject]@{
        path = $file.FullName.Substring($resolvedOutput.Length).TrimStart("\")
        size_bytes = $file.Length
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$manifestPath = Join-Path $resolvedOutput "manifest.json"
$payload = [ordered]@{
    dataset = "CICIDS2017"
    publisher_page = "https://www.unb.ca/cic/datasets/ids-2017.html"
    retrieval_url = $RetrievalUrl
    distribution = $Distribution
    archive = $resolvedArchive
    archive_size_bytes = (Get-Item -LiteralPath $resolvedArchive).Length
    archive_sha256 = (Get-FileHash -LiteralPath $resolvedArchive -Algorithm SHA256).Hash.ToLowerInvariant()
    archive_md5 = (Get-FileHash -LiteralPath $resolvedArchive -Algorithm MD5).Hash.ToLowerInvariant()
    extracted_at_utc = [DateTime]::UtcNow.ToString("o")
    files = $manifest
}
[System.IO.File]::WriteAllText(
    $manifestPath,
    ($payload | ConvertTo-Json -Depth 8),
    [System.Text.UTF8Encoding]::new($false)
)

Write-Output "Prepared CICIDS2017 under $resolvedOutput"
Write-Output "Manifest: $manifestPath"
