#!/usr/bin/env bash
set -euxo pipefail

JOB="${JOB:-sec-lord-relationship-evidence-defense-qwen25-7b-20260630}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-7B-Instruct}"
BATCH_SIZE="${BATCH_SIZE:-2}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-8}"
MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-4096}"
INPUT_JSONL="${INPUT_JSONL:-evidence_addressable_prompts.jsonl}"
CONDITIONS="${CONDITIONS:-all}"
OUTPUT_SUFFIX="${OUTPUT_SUFFIX:-qwen25-7b-all-20260630}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/sec_lord_relationship_evidence_defense_20260630}"
WORKDIR="${WORKDIR:-/opt/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
S3_OUTPUT="${S3_BASE}/output"
if [ -n "${OUTPUT_SUFFIX}" ]; then
  OUTDIR="${OUTDIR%/}/${OUTPUT_SUFFIX}"
  S3_OUTPUT="${S3_OUTPUT%/}/${OUTPUT_SUFFIX}"
fi
LOG="${LOG:-${WORKDIR}/${JOB}.log}"

export AWS_DEFAULT_REGION

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${OUTDIR}" "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

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
python -m pip install -r "${WORKDIR}/code/requirements_defense_qwen.txt"

nvidia-smi || true
df -h

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

aws s3 sync "${OUTDIR}/" "${S3_OUTPUT}/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
