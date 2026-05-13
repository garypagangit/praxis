#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION=us-east-1
JOB="ai-supply-chain-lora-20260510"
S3_BASE="s3://praxis-garypagan-272615233626-us-east-1/experiments/ai-supply-chain/cloud_jobs/${JOB}"
WORKDIR="/opt/praxis/jobs/${JOB}"
VENVDIR="/opt/praxis/venvs/sec-lord-llama-cti-20260510"
LOG="/var/log/${JOB}.log"

exec > >(tee -a "${LOG}") 2>&1

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${WORKDIR}/output"
aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"

source "${VENVDIR}/bin/activate"
python -m pip install -r "${WORKDIR}/code/requirements.txt"

python - <<'PY'
import json
from pathlib import Path

workdir = Path("/opt/praxis/jobs/ai-supply-chain-lora-20260510")
spec = json.loads((workdir / "input" / "lora_training_spec.json").read_text())
spec["train_files"] = {
    "clean": str(workdir / "input" / "clean_train.jsonl"),
    "poison": str(workdir / "input" / "poison_train.jsonl"),
}
spec["validation_files"] = {
    "clean": str(workdir / "input" / "clean_val.jsonl"),
    "poison": str(workdir / "input" / "poison_val.jsonl"),
}
(workdir / "input" / "lora_training_spec_cloud.json").write_text(json.dumps(spec, indent=2))
PY

nvidia-smi || true
export HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id praxis/huggingface/token --query SecretString --output text)"

python "${WORKDIR}/code/run_lora_provenance_cloud.py" \
  --spec "${WORKDIR}/input/lora_training_spec_cloud.json" \
  --output-dir "${WORKDIR}/output" \
  --model-id "meta-llama/Llama-3.2-3B-Instruct" \
  --max-steps 150 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --max-length 512 \
  --validation-every 10 \
  --val-batches 8 \
  --val-rows 64

aws s3 sync "${WORKDIR}/output/" "${S3_BASE}/output/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
