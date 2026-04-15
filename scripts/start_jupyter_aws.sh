#!/usr/bin/env bash
set -euo pipefail

PRAXIS_ROOT="${PRAXIS_ROOT:-/mnt/praxis}"
REPO_DIR="${REPO_DIR:-${PRAXIS_ROOT}/repo}"
PORT="${PORT:-8888}"
HOST="${HOST:-127.0.0.1}"

cd "${REPO_DIR}"
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
