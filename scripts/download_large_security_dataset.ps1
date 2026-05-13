param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("darpa-tc-e5", "darpa-tc-e3", "optc")]
    [string]$Dataset,

    [string]$OutputRoot = "external\datasets\large",
    [switch]$SyncToS3,
    [string]$BucketName = "praxis-garypagan-272615233626-us-east-1",
    [string]$Profile = "praxis-build"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (!(Test-Path -LiteralPath $python)) {
    $python = "python"
}

$aws = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
if (!(Test-Path -LiteralPath $aws)) {
    $aws = "aws"
}

$sources = @{
    "darpa-tc-e5" = @{
        Url = "https://drive.google.com/drive/folders/1okt4AYElyBohW4XiOBqmsvjwXsnUjLVf"
        S3 = "datasets/darpa-tc/raw/engagement-5/"
        Note = "DARPA TC Engagement 5. Very large; choose this for MAGIC/Kairos-style provenance graph work."
    }
    "darpa-tc-e3" = @{
        Url = "https://drive.google.com/open?id=1QlbUFWAGq3Hpl8wVdzOdIoZLFxkII4EK"
        S3 = "datasets/darpa-tc/raw/engagement-3/"
        Note = "DARPA TC Engagement 3. Very large; useful for older Cadets/Theia/Trace provenance baselines."
    }
    "optc" = @{
        Url = "https://drive.google.com/drive/u/0/folders/1n3kkS3KR31KUegn42yk3-e6JkZvf0Caa"
        S3 = "datasets/optc/raw/full-drive-mirror/"
        Note = "OpTC full release. Roughly terabyte-scale compressed JSON; prefer a targeted cloud download if possible."
    }
}

$source = $sources[$Dataset]
$outDir = Join-Path $repoRoot (Join-Path $OutputRoot $Dataset)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Dataset: $Dataset"
Write-Host $source.Note
Write-Host "Source:  $($source.Url)"
Write-Host "Output:  $outDir"
Write-Host ""
Write-Host "Starting public Google Drive folder download via gdown."
Write-Host "This can be very large. Stop with Ctrl+C if you did not intend to mirror the full folder."
Write-Host ""

& $python -m gdown --folder $source.Url --output $outDir --remaining-ok
if ($LASTEXITCODE -ne 0) {
    throw "gdown failed for $Dataset"
}

if ($SyncToS3) {
    $destination = "s3://$BucketName/$($source.S3)"
    Write-Host "Syncing to $destination"
    & $aws s3 sync $outDir $destination --profile $Profile --no-progress
    if ($LASTEXITCODE -ne 0) {
        throw "S3 sync failed for $Dataset"
    }
}

Write-Host ""
Write-Host "Done."
