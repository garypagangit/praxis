#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
aws s3 cp "s3://$BUCKET/final-praxis/20260908/code/fp001-e060bb29c7e3.zip" "$WORK/fp001-code-v2.zip" --only-show-errors
echo "3520d37ce893406b66da830b2b060d701c7547cd9d1ea27c383ef0b618295f23  $WORK/fp001-code-v2.zip" | sha256sum -c -
python3 -m zipfile -e "$WORK/fp001-code-v2.zip" "$WORK/source-v2"
cd "$WORK/source-v2"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/001_outcome_state_verification/runs/pilot_20260908_v2
finish() {
  status=$?
  trap - EXIT
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp001-pilot-agent-v2.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp001-pilot-agent-v2.zip" "s3://$BUCKET/final-praxis/20260908/001/pilot_agent_v2.zip" --only-show-errors
  fi
  echo "FINAL_PRAXIS_001_PILOT_AGENT_EXIT=$status"
  exit "$status"
}
trap finish EXIT
"$PY" -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage pilot --phase agent --run-dir "$OUT" --endpoint http://127.0.0.1:8765
