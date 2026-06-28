# Praxis Research

The publishable experiment tracker is:

[Praxis Research Experiment Tracker](reports/PRAXIS_RESEARCH_EXPERIMENT_TRACKER.html)

This dashboard is the front-door overview for completed, active, negative, blocked, and future Praxis experiments. Each tracked experiment has a stable `PX-###` ID, title, objective/evidence record, short findings/status summary, and links to supporting code, documents, results, and source artifacts.

## Experiment Portfolio

The Markdown publication index is tracked in [EXPERIMENTS.md](EXPERIMENTS.md). It is kept as the source-readable portfolio index, while the HTML tracker above is the clean dashboard for GitHub review and project navigation.

This repository is now set up as a small, clean starting point for an AI project that you edit locally and run on Colab compute.

## What goes where

- Put your Python package code in `src/praxis/`.
- Put experiment settings in `configs/`.
- Keep notebooks in the repo root or move them into a `notebooks/` folder later.
- Model outputs, checkpoints, and datasets are ignored by Git.

## Fast local start

1. Install Python 3.11 on this machine.
2. Run `.\scripts\setup_local.ps1`.
3. Activate the interpreter at `.venv\Scripts\python.exe` in VS Code.
4. Start from `src/praxis/train.py` and `configs/example.json`.
5. Run `.\scripts\run_train.ps1` for a smoke test.

The setup script auto-detects common Python install locations if the plain `python` command is still pointing at the Windows Store alias. It also installs a small dev-tool layer from `requirements-dev.txt` so each machine gets the same Jupyter and test tooling.

## Multi-Machine Recommendation

For the smoothest setup across laptops and cloud machines:

- Keep the active Git clone in a normal folder such as `C:\dev\praxis` instead of working directly out of OneDrive. OneDrive is fine for backups, but it can slow large Python and notebook workloads.
- Use GitHub as the source of truth for code and notebooks, then clone the repo onto each machine.
- Keep datasets, run outputs, checkpoints, and caches local. They are already ignored by Git.
- Use the existing Colab notebooks when you want cloud compute without moving your whole local setup.

This repo includes a tracked `.python-version` file so future machines can align on Python 3.11 quickly.

## Push to GitHub

When you are ready to back this up or run from standalone Colab:

```powershell
git add .
git commit -m "Initial Praxis workspace"
gh auth login --web --git-protocol https
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 -GitHubUser YOUR-USER -RepoName praxis -CreateRepo -Push
```

If the GitHub repo already exists, you can omit `-CreateRepo`. The publish script will also reinitialize the repo if the local `.git` pointer has gone stale.

If you prefer not to install GitHub CLI, create an empty private GitHub repo in the browser first, then run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 -GitHubUser YOUR-USER -RepoName praxis
git push -u origin main
```

## Colab Quick Start

This is the simplest path to using Praxis from multiple machines:

1. Create an empty private GitHub repo in the browser, for example `YOUR-GITHUB-USER/praxis`.
2. From this machine, commit your local repo and push it to that GitHub repo.
3. In Colab, open [Praxisv01.ipynb](C:/Users/garyp/OneDrive/Documents/codex/Praxisv01.ipynb) or [Praxisv03_Colab.ipynb](C:/Users/garyp/OneDrive/Documents/codex/Praxisv03_Colab.ipynb).
4. Set the repo value at the top of the notebook to your own GitHub repo.
5. If the repo is private, use a GitHub fine-grained personal access token with read access when Colab prompts for it.

Current defaults in this repo:

- `Praxisv01.ipynb`: `REPO_URL = "https://github.com/garypagangit/praxis.git"`
- `Praxisv03_Colab.ipynb`: `REPO_SLUG = "garypagangit/praxis"` and `BRANCH = "main"`

Keep datasets and run outputs in Drive or local machine storage. Keep code and notebooks in GitHub.

If you want the single easiest fresh-start workflow, use the new guide in [PIPELINE_EASY_START.md](C:/Users/garyp/OneDrive/Documents/codex/PIPELINE_EASY_START.md). It standardizes on:

- Codex for coding
- GitHub for source control
- Colab for compute
- Google Drive for persistent datasets and run artifacts

The quickest first proof run is now:

```python
from getpass import getpass
from urllib.parse import quote

token = getpass("GitHub token: ").strip()
%pip install -q "git+https://x-access-token:{quote(token, safe='')}@github.com/garypagangit/praxis.git"

from praxis.colab_bootstrap import setup_easy_colab

