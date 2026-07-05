#!/usr/bin/env bash
set -euxo pipefail

JOB="${JOB:-cti-full-bucket-downstream-qwen25-7b-20260705}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/cti_full_bucket_downstream_20260705}"
INPUT_JSONL="${INPUT_JSONL:-full_bucket_prompts.jsonl}"
CONDITIONS="${CONDITIONS:-vanilla,relationship_evidence}"
BATCH_SIZE="${BATCH_SIZE:-2}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-8}"
MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-4096}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"

WORKDIR="${WORKDIR:-/opt/dlami/nvme/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/dlami/nvme/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
LOG="${LOG:-${WORKDIR}/${JOB}.log}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-/opt/dlami/nvme/praxis/pip-cache}"
TMPDIR="${TMPDIR:-/opt/dlami/nvme/praxis/tmp}"
HF_HOME="${HF_HOME:-/opt/dlami/nvme/praxis/hf-cache}"
TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-${HF_HOME}/transformers}"
PIP_DISABLE_PIP_VERSION_CHECK="${PIP_DISABLE_PIP_VERSION_CHECK:-1}"
PIP_PROGRESS_BAR="${PIP_PROGRESS_BAR:-off}"

export AWS_DEFAULT_REGION PIP_CACHE_DIR TMPDIR HF_HOME TRANSFORMERS_CACHE
export PIP_DISABLE_PIP_VERSION_CHECK PIP_PROGRESS_BAR

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${OUTDIR}" "$(dirname "${VENVDIR}")"
mkdir -p "${PIP_CACHE_DIR}" "${TMPDIR}" "${HF_HOME}" "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

date -u
df -h
nvidia-smi || true

aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"

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

python "${WORKDIR}/code/run_sec_lord_relationship_evidence_cloud.py" \
  --model-id "${MODEL_ID}" \
  --input-jsonl "${WORKDIR}/input/${INPUT_JSONL}" \
  --output-dir "${OUTDIR}" \
  --batch-size "${BATCH_SIZE}" \
  --max-new-tokens "${MAX_NEW_TOKENS}" \
  --max-input-tokens "${MAX_INPUT_TOKENS}" \
  --conditions "${CONDITIONS}"

aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/${JOB}/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
date -u

