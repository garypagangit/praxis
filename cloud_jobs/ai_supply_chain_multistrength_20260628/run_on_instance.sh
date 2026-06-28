#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION=us-east-1
JOB="ai-supply-chain-multistrength-20260628"
S3_BASE="s3://praxis-garypagan-272615233626-us-east-1/experiments/ai-supply-chain/cloud_jobs/${JOB}"
WORKDIR="/opt/praxis/jobs/${JOB}"
VENVDIR="/opt/praxis/venvs/${JOB}"
LOG="/var/log/${JOB}.log"

exec > >(tee -a "${LOG}") 2>&1

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${WORKDIR}/output"
aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"

if [[ ! -f "${VENVDIR}/bin/activate" ]]; then
  python3 -m venv "${VENVDIR}"
fi
source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r "${WORKDIR}/code/requirements.txt"

python - <<'PY'
import json
from pathlib import Path

workdir = Path("/opt/praxis/jobs/ai-supply-chain-multistrength-20260628")
spec_path = workdir / "input" / "multistrength_lora_gate_spec.json"
spec = json.loads(spec_path.read_text(encoding="utf-8"))

def map_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if len(parts) >= 2 and parts[-2].startswith("seed_"):
        return str(workdir / "input" / parts[-2] / parts[-1])
    return str(workdir / "input" / parts[-1])

for run in spec["paired_runs"]:
    for condition in ["clean", "poison"]:
        run["conditions"][condition]["train_file"] = map_path(run["conditions"][condition]["train_file"])
        run["conditions"][condition]["validation_file"] = map_path(run["conditions"][condition]["validation_file"])
    run["conditions"]["poison"]["trigger_eval_file"] = map_path(
        run["conditions"]["poison"]["trigger_eval_file"]
    )

cloud_spec_path = workdir / "input" / "multistrength_lora_gate_spec_cloud.json"
cloud_spec_path.write_text(json.dumps(spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

nvidia-smi || true
set +x
export HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id praxis/huggingface/token --query SecretString --output text)"
set -x

python "${WORKDIR}/code/run_multistrength_lora_cloud.py" \
  --spec "${WORKDIR}/input/multistrength_lora_gate_spec_cloud.json" \
  --output-dir "${WORKDIR}/output" \
  --model-id "meta-llama/Llama-3.2-3B-Instruct" \
  --max-steps 150 \
  --batch-size 1 \
  --gradient-accumulation-steps 8 \
  --max-length 512 \
  --validation-every 10 \
  --val-batches 8 \
  --val-rows 64 \
  --trigger-eval-rows 16

aws s3 sync "${WORKDIR}/output/" "${S3_BASE}/output/"
sed -E 's/hf_[A-Za-z0-9]+/hf_REDACTED/g' "${LOG}" > "${WORKDIR}/output/${JOB}.log"
aws s3 cp "${WORKDIR}/output/${JOB}.log" "${S3_BASE}/logs/${JOB}.log" || true
