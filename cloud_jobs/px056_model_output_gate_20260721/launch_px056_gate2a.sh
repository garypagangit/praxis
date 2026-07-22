#!/usr/bin/env bash
set -euo pipefail

cd /opt/ml/code
python -m pip install --no-cache-dir --upgrade pip
python -m pip install --no-cache-dir -r requirements.txt

python run_px056_gate2_model_output.py \
  --generations-per-prompt "${PX056_GENERATIONS_PER_PROMPT:-3}" \
  --max-input-tokens "${PX056_MAX_INPUT_TOKENS:-1400}" \
  --max-new-tokens "${PX056_MAX_NEW_TOKENS:-384}" \
  --mode "${PX056_MODE:-pilot}" \
  --outdir /opt/ml/output/data/px056_gate2_model_output \
  --s3-uri "${PX056_S3_URI:?PX056_S3_URI missing}"
