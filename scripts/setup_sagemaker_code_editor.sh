#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "Repo: ${REPO_DIR}"

if command -v sudo >/dev/null 2>&1 && sudo -n true >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    git \
    python3-venv
else
  echo "Skipping apt package install because passwordless sudo is not available."
fi

cd "${REPO_DIR}"

if [[ ! -d ".venv" ]]; then
  "${PYTHON_BIN}" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip

for req_file in requirements-local.txt requirements.txt requirements-dev.txt; do
  if [[ -f "${req_file}" ]]; then
    python -m pip install -r "${req_file}"
  fi
done

python -m pip install --no-build-isolation -e .

mkdir -p \
  runs \
  data/processed/unraveled_v02 \
  data/processed/unraveled_v03

python - <<'PY'
import platform
print("Python:", platform.python_version())
try:
    import torch
    print("CUDA available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("GPU:", torch.cuda.get_device_name(0))
except Exception as exc:
    print("Torch check failed:", exc)
PY

cat <<'EOF'

Workspace ready.

First quick proof run:
  bash scripts/run_synthetic_smoke.sh

When the Unraveled dataset is uploaded:
  bash scripts/link_unraveled_data.sh
  bash scripts/run_praxisv03_ide_smoke.sh
EOF
