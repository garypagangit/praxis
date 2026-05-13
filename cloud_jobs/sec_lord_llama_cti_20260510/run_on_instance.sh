#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION=us-east-1
JOB="sec-lord-llama-cti-20260510"
S3_BASE="s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/${JOB}"
WORKDIR="/opt/praxis/jobs/${JOB}"
VENVDIR="/opt/praxis/venvs/${JOB}"
LOG="/var/log/${JOB}.log"

exec > >(tee -a "${LOG}") 2>&1

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${WORKDIR}/output" "${VENVDIR}"
aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"

if ! dpkg -s python3-venv >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi

rm -rf "${VENVDIR}"
python3 -m venv "${VENVDIR}"
source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel

if ! python - <<'PY'
import torch
print(torch.__version__)
PY
then
  python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch
fi

python -m pip install -r "${WORKDIR}/code/requirements.txt"

nvidia-smi || true
export HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id praxis/huggingface/token --query SecretString --output text)"

python "${WORKDIR}/code/run_sec_lord_llama_cti_cloud.py" \
  --model-id "meta-llama/Llama-3.2-3B-Instruct" \
  --input-jsonl "${WORKDIR}/input/cti_mcq_queries.jsonl" \
  --seed-bank "${WORKDIR}/input/domain_seed_bank.json" \
  --output-dir "${WORKDIR}/output" \
  --limit 500 \
  --batch-size 8

aws s3 sync "${WORKDIR}/output/" "${S3_BASE}/output/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true
