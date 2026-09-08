#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
aws s3 cp "s3://$BUCKET/final-praxis/20260908/code/fp001-ff19b1d1890e.zip" "$WORK/fp001-code.zip" --only-show-errors
echo "ebf56b28e3b4f19fab5c78d94b72526e1e5009298766b3c9ce33d5a2e113be4b  $WORK/fp001-code.zip" | sha256sum -c -
python3 -m zipfile -e "$WORK/fp001-code.zip" "$WORK/source-v1"
cd "$WORK/source-v1"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/001_outcome_state_verification/runs/pilot_20260908
finish() {
  status=$?
  trap - EXIT
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp001-pilot-agent-v1.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp001-pilot-agent-v1.zip" "s3://$BUCKET/final-praxis/20260908/001/pilot_agent_v1.zip" --only-show-errors
  fi
  echo "FINAL_PRAXIS_001_PILOT_AGENT_EXIT=$status"
  exit "$status"
}
trap finish EXIT
"$PY" -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage pilot --phase agent --run-dir "$OUT" --endpoint http://127.0.0.1:8765
