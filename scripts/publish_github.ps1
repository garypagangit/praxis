param(
    [string]$GitHubUser = $env:USERNAME,
    [string]$RepoName = "praxis",
    [ValidateSet("public", "private")]
    [string]$Visibility = "public",
    [switch]$CreateRepo,
    [switch]$Push
)

$ErrorActionPreference = "Stop"

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments = @()
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

function Resolve-Tool {
    param(
        [string]$CommandName,
        [string[]]$FallbackPaths = @()
    )

    $command = Get-Command $CommandName -ErrorAction SilentlyContinue
    if ($command -and $command.Source -and (Test-Path -LiteralPath $command.Source)) {
        return $command.Source
    }

    foreach ($candidate in $FallbackPaths) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }

    throw "Could not find required tool: $CommandName"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$gitExe = Resolve-Tool -CommandName "git" -FallbackPaths @("C:\Program Files\Git\cmd\git.exe")
$ghExe = Resolve-Tool -CommandName "gh" -FallbackPaths @("C:\Program Files\GitHub CLI\gh.exe")
$remoteUrl = "https://github.com/$GitHubUser/$RepoName.git"

$hasOrigin = $false
try {
    & $gitExe -C $repoRoot remote get-url origin | Out-Null
    $hasOrigin = $LASTEXITCODE -eq 0
} catch {
    $hasOrigin = $false
}

if ($hasOrigin) {
    Invoke-Checked -FilePath $gitExe -Arguments @("-C", $repoRoot, "remote", "set-url", "origin", $remoteUrl)
} else {
    Invoke-Checked -FilePath $gitExe -Arguments @("-C", $repoRoot, "remote", "add", "origin", $remoteUrl)
}

Write-Host "Origin set to $remoteUrl"

if ($CreateRepo) {
    & $ghExe auth status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI is not logged in. Run: gh auth login --web --git-protocol https"
    }

    & $ghExe repo view "$GitHubUser/$RepoName" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        $createArgs = @("repo", "create", "$GitHubUser/$RepoName")
        if ($Visibility -eq "private") {
            $createArgs += "--private"
        } else {
            $createArgs += "--public"
        }
        $createArgs += @("--source", $repoRoot, "--remote", "origin")
        Invoke-Checked -FilePath $ghExe -Arguments $createArgs
    } else {
        Write-Host "GitHub repository already exists: $GitHubUser/$RepoName"
    }
}

if ($Push) {
    Invoke-Checked -FilePath $gitExe -Arguments @("-C", $repoRoot, "push", "-u", "origin", "main")
}

Write-Host ""
Write-Host "Next commands:"
Write-Host "  gh auth login --web --git-protocol https"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 -GitHubUser $GitHubUser -RepoName $RepoName -CreateRepo -Push"
