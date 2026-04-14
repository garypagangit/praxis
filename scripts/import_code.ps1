param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath,
    [string]$Destination = "src\praxis\imported",
    [switch]$Preview
)

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Copy-FromDirectory {
    param(
        [string]$SourceDirectory,
        [string]$TargetRoot,
        [switch]$PreviewOnly
    )

    $copiedPaths = New-Object System.Collections.Generic.List[string]
    $sourceRoot = Get-Item -LiteralPath $SourceDirectory
    $files = Get-ChildItem -LiteralPath $sourceRoot.FullName -Recurse -File | Where-Object {
        -not (Test-SkippedPath -FullName $_.FullName)
    }

    foreach ($file in $files) {
        $relative = $file.FullName.Substring($sourceRoot.FullName.Length).TrimStart('\')
        $target = Join-Path $TargetRoot $relative
        $targetDir = Split-Path -Parent $target
        if (-not $PreviewOnly) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            Copy-Item -LiteralPath $file.FullName -Destination $target -Force
        }
        $copiedPaths.Add($target) | Out-Null
    }

    return $copiedPaths
}

function Test-SkippedPath {
    param(
        [string]$FullName
    )

    $skipMarkers = @(
        "\.git\",
        "\.venv\",
        "\venv\",
        "\__pycache__\",
        "\.ipynb_checkpoints\",
        "\node_modules\"
    )

    foreach ($marker in $skipMarkers) {
        if ($FullName -like "*$marker*") {
            return $true
        }
    }

    return $false
}

$repoRoot = Get-RepoRoot
$resolvedSource = (Resolve-Path -LiteralPath $SourcePath).Path
$destinationRoot = Join-Path $repoRoot $Destination

if (-not (Test-Path -LiteralPath $resolvedSource)) {
    throw "Source path not found: $SourcePath"
}

if ($resolvedSource.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Source path is already inside this repo. Choose an external folder, zip contents, or repo checkout."
}

$copied = New-Object System.Collections.Generic.List[string]

if (Test-Path -LiteralPath $resolvedSource -PathType Leaf) {
    $sourceFile = Get-Item -LiteralPath $resolvedSource

    if ($sourceFile.Extension -ieq ".zip") {
        $tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("praxis-import-" + [System.Guid]::NewGuid().ToString("N"))
        try {
            New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
            Expand-Archive -LiteralPath $resolvedSource -DestinationPath $tempRoot -Force
            $expandedSource = $tempRoot
            if (-not (Test-Path -LiteralPath $expandedSource)) {
                throw "Could not expand archive: $resolvedSource"
            }
            $fromArchive = Copy-FromDirectory -SourceDirectory $expandedSource -TargetRoot $destinationRoot -PreviewOnly:$Preview
            foreach ($path in $fromArchive) {
                $copied.Add($path) | Out-Null
            }
        } finally {
            if (Test-Path -LiteralPath $tempRoot) {
                Remove-Item -LiteralPath $tempRoot -Recurse -Force
            }
        }
    } else {
        $destinationHasExtension = [System.IO.Path]::HasExtension($destinationRoot)
        $target = if ($destinationHasExtension) {
            $destinationRoot
        } else {
            Join-Path $destinationRoot $sourceFile.Name
        }
        $parent = Split-Path -Parent $target
        if (-not $Preview) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
            Copy-Item -LiteralPath $resolvedSource -Destination $target -Force
        }
        $copied.Add($target) | Out-Null
    }
} else {
    $fromDirectory = Copy-FromDirectory -SourceDirectory $resolvedSource -TargetRoot $destinationRoot -PreviewOnly:$Preview
    foreach ($path in $fromDirectory) {
        $copied.Add($path) | Out-Null
    }
}

Write-Host ""
if ($Preview) {
    Write-Host "Preview only. These paths would be created or updated:"
} else {
    Write-Host "Import complete. These paths were created or updated:"
}

$copied | Select-Object -First 50 | ForEach-Object { Write-Host "  $_" }

if ($copied.Count -gt 50) {
    Write-Host "  ... plus $($copied.Count - 50) more"
}

Write-Host ""
Write-Host "Next:"
Write-Host "  1. Review the imported files."
Write-Host "  2. Update requirements.txt if the code needs extra packages."
Write-Host "  3. Tell Codex which imported file should become the main training entrypoint."
