#!/usr/bin/env bash
set -euxo pipefail

JOB="${JOB:-halluhard-constrained-20260701}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/halluhard_constrained_20260701}"
WORKDIR="${WORKDIR:-/opt/dlami/nvme/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/dlami/nvme/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
LOG="${LOG:-${WORKDIR}/${JOB}.log}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-/opt/dlami/nvme/praxis/pip-cache}"
TMPDIR="${TMPDIR:-/opt/dlami/nvme/praxis/tmp}"
HF_HOME="${HF_HOME:-/opt/dlami/nvme/praxis/hf-cache}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}/transformers}"
PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"
PIP_PROGRESS_BAR="${PIP_PROGRESS_BAR:-off}"

export AWS_DEFAULT_REGION PIP_CACHE_DIR TMPDIR HF_HOME TRANSFORMERS_CACHE PIP_DISABLE_PIP_VERSION_CHECK PIP_PROGRESS_BAR

mkdir -p "${WORKDIR}/code" "${OUTDIR}" "$(dirname "${VENVDIR}")" "${PIP_CACHE_DIR}" "${TMPDIR}" "${HF_HOME}" "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

date -u
df -h
nvidia-smi || true

aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip
fi
if ! dpkg -s python3-venv >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi

rm -rf "${VENVDIR}"
python3 -m venv "${VENVDIR}"
source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r "${WORKDIR}/code/requirements.txt"

if [ -z "${HF_TOKEN:-}" ] && command -v aws >/dev/null 2>&1; then
  set +x
  HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id "${HF_SECRET_ID}" --query SecretString --output text)"
  export HF_TOKEN
  set -x
fi

python "${WORKDIR}/code/run_halluhard_constrained_gate.py" \
  --model-id "${MODEL_ID}" \
  --output-dir "${OUTDIR}" \
  --limit "${HALLUHARD_LIMIT:-250}" \
  --batch-size "${BATCH_SIZE:-4}" \
  --max-input-tokens "${MAX_INPUT_TOKENS:-1536}" \
  --max-new-tokens "${MAX_NEW_TOKENS:-48}"

aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/${JOB}/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
date -u
