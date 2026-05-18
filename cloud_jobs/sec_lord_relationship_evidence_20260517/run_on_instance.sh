#!/usr/bin/env bash
set -euxo pipefail

JOB="sec-lord-relationship-evidence-20260517"
MODEL_ID="${MODEL_ID:-meta-llama/Llama-3.1-8B-Instruct}"
BATCH_SIZE="${BATCH_SIZE:-2}"
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-8}"
MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-4096}"
INPUT_JSONL="${INPUT_JSONL:-evidence_addressable_prompts.jsonl}"
CONDITIONS="${CONDITIONS:-all}"
OUTPUT_SUFFIX="${OUTPUT_SUFFIX:-}"
HF_SECRET_ID="${HF_SECRET_ID:-praxis/huggingface/token}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/${JOB}}"
REPO_DIR="${REPO_DIR:-$(pwd)}"
WORKDIR="${WORKDIR:-/opt/praxis/jobs/${JOB}}"
VENVDIR="${VENVDIR:-/opt/praxis/venvs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
if [ -n "${OUTPUT_SUFFIX}" ]; then
  OUTDIR="${OUTDIR%/}/${OUTPUT_SUFFIX}"
fi
LOG="${LOG:-${WORKDIR}/${JOB}.log}"

export AWS_DEFAULT_REGION

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${OUTDIR}" "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

if [ -f "${REPO_DIR}/cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py" ]; then
  cp "${REPO_DIR}/cloud_jobs/sec_lord_relationship_evidence_20260517/run_sec_lord_relationship_evidence_cloud.py" "${WORKDIR}/code/"
  cp "${REPO_DIR}/cloud_jobs/sec_lord_relationship_evidence_20260517/requirements.txt" "${WORKDIR}/code/"
  cp "${REPO_DIR}/cloud_jobs/sec_lord_relationship_evidence_20260517/input/evidence_addressable_prompts.jsonl" "${WORKDIR}/input/"
elif command -v aws >/dev/null 2>&1; then
  aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
  aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"
else
  echo "No repo checkout or aws CLI input source found." >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 2
fi

if ! dpkg -s python3-venv >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
  else
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
  fi
fi

if [ ! -x "${VENVDIR}/bin/python" ]; then
  rm -rf "${VENVDIR}"
  python3 -m venv "${VENVDIR}"
fi

source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -r "${WORKDIR}/code/requirements.txt"

nvidia-smi || true

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

if command -v aws >/dev/null 2>&1; then
  aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/"
  aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
fi
