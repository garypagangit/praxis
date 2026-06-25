#!/usr/bin/env bash
set -euo pipefail

JOB="${JOB:-falsecite-code-model-gate-20260624}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/falsecite_code_20260624}"
JOB_ROOT="${JOB_ROOT:-/opt/praxis/jobs/${JOB}}"
CODE_DIR="${JOB_ROOT}/code"
INPUT_DIR="${JOB_ROOT}/input"
OUTPUT_DIR="${JOB_ROOT}/output"
LOG_FILE="${JOB_ROOT}/${JOB}.log"
VENV_DIR="${VENV_DIR:-/opt/praxis/venvs/${JOB}}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"
OUTPUT_SUFFIX="${OUTPUT_SUFFIX:-}"
S3_OUTPUT="${S3_BASE}/output"
CONFIG_BASENAME="${CONFIG_BASENAME:-falsecite_code_model_gate_20260624.json}"

if [ -n "${OUTPUT_SUFFIX}" ]; then
  OUTPUT_DIR="${OUTPUT_DIR%/}/${OUTPUT_SUFFIX}"
  S3_OUTPUT="${S3_OUTPUT%/}/${OUTPUT_SUFFIX}"
fi

export AWS_DEFAULT_REGION

mkdir -p "${CODE_DIR}" "${INPUT_DIR}" "${OUTPUT_DIR}" "$(dirname "${VENV_DIR}")"

{
  echo "JOB=${JOB}"
  date -u
  python3 --version
  nvidia-smi || true
  df -h

  aws s3 sync "${S3_BASE}/code/" "${CODE_DIR}/"
  aws s3 sync "${S3_BASE}/input/" "${INPUT_DIR}/"

  if ! dpkg -s python3-venv >/dev/null 2>&1; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
  fi

  if [ ! -x "${VENV_DIR}/bin/python" ]; then
    rm -rf "${VENV_DIR}"
    python3 -m venv "${VENV_DIR}"
  fi

  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip wheel
  python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
  python -m pip install -r "${CODE_DIR}/requirements.txt"

  if [ -z "${HF_TOKEN:-}" ]; then
    set +e
    SECRET_VALUE="$(aws secretsmanager get-secret-value --secret-id "${HF_SECRET_ID}" --query SecretString --output text 2>/dev/null)"
    SECRET_STATUS=$?
    set -e
    if [ "${SECRET_STATUS}" = "0" ] && [ -n "${SECRET_VALUE}" ]; then
      export HF_TOKEN="${SECRET_VALUE}"
    fi
  fi

  CONFIG_FOR_INSTANCE="${JOB_ROOT}/${CONFIG_BASENAME%.json}.instance.json"
  python3 - "${INPUT_DIR}/${CONFIG_BASENAME}" "${CONFIG_FOR_INSTANCE}" "${OUTPUT_DIR}" <<'PY'
import json
import os
import sys

src, dst, output_dir = sys.argv[1:4]
with open(src, "r", encoding="utf-8") as handle:
    config = json.load(handle)
config["output_dir"] = output_dir
config["locked_claims_path"] = os.path.join(os.path.dirname(src), "FALSECITE_CODE_LOCKED_CLAIMS_20260623.jsonl")
if os.environ.get("MODEL_ID"):
    config["model"]["hf_model_id"] = os.environ["MODEL_ID"]
if os.environ.get("BATCH_SIZE"):
    config["model"]["batch_size"] = int(os.environ["BATCH_SIZE"])
with open(dst, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY

  python "${CODE_DIR}/run_falsecite_code_model_gate.py" --config "${CONFIG_FOR_INSTANCE}"
  aws s3 sync "${OUTPUT_DIR}/" "${S3_OUTPUT}/"
  aws s3 cp "${LOG_FILE}" "${S3_BASE}/logs/${JOB}.log" || true
  date -u
} 2>&1 | tee "${LOG_FILE}"

if [ "${STOP_INSTANCE_ON_DONE:-0}" = "1" ]; then
  TOKEN="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 21600' || true)"
  INSTANCE_ID="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/instance-id || true)"
  REGION="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/dynamic/instance-identity/document | python3 -c 'import json,sys; print(json.load(sys.stdin)["region"])' || true)"
  if [ -n "${INSTANCE_ID}" ] && [ -n "${REGION}" ]; then
    aws ec2 stop-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}" || true
  fi
fi
