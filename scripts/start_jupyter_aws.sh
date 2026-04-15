#!/usr/bin/env bash
set -euo pipefail

PRAXIS_ROOT="${PRAXIS_ROOT:-/mnt/praxis}"
REPO_DIR="${REPO_DIR:-${PRAXIS_ROOT}/repo}"
PORT="${PORT:-8888}"
HOST="${HOST:-127.0.0.1}"

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "Repo directory not found: ${REPO_DIR}"
  echo "Clone the repo into ${REPO_DIR} and run the bootstrap first."
  echo "If the repo is private, use a GitHub token during clone:"
  echo "  git clone https://x-access-token:YOUR_GITHUB_TOKEN@github.com/garypagangit/praxis.git ${REPO_DIR}"
  echo "  cd ${REPO_DIR}"
  echo "  GITHUB_TOKEN=YOUR_GITHUB_TOKEN ./scripts/bootstrap_aws_gpu_ubuntu.sh"
  exit 1
fi

cd "${REPO_DIR}"

if [[ ! -f ".venv/bin/activate" ]]; then
  echo "Virtualenv not found in ${REPO_DIR}/.venv"
  echo "Run:"
  echo "  cd ${REPO_DIR}"
  echo "  GITHUB_TOKEN=your_token_here ./scripts/bootstrap_aws_gpu_ubuntu.sh"
  exit 1
fi

source .venv/bin/activate

mkdir -p "${PRAXIS_ROOT}/logs"

if command -v tmux >/dev/null 2>&1; then
  tmux kill-session -t praxis-jupyter 2>/dev/null || true
  tmux new-session -d -s praxis-jupyter \
    "cd '${REPO_DIR}' && source .venv/bin/activate && jupyter lab --no-browser --ip='${HOST}' --port='${PORT}' | tee '${PRAXIS_ROOT}/logs/jupyter.log'"
  echo "Started JupyterLab in tmux session: praxis-jupyter"
  echo "Check token with:"
  echo "  tmux capture-pane -pt praxis-jupyter | tail -n 20"
else
  echo "tmux not found; starting JupyterLab in foreground"
  jupyter lab --no-browser --ip="${HOST}" --port="${PORT}" | tee "${PRAXIS_ROOT}/logs/jupyter.log"
fi
