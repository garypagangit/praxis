param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [switch]$Full
)

$ErrorActionPreference = "Stop"
$configs = @(
    "configs\praxis04-baseline-single.json",
    "configs\praxis04-baseline-tse.json",
    "configs\praxis04-treatment-stage.json",
    "configs\praxis04-ablation-nostage.json",
    "configs\praxis04-ablation-oraclestage.json"
)

foreach ($config in $configs) {
    $configJson = Get-Content $config -Raw | ConvertFrom-Json
    foreach ($seed in $configJson.seeds) {
        $runName = "$($configJson.name)_seed$seed"
        if ($Full) {
            & $Python -m praxis.praxis04.train --config $config --seed $seed --output-dir "runs\$runName"
        } else {
            & $Python "scripts\run_praxis04_smoke.py" --config $config --seed $seed --output-dir "runs\$runName"
        }
    }
}

& $Python "scripts\analyze_praxis04.py" --results-dir "runs" --output "runs\praxis04_headline_table.csv"
