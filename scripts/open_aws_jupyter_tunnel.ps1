param(
    [Parameter(Mandatory = $true)]
    [string]$Host,
    [string]$User = "ubuntu",
    [int]$LocalPort = 8888,
    [int]$RemotePort = 8888,
    [string]$KeyPath = ""
)

$ErrorActionPreference = "Stop"

$forwardSpec = "{0}:127.0.0.1:{1}" -f $LocalPort, $RemotePort
$targetHost = "{0}@{1}" -f $User, $Host
$sshArgs = @("-N", "-L", $forwardSpec, $targetHost)

if ($KeyPath) {
    $sshArgs = @("-i", $KeyPath) + $sshArgs
}

Write-Host ("Opening tunnel: http://127.0.0.1:{0} -> {1}@{2}:{3}" -f $LocalPort, $User, $Host, $RemotePort)
Write-Host "Leave this terminal window open while using Jupyter."

& ssh @sshArgs
