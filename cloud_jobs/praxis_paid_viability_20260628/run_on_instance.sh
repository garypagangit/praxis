#!/usr/bin/env bash
set -euo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

JOB="${JOB:-praxis-paid-viability-20260628}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/praxis_paid_viability_20260628}"
WORKDIR="${WORKDIR:-/opt/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
LOG="${LOG:-${WORKDIR}/${JOB}.log}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"

stop_instance_on_exit() {
  if [ "${STOP_INSTANCE_ON_DONE:-1}" != "1" ]; then
    return 0
  fi
  TOKEN="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' || true)"
  if [ -n "${TOKEN}" ]; then
    INSTANCE_ID="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/instance-id || true)"
  else
    INSTANCE_ID="$(curl -s http://169.254.169.254/latest/meta-data/instance-id || true)"
  fi
  if [ -n "${INSTANCE_ID}" ]; then
    aws ec2 stop-instances --instance-ids "${INSTANCE_ID}" --region "${AWS_DEFAULT_REGION}" || true
  fi
}
trap stop_instance_on_exit EXIT

mkdir -p "${WORKDIR}/code" "${OUTDIR}" "$(dirname "${LOG}")" /opt/praxis/hf_cache
exec > >(tee -a "${LOG}") 2>&1

echo "JOB=${JOB}"
date -u
python3 --version
nvidia-smi || true
df -h || true

aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip
fi

if ! python3 -c "import venv" >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io
fi
sudo systemctl start docker || true

if [ ! -x "${VENVDIR}/bin/python" ]; then
  rm -rf "${VENVDIR}"
  python3 -m venv --system-site-packages "${VENVDIR}"
fi

source "${VENVDIR}/bin/activate"
if [ "${SKIP_PIP_INSTALL:-0}" = "1" ]; then
  python - <<'PY'
import requests
import torch
import transformers

print("SKIP_PIP_INSTALL=1")
print("torch", torch.__version__)
print("transformers", transformers.__version__)
PY
else
  export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/opt/dlami/nvme/praxis/pip_cache}"
  mkdir -p "${PIP_CACHE_DIR}"
  python -m pip install --upgrade pip wheel
  python -m pip install -r "${WORKDIR}/code/requirements.txt"
fi

export HF_HOME="${HF_HOME:-/opt/praxis/hf_cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/opt/praxis/hf_cache}"

if [ -z "${HF_TOKEN:-}" ] && command -v aws >/dev/null 2>&1; then
  set +e
  SECRET_VALUE="$(aws secretsmanager get-secret-value --secret-id "${HF_SECRET_ID}" --query SecretString --output text 2>/dev/null)"
  SECRET_STATUS=$?
  set -e
  if [ "${SECRET_STATUS}" = "0" ] && [ -n "${SECRET_VALUE}" ]; then
    export HF_TOKEN="${SECRET_VALUE}"
  fi
fi

python "${WORKDIR}/code/run_paid_viability_gates.py" --output-dir "${OUTDIR}"

sed -E 's/hf_[A-Za-z0-9]+/hf_REDACTED/g' "${LOG}" > "${OUTDIR}/${JOB}.log"
aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/" \
  --exclude "swe_eval_work/base/*" \
  --exclude "swe_eval_work/eval_base/*" \
  --exclude "swe_eval_work/eval_model/*" \
  --exclude "swe_eval_work/eval_gold/*"
aws s3 cp "${OUTDIR}/${JOB}.log" "${S3_BASE}/logs/${JOB}.log" || true
date -u
