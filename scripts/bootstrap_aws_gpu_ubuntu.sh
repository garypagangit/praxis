#!/usr/bin/env bash
set -euo pipefail

PRAXIS_ROOT="${PRAXIS_ROOT:-/mnt/praxis}"
REPO_URL="${REPO_URL:-https://github.com/garypagangit/praxis.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"
GITHUB_USER="${GITHUB_USER:-x-access-token}"

AUTH_REPO_URL="${REPO_URL}"
if [[ -n "${GITHUB_TOKEN}" && "${REPO_URL}" =~ ^https://github\.com/ ]]; then
  AUTH_REPO_URL="${REPO_URL/https:\/\/github.com\//https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/}"
fi

echo "Bootstrap root: ${PRAXIS_ROOT}"
echo "Repo: ${REPO_URL} (${REPO_BRANCH})"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git \
  htop \
  tmux \
  unzip \
  build-essential \
  python3-venv

sudo mkdir -p \
  "${PRAXIS_ROOT}/data/unraveled" \
  "${PRAXIS_ROOT}/cache/unraveled_v03" \
  "${PRAXIS_ROOT}/runs" \
  "${PRAXIS_ROOT}/logs"
sudo chown -R "${USER}:${USER}" "${PRAXIS_ROOT}"

REPO_DIR="${PRAXIS_ROOT}/repo"

if [[ -d "${REPO_DIR}/.git" ]]; then
  if [[ -n "${GITHUB_TOKEN}" ]]; then
    git -C "${REPO_DIR}" remote set-url origin "${AUTH_REPO_URL}"
  fi
  git -C "${REPO_DIR}" fetch origin "${REPO_BRANCH}"
  git -C "${REPO_DIR}" checkout "${REPO_BRANCH}"
  git -C "${REPO_DIR}" pull --ff-only origin "${REPO_BRANCH}"
else
  rm -rf "${REPO_DIR}"
  git clone --branch "${REPO_BRANCH}" "${AUTH_REPO_URL}" "${REPO_DIR}"
fi

git -C "${REPO_DIR}" remote set-url origin "${REPO_URL}"

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

python - <<'PY'
import sys
import torch
print("Python:", sys.version.split()[0])
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
PY

cat <<EOF

Bootstrap complete.

Repo: ${REPO_DIR}
Activate: source ${REPO_DIR}/.venv/bin/activate
Run Mamba:
  python -m praxis.train --config configs/praxisv03-unraveled-aws-mamba-proper.json
EOF
