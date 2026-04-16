# Single IDE Pipeline

This is the easiest no-switching workflow for Praxis.

## Default setup

- GitHub stores the code
- Amazon SageMaker Code Editor is the IDE
- The same SageMaker workspace runs the models
- The workspace EBS volume stores the repo, caches, and run outputs
- Google Drive stays optional as a later backup path, not a requirement for day one

## Why this is easier than Colab

- one place to code and run
- no runtime resets between sessions
- no repeated package installs every time you reopen a notebook
- no switching back and forth between Codex and Colab for normal work

## One-time AWS setup

1. Open the SageMaker AI console.
2. Create a domain with `Set up for single user (Quick setup)`.
3. Open Studio.
4. Create a `Code Editor` space.
5. Choose a GPU instance and a GPU-based image if you want GPU training.
6. Give the space enough EBS storage for the repo and data.

## First-time workspace setup

In the Code Editor terminal:

```bash
git clone https://x-access-token:YOUR_GITHUB_TOKEN@github.com/garypagangit/praxis.git
cd praxis
bash scripts/setup_sagemaker_code_editor.sh
```

## First proof run

This does not require the Unraveled dataset yet:

```bash
bash scripts/run_synthetic_smoke.sh
```

That writes outputs to:

```text
runs/synthetic-smoke/
```

## Real Praxis smoke run after data upload

Upload the Unraveled dataset into:

```text
~/SageMaker/praxis-storage/data/unraveled/network-flows
```

Then run:

```bash
bash scripts/link_unraveled_data.sh
bash scripts/run_praxisv03_ide_smoke.sh
```

That writes outputs to:

```text
runs/praxisv03-unraveled-ide-smoke/
```

## What this gives you

- one cloud IDE instead of an IDE plus a separate notebook service
- GitHub-backed code you can open from any machine
- a quick synthetic run for environment validation
- a clear next step for the real Praxisv03 pipeline

## When to use Colab or Drive

- Use Colab only if you need a temporary extra GPU environment
- Use Google Drive as optional backup or export storage later
- Do not make Drive the primary live workspace for this setup
