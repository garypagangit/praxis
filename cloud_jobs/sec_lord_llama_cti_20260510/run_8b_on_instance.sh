#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION=us-east-1
JOB="sec-lord-llama-cti-20260510"
RUN="sec-lord-llama-cti-20260510-8b"
S3_BASE="s3://praxis-garypagan-272615233626-us-east-1/experiments/sec-lord-ds-lord/cloud_jobs/${JOB}"
WORKDIR="/opt/praxis/jobs/${JOB}"
VENVDIR="/opt/praxis/venvs/${JOB}"
OUTDIR="${WORKDIR}/output-8b"
LOG="/var/log/${RUN}.log"

exec > >(tee -a "${LOG}") 2>&1

mkdir -p "${WORKDIR}/code" "${WORKDIR}/input" "${OUTDIR}"
aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/input/" "${WORKDIR}/input/"

if ! dpkg -s python3-venv >/dev/null 2>&1; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv
fi

if [ ! -x "${VENVDIR}/bin/python" ]; then
  rm -rf "${VENVDIR}"
  python3 -m venv "${VENVDIR}"
fi

source "${VENVDIR}/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -r "${WORKDIR}/code/requirements.txt"

nvidia-smi || true
export HF_TOKEN="$(aws secretsmanager get-secret-value --secret-id praxis/huggingface/token --query SecretString --output text)"

python "${WORKDIR}/code/run_sec_lord_llama_cti_cloud.py" \
  --model-id "meta-llama/Llama-3.1-8B-Instruct" \
  --input-jsonl "${WORKDIR}/input/cti_mcq_queries.jsonl" \
  --seed-bank "${WORKDIR}/input/domain_seed_bank.json" \
  --output-dir "${OUTDIR}" \
  --limit 500 \
  --batch-size 2

aws s3 sync "${OUTDIR}/" "${S3_BASE}/output-8b/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${RUN}.log" || true
