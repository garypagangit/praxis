# Praxis Starter Workspace

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

The setup script auto-detects common Python install locations if the plain `python` command is still pointing at the Windows Store alias.

## Push to GitHub

When you are ready to back this up or run from standalone Colab:

```powershell
gh auth login --web --git-protocol https
powershell -ExecutionPolicy Bypass -File .\scripts\publish_github.ps1 -GitHubUser YOUR-USER -RepoName praxis -CreateRepo -Push
```

If the GitHub repo already exists, you can omit `-CreateRepo`.

## Run on Colab

Open `Praxisv01.ipynb` and do one of these:

- If you are using VS Code with a mounted Colab server, leave `REPO_URL` blank and run the setup cells.
- If you are using standalone Colab in the browser, set `REPO_URL` to your GitHub repo URL and run the setup cells to clone, install, and launch your code.

The notebook installs the repo in editable mode, so any code you push to GitHub can be pulled and run from Colab compute.

## First files to edit

- `src/praxis/train.py`
- `configs/example.json`
- `requirements.txt`

Once you share a GitHub repo URL, the next useful step is wiring `origin` and pushing this project upstream from here.
