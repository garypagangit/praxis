#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-${REPO_DIR}/configs/synthetic-smoke.json}"

cd "${REPO_DIR}"
source .venv/bin/activate

RUN_NAME="$(python - <<PY
import json
from pathlib import Path
config = json.loads(Path(r"${CONFIG_PATH}").read_text(encoding="utf-8"))
print(config["run_name"])
PY
)"

RUN_DIR="${REPO_DIR}/runs/${RUN_NAME}"
LOG_PATH="${RUN_DIR}/console.log"
mkdir -p "${RUN_DIR}"

python -m praxis.train --config "${CONFIG_PATH}" 2>&1 | tee "${LOG_PATH}"

echo
echo "Console log: ${LOG_PATH}"
