#!/usr/bin/env bash
set -euxo pipefail

JOB="${JOB:-px054-refusal-geometry-huginn-20260705}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/px054_refusal_geometry_20260705}"
DEPTHS="${DEPTHS:-4,8,16,32}"
MAX_INPUT_TOKENS="${MAX_INPUT_TOKENS:-96}"
MAX_DIMS="${MAX_DIMS:-512}"
DTYPE="${DTYPE:-auto}"

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

mkdir -p "${WORKDIR}/code" "${OUTDIR}" "$(dirname "${VENVDIR}")"
mkdir -p "${PIP_CACHE_DIR}" "${TMPDIR}" "${HF_HOME}" "$(dirname "${LOG}")"
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

python "${WORKDIR}/code/run_px054_refusal_geometry_activation_gate.py" \
  --output-dir "${OUTDIR}" \
  --depths "${DEPTHS}" \
  --max-input-tokens "${MAX_INPUT_TOKENS}" \
  --max-dims "${MAX_DIMS}" \
  --dtype "${DTYPE}"

aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/${JOB}/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
date -u
