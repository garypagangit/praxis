#!/usr/bin/env bash
set -euo pipefail

JOB="${JOB:-moe-qwen15-router-smoke-20260628}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/moe_qwen15_router_smoke_20260628}"
JOB_ROOT="${JOB_ROOT:-/opt/praxis/jobs/${JOB}}"
CODE_DIR="${JOB_ROOT}/code"
OUTPUT_DIR="${JOB_ROOT}/output"
LOG_FILE="${JOB_ROOT}/${JOB}.log"
VENV_DIR="${VENV_DIR:-/opt/praxis/venvs/${JOB}}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen1.5-MoE-A2.7B}"
PROMPTS_PER_DOMAIN="${PROMPTS_PER_DOMAIN:-1}"
MAX_LENGTH="${MAX_LENGTH:-64}"
LOAD_IN_8BIT="${LOAD_IN_8BIT:-1}"

export AWS_DEFAULT_REGION
mkdir -p "${CODE_DIR}" "${OUTPUT_DIR}" "$(dirname "${VENV_DIR}")"

stop_instance_on_exit() {
  if [ "${STOP_INSTANCE_ON_DONE:-0}" != "1" ]; then
    return 0
  fi
  TOKEN="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 21600' || true)"
  INSTANCE_ID="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/instance-id || true)"
  REGION="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/dynamic/instance-identity/document | python3 -c 'import json,sys; print(json.load(sys.stdin)["region"])' || true)"
  if [ -n "${INSTANCE_ID}" ] && [ -n "${REGION}" ]; then
    aws ec2 stop-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}" || true
  fi
}
trap stop_instance_on_exit EXIT

{
  echo "JOB=${JOB}"
  date -u
  python3 --version || true
  nvidia-smi || true
  df -h

  aws s3 sync "${S3_BASE}/code/" "${CODE_DIR}/"

  if ! command -v python3 >/dev/null 2>&1; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip
  fi
  if ! python3 -c "import venv" >/dev/null 2>&1; then
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

  python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.cuda.is_available())
PY

  EXTRA_ARGS=()
  if [ "${LOAD_IN_8BIT}" = "1" ]; then
    EXTRA_ARGS+=(--load-in-8bit)
  fi

  python "${CODE_DIR}/run_qwen_moe_router_smoke.py" \
    --model-id "${MODEL_ID}" \
    --outdir "${OUTPUT_DIR}" \
    --max-length "${MAX_LENGTH}" \
    --prompts-per-domain "${PROMPTS_PER_DOMAIN}" \
    "${EXTRA_ARGS[@]}"

  aws s3 sync "${OUTPUT_DIR}/" "${S3_BASE}/output/"
  aws s3 cp "${LOG_FILE}" "${S3_BASE}/logs/${JOB}.log" || true
  date -u
} 2>&1 | tee "${LOG_FILE}"