paths = setup_easy_colab(
    repo_slug="garypagangit/praxis",
    branch="main",
    github_token=token,
)
```

Then run:

```python
%cd /content/praxis-workspace
!python -m praxis.train --config configs/praxisv03-unraveled-colab-smoke.json
```

## AWS Pipeline

If you want a persistent high-performance workflow instead of Colab runtime resets, use the AWS-first pipeline in [AWS_PIPELINE.md](C:/Users/garyp/OneDrive/Documents/codex/AWS_PIPELINE.md).

If your main goal is to stop switching between an editor and Colab, use the single-IDE guide in [SINGLE_IDE_PIPELINE.md](C:/Users/garyp/OneDrive/Documents/codex/SINGLE_IDE_PIPELINE.md). That path uses SageMaker Code Editor as both the editor and runtime, plus:

- [scripts/setup_sagemaker_code_editor.sh](C:/Users/garyp/OneDrive/Documents/codex/scripts/setup_sagemaker_code_editor.sh)
- [scripts/run_synthetic_smoke.sh](C:/Users/garyp/OneDrive/Documents/codex/scripts/run_synthetic_smoke.sh)
- [scripts/link_unraveled_data.sh](C:/Users/garyp/OneDrive/Documents/codex/scripts/link_unraveled_data.sh)
- [scripts/run_praxisv03_ide_smoke.sh](C:/Users/garyp/OneDrive/Documents/codex/scripts/run_praxisv03_ide_smoke.sh)

The fastest first run in that flow is:

```bash
bash scripts/setup_sagemaker_code_editor.sh
bash scripts/run_synthetic_smoke.sh
```

Highlights:

- upload the Unraveled dataset once to S3 with [sync_unraveled_to_s3.ps1](C:/Users/garyp/OneDrive/Documents/codex/scripts/sync_unraveled_to_s3.ps1)
- bootstrap a persistent GPU instance with [bootstrap_aws_gpu_ubuntu.sh](C:/Users/garyp/OneDrive/Documents/codex/scripts/bootstrap_aws_gpu_ubuntu.sh)
- run the AWS-targeted configs under `configs/praxisv03-unraveled-aws-*.json`

## Run on Colab

Open `Praxisv01.ipynb` and do one of these:

- If you are using VS Code with a mounted Colab server, leave `REPO_URL` blank and run the setup cells.
- If you are using standalone Colab in the browser, set `REPO_URL` to your GitHub repo URL and run the setup cells to clone, install, and launch your code.

The notebook installs the repo in editable mode, so any code you push to GitHub can be pulled and run from Colab compute.

For the Unraveled `praxisv03` Colab workflow and the next high-budget experiments, use `Praxisv03_Colab.ipynb` together with `COLAB_UNRAVELED_RUNBOOK.md`.

## Best Local Praxisv03 Pipeline

For the strongest proven local Unraveled setup so far, use the dedicated MLP champion pipeline:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_praxisv03_best.ps1 -Mode Smoke
```

That runs a one-epoch smoke validation with the fixed winning MLP hyperparameters and writes artifacts under `runs/praxisv03-unraveled-best-local-smoke/`.

When you are ready for the full local champion run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_praxisv03_best.ps1 -Mode Full
```

That writes artifacts under `runs/praxisv03-unraveled-best-local/`.

## First files to edit

- `src/praxis/train.py`
- `configs/example.json`
- `requirements.txt`

## Praxis 04 Stage Routing

The Praxis 04 preregistered plan lives in [PRAXIS04_TESTPLAN.md](C:/Users/garyp/OneDrive/Documents/codex/PRAXIS04_TESTPLAN.md).

Quick deterministic smoke:

```powershell
.\.venv\Scripts\python.exe -m praxis.praxis04.train --config configs\praxis04-treatment-stage.json --smoke
```

After downloading CIC-IDS2018 CSVs:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\download_praxis04_cicids2018.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_praxis04_all.ps1 -Full
```

## Bring In Existing Code

If you already have code in another folder, a single file, or a zip archive, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_code.ps1 -SourcePath C:\path\to\your\code
```

By default this copies the source into `src/praxis/imported/` and skips common junk folders like `.git`, `.venv`, `__pycache__`, and `.ipynb_checkpoints`.

If you want a different destination inside this repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_code.ps1 -SourcePath C:\path\to\your\code -Destination src\praxis\my_module
```

You can also use `-Preview` first to see what would be copied without changing anything.

## Import Local DAPT2020 CSV Data

To copy and consolidate the 10 local DAPT2020 CSV files into the repo:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\import_dapt2020_data.ps1 -SourceDirectory C:\Users\garyp\Downloads
```

This writes:

- raw files to `data/raw/dapt2020/`
- a combined dataset to `data/processed/dapt2020/combined_flows.csv`
- a summary file to `data/processed/dapt2020/summary.json`

The imported GML notebook bundle under `imports/gml_to_detect_apt_final/` is now configured to use those local paths instead of AWS/S3.
