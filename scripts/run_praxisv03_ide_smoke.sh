#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_PATH="${CONFIG_PATH:-${REPO_DIR}/configs/praxisv03-unraveled-ide-smoke.json}"

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
CACHE_DIR="${RUN_DIR}/.runtime-cache"
MPL_CONFIG_DIR="${CACHE_DIR}/matplotlib"
TORCH_HOME="${CACHE_DIR}/torch"

mkdir -p "${RUN_DIR}" "${MPL_CONFIG_DIR}" "${TORCH_HOME}"

export MPLCONFIGDIR="${MPL_CONFIG_DIR}"
export TORCH_HOME="${TORCH_HOME}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUTF8=1

python -m praxis.train --config "${CONFIG_PATH}" 2>&1 | tee "${LOG_PATH}"

echo
echo "Console log: ${LOG_PATH}"
