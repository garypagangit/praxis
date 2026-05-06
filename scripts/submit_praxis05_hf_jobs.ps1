param(
    [string]$OutputRepo = "",
    [string]$Flavor = "a10g-large",
    [string]$Timeout = "12h",
    [string]$RepoRef = "feature/two-stage-attack-mlp"
)

$ErrorActionPreference = "Stop"

$hf = "$env:USERPROFILE\.venvs\praxis05\Scripts\hf.exe"
if (!(Test-Path $hf)) {
    throw "HF CLI not found at $hf. Create the Praxis 5 venv first or install huggingface_hub."
}

if (-not $OutputRepo) {
    $whoami = & $hf auth whoami 2>$null
    if ($LASTEXITCODE -eq 0 -and $whoami) {
        $namespace = ($whoami | Select-Object -First 1).Trim()
        $OutputRepo = "$namespace/praxis05-phase-a-full-magic"
    } else {
        throw "Provide -OutputRepo username/praxis05-phase-a-full-magic after logging in with `"$hf auth login`"."
    }
}

& $hf jobs uv run jobs/praxis05/hf_phase_a_full_magic.py `
    --flavor $Flavor `
    --timeout $Timeout `
    --secrets HF_TOKEN `
    --detach `
    -- `
    --repo-ref $RepoRef `
    --output-repo $OutputRepo
