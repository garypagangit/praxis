#!/usr/bin/env bash
set -euo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"

JOB="${JOB:-swe-evo-true-eval-sweep-20260629}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/cloud_jobs/swe_evo_true_eval_sweep_20260629}"
WORKDIR="${WORKDIR:-/opt/dlami/nvme/praxis/jobs/${JOB}}"
OUTDIR="${OUTDIR:-${WORKDIR}/output}"
LOG="${LOG:-${WORKDIR}/${JOB}.log}"
DOCKER_DATA_ROOT="${DOCKER_DATA_ROOT:-/opt/dlami/nvme/docker}"

mkdir -p "${WORKDIR}/code" "${OUTDIR}" "$(dirname "${LOG}")"
exec > >(tee -a "${LOG}") 2>&1

echo "JOB=${JOB}"
date -u
python3 --version
df -h / /opt/dlami/nvme || true

aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"

if ! command -v python3 >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3
fi

if ! command -v git >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git
fi

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io
fi

sudo mkdir -p "${DOCKER_DATA_ROOT}" /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<JSON
{
  "data-root": "${DOCKER_DATA_ROOT}"
}
JSON
sudo systemctl restart docker || sudo service docker restart
sudo docker info | grep -E "Docker Root Dir|Storage Driver" || true
df -h / /opt/dlami/nvme || true

python3 "${WORKDIR}/code/run_swe_evo_true_eval_sweep.py" --output-dir "${OUTDIR}"

sed -E 's/hf_[A-Za-z0-9]+/hf_REDACTED/g' "${LOG}" > "${OUTDIR}/${JOB}.log"
aws s3 sync "${OUTDIR}/" "${S3_BASE}/output/"
aws s3 cp "${OUTDIR}/${JOB}.log" "${S3_BASE}/logs/${JOB}.log" || true
date -u
