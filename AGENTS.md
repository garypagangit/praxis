# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Praxis is a Python ML research workspace for APT (Advanced Persistent Threat) detection in network traffic. It is a single Python package (`src/praxis/`) — no web servers, databases, or Docker services.

### Environment

- Python 3.12+ (satisfies the `requires-python = ">=3.11"` constraint in `pyproject.toml`)
- Virtual environment at `.venv/`
- PyTorch is installed as CPU-only (no GPU in Cloud Agent VMs)

### Key commands

| Action | Command |
|--------|---------|
| Activate venv | `source .venv/bin/activate` |
| Lint | `ruff check src/` |
| Tests | `python -m pytest tests/ -v` |
| Synthetic smoke (no data needed) | `python -m praxis.train --config configs/synthetic-smoke.json` |
| Praxis04 smoke (no data needed) | `python -m praxis.praxis04.train --config configs/praxis04-treatment-stage.json --smoke` |

### Gotchas

- The `requirements.txt` pulls in `torch-geometric==2.4.0` which is pinned. If you see version conflicts, install PyTorch first (CPU: `pip install torch --index-url https://download.pytorch.org/whl/cpu`) before installing `torch-geometric==2.4.0`.
- The `synthetic_smoke` and `praxis04 --smoke` pipelines generate synthetic data internally; they require **zero external datasets** and are the recommended way to validate the environment.
- Real dataset pipelines (DAPT2020, Unraveled, CIC-IDS2018) require external CSV data that is not in the repo. Only use `synthetic_smoke` or `--smoke` flags for environment validation.
- Ruff reports 5 pre-existing `F541` lint warnings in `src/praxis/praxisv04.py` (f-strings without placeholders). These are harmless.
- The `ensurepip` module may not be available in the base system Python. Create the venv with `python3 -m venv --without-pip .venv` and then bootstrap pip with `curl -sSL https://bootstrap.pypa.io/get-pip.py | .venv/bin/python`.
