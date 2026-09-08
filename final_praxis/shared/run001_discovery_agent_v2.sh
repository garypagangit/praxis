#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
aws s3 cp "s3://$BUCKET/final-praxis/20260908/001/pilot_complete_v2.zip" "$WORK/fp001-pilot-complete-v2.zip" --only-show-errors
aws s3 cp "s3://$BUCKET/final-praxis/20260908/code/safe_extract.py" "$WORK/safe_extract.py" --only-show-errors
python3 "$WORK/safe_extract.py" "$WORK/fp001-pilot-complete-v2.zip" "$WORK/source-v2"
cd "$WORK/source-v2"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/001_outcome_state_verification/runs/discovery_20260908_v2
LOG="$WORK/logs/fp001-discovery-agent-v2.log"
finish() {
  status=$?
  trap - EXIT
  if [ -n "${SYNC_PID:-}" ]; then kill "$SYNC_PID" 2>/dev/null || true; fi
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp001-discovery-agent-v2.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp001-discovery-agent-v2.zip" "s3://$BUCKET/final-praxis/20260908/001/discovery_agent_v2.zip" --only-show-errors
  fi
  aws s3 cp "$LOG" "s3://$BUCKET/final-praxis/20260908/001/discovery_agent_v2.log" --only-show-errors
  tail -8 "$LOG"
  echo "FINAL_PRAXIS_001_DISCOVERY_AGENT_EXIT=$status"
  exit "$status"
}
trap finish EXIT
(while sleep 120; do
  aws s3 sync "$OUT" "s3://$BUCKET/final-praxis/20260908/001/discovery_agent_v2_live/" --only-show-errors || true
done) &
SYNC_PID=$!
"$PY" -m final_praxis.001_outcome_state_verification.harness.run_scientific --stage discovery --phase agent --run-dir "$OUT" --endpoint http://127.0.0.1:8765 > "$LOG" 2>&1
