#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${1:-$PWD}"
cd "$REPO_DIR"

python -m pip install -r cloud_jobs/px057_adaptive_stopping_20260723/requirements.txt
python -m pytest tests/test_px057_adaptive_stopping.py tests/test_px057_trace_collection.py -q
python scripts/run_px057_trace_collection.py \
  --config configs/px057_adaptive_stopping_gate1_gpu_pilot_20260723.json

echo "PX-057 Gate 1 output:"
echo "$REPO_DIR/reports/adaptive_stopping_overthinking/gate1_gpu_pilot_20260723"
