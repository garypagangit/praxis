# Praxis Easy Start Pipeline

This is the easiest working setup for Praxis when you want to code from Codex and run models without turning cloud setup into a second project.

## Recommended Default

- Code and notebooks live in GitHub: `garypagangit/praxis`
- Coding happens locally in Codex
- Quick model runs happen in Google Colab
- Persistent data and run artifacts live in Google Drive
- AWS is optional later for long or expensive runs

## Why this is the best starting point

- GitHub gives you one source of truth across machines
- Colab gives you GPU access without maintaining a server
- Google Drive gives you persistent storage without extra infrastructure
- Codex stays focused on editing code and launching small local checks

## Storage layout

Use this Drive layout:

- `/content/drive/MyDrive/praxis/data/unraveled/network-flows`
- `/content/drive/MyDrive/praxis/runs`
- `/content/drive/MyDrive/praxis/cache`

This repo now creates those top-level folders automatically from Colab.

## Day 1 setup

1. Keep using the existing GitHub repo: `garypagangit/praxis`
2. Create a fine-grained GitHub token with access only to that repo
3. Open Colab and set the runtime to `GPU`
4. Mount Google Drive in Colab
5. Clone the repo from GitHub into `/content/praxis-workspace`
6. Install the repo
7. Put the Unraveled dataset in Drive
8. Run the smoke config first

## Exact Colab cells

Cell 1:

```python
from getpass import getpass
from urllib.parse import quote

github_token = getpass("GitHub token for garypagangit/praxis: ").strip()
%pip install -q "git+https://x-access-token:{quote(github_token, safe='')}@github.com/garypagangit/praxis.git"

from praxis.colab_bootstrap import setup_easy_colab

paths = setup_easy_colab(
    repo_slug="garypagangit/praxis",
    branch="main",
    github_token=github_token,
)
paths
```

Cell 2:

```python
from pathlib import Path

data_dir = Path("/content/drive/MyDrive/praxis/data/unraveled/network-flows")
print("Data dir exists:", data_dir.exists())
if data_dir.exists():
    print("Sample files:", sorted(p.name for p in data_dir.iterdir())[:5])
```

Cell 3:

```python
%cd /content/praxis-workspace
!python -m praxis.train --config configs/praxisv03-unraveled-colab-smoke.json
```

## First proof that the pipeline works

The smoke run is the first milestone. It proves:

- GitHub access works
- Colab can import the project
- Google Drive is mounted
- output artifacts can be written to Drive
- the training path works end-to-end

The smoke config is:

- [configs/praxisv03-unraveled-colab-smoke.json](C:/Users/garyp/OneDrive/Documents/codex/configs/praxisv03-unraveled-colab-smoke.json)

It is intentionally small:

- one epoch
- one Optuna trial
- one model
- outputs written to Drive

## After the smoke run

Move to the heavier Colab config:

- [configs/praxisv03-unraveled-colab-mamba-proper.json](C:/Users/garyp/OneDrive/Documents/codex/configs/praxisv03-unraveled-colab-mamba-proper.json)

Command:

```python
%cd /content/praxis-workspace
!python -m praxis.train --config configs/praxisv03-unraveled-colab-mamba-proper.json
```

## What Codex does well in this setup

- edit code locally
- edit configs locally
- commit and push to GitHub
- inspect results after you pull them back from Drive or GitHub
- run small local smoke tests before sending larger runs to Colab

## When to use AWS

Add AWS only when one of these becomes true:

- Colab time limits keep interrupting long runs
- you want a machine that stays alive between sessions
- you want larger and more predictable GPU capacity

When that happens, use SageMaker notebook or Studio first, not raw EC2. It is simpler to operate if you are still getting comfortable with AWS.
