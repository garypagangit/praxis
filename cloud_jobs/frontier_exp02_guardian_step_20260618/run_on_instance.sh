#!/usr/bin/env bash
set -euo pipefail

JOB="${JOB:-frontier-exp02-guardian-step-20260618}"
S3_BASE="${S3_BASE:-s3://praxis-garypagan-272615233626-us-east-1/experiments/frontier-exp02-self-jailbreak/cloud_jobs/frontier-exp02-guardian-step-20260618}"
JOB_ROOT="/opt/praxis/jobs/${JOB}"
CODE_DIR="${JOB_ROOT}/code"
OUTPUT_DIR="${JOB_ROOT}/output"
LOG_FILE="${JOB_ROOT}/${JOB}.log"
VENV_DIR="/opt/praxis/venvs/${JOB}"

mkdir -p "${CODE_DIR}" "${OUTPUT_DIR}" "$(dirname "${VENV_DIR}")"

{
  echo "JOB=${JOB}"
  date -u
  python3 --version
  nvidia-smi || true
  df -h
  if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
  fi
  # shellcheck source=/dev/null
  source "${VENV_DIR}/bin/activate"
  python -m pip install --upgrade pip
  python -m pip install torch --index-url https://download.pytorch.org/whl/cu121
  python -m pip install -r "${CODE_DIR}/requirements.txt"
  CONFIG_FOR_INSTANCE="${JOB_ROOT}/frontier_exp02_guardian_step_20260618.instance.json"
  python3 - "${CODE_DIR}/frontier_exp02_guardian_step_20260618.json" "${CONFIG_FOR_INSTANCE}" "${OUTPUT_DIR}" <<'PY'
import json
import sys

src, dst, output_dir = sys.argv[1:4]
with open(src, "r", encoding="utf-8") as handle:
    config = json.load(handle)
config["output_dir"] = output_dir
with open(dst, "w", encoding="utf-8") as handle:
    json.dump(config, handle, indent=2, sort_keys=True)
    handle.write("\n")
PY
  python "${CODE_DIR}/run_frontier_exp02_guardian_step_gate.py" \
    --config "${CONFIG_FOR_INSTANCE}"
  aws s3 sync "${OUTPUT_DIR}/" "${S3_BASE}/output/"
  aws s3 cp "${LOG_FILE}" "${S3_BASE}/logs/${JOB}.log" || true
  date -u
} 2>&1 | tee "${LOG_FILE}"

if [ "${STOP_INSTANCE_ON_DONE:-0}" = "1" ]; then
  TOKEN="$(curl -s -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 21600' || true)"
  INSTANCE_ID="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/meta-data/instance-id || true)"
  REGION="$(curl -s -H "X-aws-ec2-metadata-token: ${TOKEN}" http://169.254.169.254/latest/dynamic/instance-identity/document | python3 -c 'import json,sys; print(json.load(sys.stdin)["region"])' || true)"
  if [ -n "${INSTANCE_ID}" ] && [ -n "${REGION}" ]; then
    aws ec2 stop-instances --region "${REGION}" --instance-ids "${INSTANCE_ID}" || true
  fi
fi
