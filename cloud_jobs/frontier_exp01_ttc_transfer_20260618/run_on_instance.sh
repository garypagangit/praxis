#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

JOB="${JOB:-frontier-exp01-ttc-transfer-20260618}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp01-ttc-transfer/cloud_jobs/${JOB}}"
WORKDIR="${WORKDIR:-/opt/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
LOG="${LOG:-${WORKDIR}/${JOB}.log}"
CONFIG_PATH="${CONFIG_PATH:-${WORKDIR}/code/frontier_exp01_ttc_full_20260618.json}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"

mkdir -p "${WORKDIR}/code" "${OUTDIR}" "$(dirname "${LOG}")" /opt/praxis/hf_cache
exec > >(tee -a "${LOG}") 2>&1

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required on the instance." >&2
  exit 2
fi

aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip
fi

if ! python3 -c "import venv" >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi

if [ ! -x "${VENVDIR}/bin/python" ]; then
  rm -rf "${VENVDIR}"
  python3 -m venv --system-site-packages "${VENVDIR}"
fi

source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -r "${WORKDIR}/code/requirements.txt"

export HF_HOME="${HF_HOME:-/opt/praxis/hf_cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-/opt/praxis/hf_cache}"

if [ -z "${HF_TOKEN:-}" ] && command -v aws >/dev/null 2>&1; then
  set +x
  HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id "${HF_SECRET_ID}" --query SecretString --output text || true)"
  export HF_TOKEN
  set -x
fi

nvidia-smi || true
df -h || true

python "${WORKDIR}/code/run_frontier_exp01_ttc_cloud.py" \
  --config "${CONFIG_PATH}" \
  --output-dir "${OUTDIR}" \
  --run-label "${JOB}"

aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true

if [ "${STOP_INSTANCE_ON_DONE:-1}" = "1" ]; then
  TOKEN="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' || true)"
  if [ -n "${TOKEN}" ]; then
    INSTANCE_ID="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/instance-id || true)"
  else
    INSTANCE_ID="$(curl -s http://169.254.169.254/latest/meta-data/instance-id || true)"
  fi
  if [ -n "${INSTANCE_ID}" ]; then
    aws ec2 stop-instances --instance-ids "${INSTANCE_ID}" --region "${AWS_DEFAULT_REGION}" || true
  fi
fi
