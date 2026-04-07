param(
    [string]$SourceDirectory = "$HOME\Downloads",
    [string]$RawDataDir = "data\raw\dapt2020",
    [string]$ProcessedDir = "data\processed\dapt2020",
    [switch]$SkipConsolidation
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Get-NetworkType {
    param(
        [string]$FileName
    )

    $name = $FileName.ToLowerInvariant()

    if ($name.Contains("public") -or
        ($name.Contains("enp0s3-monday.pcap") -and -not $name.Contains("pvt")) -or
        ($name.Contains("enp0s3-tcpdump-friday.pcap") -and -not $name.Contains("pvt"))) {
        return "public"
    }

    if ($name.Contains("pvt") -or $name.Contains("private")) {
        return "private"
    }

    return "unknown"
}

function Get-DayName {
    param(
        [string]$FileName
    )

    $name = $FileName.ToLowerInvariant()
    foreach ($day in @("monday", "tuesday", "wednesday", "thursday", "friday")) {
        if ($name.Contains($day)) {
            return $day
        }
    }

    return "unknown"
}

$repoRoot = Get-RepoRoot
$sourceRoot = (Resolve-Path -LiteralPath $SourceDirectory).Path
$rawRoot = Join-Path $repoRoot $RawDataDir
$processedRoot = Join-Path $repoRoot $ProcessedDir
$combinedCsv = Join-Path $processedRoot "combined_flows.csv"
$summaryPath = Join-Path $processedRoot "summary.json"

$expectedFiles = @(
    "enp0s3-monday-pvt.pcap_Flow.csv",
    "enp0s3-monday.pcap_Flow.csv",
    "enp0s3-public-thursday.pcap_Flow.csv",
    "enp0s3-public-tuesday.pcap_Flow.csv",
    "enp0s3-public-wednesday.pcap_Flow.csv",
    "enp0s3-pvt-thursday.pcap_Flow.csv",
    "enp0s3-pvt-tuesday.pcap_Flow.csv",
    "enp0s3-pvt-wednesday.pcap_Flow.csv",
    "enp0s3-tcpdump-friday.pcap_Flow.csv",
    "enp0s3-tcpdump-pvt-friday.pcap_Flow.csv"
)

New-Item -ItemType Directory -Path $rawRoot -Force | Out-Null
New-Item -ItemType Directory -Path $processedRoot -Force | Out-Null

$copiedFiles = New-Object System.Collections.Generic.List[string]

foreach ($fileName in $expectedFiles) {
    $sourcePath = Join-Path $sourceRoot $fileName
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        throw "Missing expected source file: $sourcePath"
    }

    $targetPath = Join-Path $rawRoot $fileName
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    $copiedFiles.Add($targetPath) | Out-Null
}

Write-Host ""
Write-Host "Copied raw CSV files:"
$copiedFiles | ForEach-Object { Write-Host "  $_" }

if (-not $SkipConsolidation) {
    if (Test-Path -LiteralPath $combinedCsv) {
        Remove-Item -LiteralPath $combinedCsv -Force
    }

    $combinedWriter = [System.IO.StreamWriter]::new($combinedCsv, $false, [System.Text.UTF8Encoding]::new($false))
    $summary = [ordered]@{
        generated_at = (Get-Date).ToString("o")
        raw_data_dir = $rawRoot
        combined_csv = $combinedCsv
        files = @()
        total_rows = 0
    }

    try {
        $headerWritten = $false
        $referenceHeader = $null

        foreach ($fileName in $expectedFiles) {
            $path = Join-Path $rawRoot $fileName
            $networkType = Get-NetworkType -FileName $fileName
            $day = Get-DayName -FileName $fileName

            $reader = [System.IO.StreamReader]::new($path)
            try {
                $header = $reader.ReadLine()
                if (-not $header) {
                    Write-Warning "No header found in $fileName"
                    continue
                }

                if (-not $headerWritten) {
                    $combinedWriter.WriteLine($header + ',network_type,day,source_file')
                    $referenceHeader = $header
                    $headerWritten = $true
                } elseif ($header -eq $referenceHeader) {
                    # Same header as the reference file; continue normally.
                } else {
                    Write-Warning "Header missing or different in $fileName; treating first line as data and using the reference header."
                    $combinedWriter.WriteLine($header + ",$networkType,$day,$fileName")
                    $rowCount = 1
                    while (($line = $reader.ReadLine()) -ne $null) {
                        if ([string]::IsNullOrWhiteSpace($line)) {
                            continue
                        }
                        $combinedWriter.WriteLine($line + ",$networkType,$day,$fileName")
                        $rowCount += 1
                    }

                    $summary.files += [ordered]@{
                        file_name = $fileName
                        network_type = $networkType
                        day = $day
                        rows = $rowCount
                    }
                    $summary.total_rows += $rowCount
                    continue
                }

                $rowCount = 0
                while (($line = $reader.ReadLine()) -ne $null) {
                    if ([string]::IsNullOrWhiteSpace($line)) {
                        continue
                    }
                    $combinedWriter.WriteLine($line + ",$networkType,$day,$fileName")
                    $rowCount += 1
                }

                if ($rowCount -eq 0) {
                    Write-Warning "No data rows found in $fileName"
                }

                $summary.files += [ordered]@{
                    file_name = $fileName
                    network_type = $networkType
                    day = $day
                    rows = $rowCount
                }
                $summary.total_rows += $rowCount
            } finally {
                $reader.Dispose()
            }
        }
    } finally {
        $combinedWriter.Dispose()
    }

    $summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding utf8

    Write-Host ""
    Write-Host "Consolidated dataset:"
    Write-Host "  $combinedCsv"
    Write-Host "Summary:"
    Write-Host "  $summaryPath"
    Write-Host "Total rows: $($summary.total_rows)"
}
