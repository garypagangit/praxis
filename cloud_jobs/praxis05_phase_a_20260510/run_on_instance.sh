#!/usr/bin/env bash
set -euxo pipefail

export AWS_DEFAULT_REGION=us-east-1
JOB="praxis05-phase-a-full-magic-20260510"
S3_BASE="s3://praxis-garypagan-272615233626-us-east-1/experiments/praxis05/cloud_jobs/${JOB}"
WORKDIR="/opt/praxis/jobs/${JOB}"
VENVDIR="/opt/praxis/venvs/${JOB}"
LOG="/var/log/${JOB}.log"

exec > >(tee -a "${LOG}") 2>&1

mkdir -p "${WORKDIR}/code" "${WORKDIR}/cache" "${WORKDIR}/output" "${VENVDIR}"
aws s3 sync "${S3_BASE}/code/" "${WORKDIR}/code/"
aws s3 sync "${S3_BASE}/cache/" "${WORKDIR}/cache/"

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

if ! python - <<'PY'
import torch
print(torch.__version__)
PY
then
  python -m pip install --index-url https://download.pytorch.org/whl/cu121 torch
fi

python -m pip install -r "${WORKDIR}/code/requirements-praxis05.txt"

nvidia-smi || true
export PYTHONPATH="${WORKDIR}/code/src"
export SAE_LENS_DISABLE_TRITON=1

python "${WORKDIR}/code/scripts/praxis05_04_phase_a_train_saes.py" \
  --config "${WORKDIR}/code/configs/praxis05-sae-topk-k32-x16.json" \
  --cache-dir "${WORKDIR}/cache" \
  --output-root "${WORKDIR}/output/phase_a_full_magic"

set +e
python "${WORKDIR}/code/scripts/praxis05_05_phase_a_diagnostics.py" \
  --config "${WORKDIR}/code/configs/praxis05-sae-topk-k32-x16.json" \
  --phase-a-root "${WORKDIR}/output/phase_a_full_magic" \
  --output "${WORKDIR}/output/diagnostics.json"
DIAG_EXIT=$?
set -e

cat > "${WORKDIR}/output/summary.json" <<EOF
{
  "job": "${JOB}",
  "diagnostics_exit_code": ${DIAG_EXIT},
  "s3_base": "${S3_BASE}",
  "runner": "$(hostname)",
  "completed_utc": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

aws s3 sync "${WORKDIR}/output/" "${S3_BASE}/output/"
aws s3 cp "${LOG}" "${S3_BASE}/logs/${JOB}.log" || true

exit "${DIAG_EXIT}"
