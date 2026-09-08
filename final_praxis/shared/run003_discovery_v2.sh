#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
cd "$WORK/source-v2"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/003_adaptive_investigation_stopping/artifacts/discovery/qwen_20260908_v2
LOG="$WORK/logs/fp003-discovery-v2.log"
finish() {
  status=$?
  trap - EXIT
  if [ -n "${SYNC_PID:-}" ]; then kill "$SYNC_PID" 2>/dev/null || true; fi
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp003-discovery-v2.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp003-discovery-v2.zip" "s3://$BUCKET/final-praxis/20260908/003/discovery_v2.zip" --only-show-errors
  fi
  aws s3 cp "$LOG" "s3://$BUCKET/final-praxis/20260908/003/discovery_v2.log" --only-show-errors
  tail -25 "$LOG"
  echo "FINAL_PRAXIS_003_DISCOVERY_EXIT=$status"
  exit "$status"
}
trap finish EXIT
(while sleep 120; do
  aws s3 sync "$OUT" "s3://$BUCKET/final-praxis/20260908/003/discovery_v2_live/" --only-show-errors || true
done) &
SYNC_PID=$!
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/run_traces.py --base-url http://127.0.0.1:8765 --run-dir "$OUT" --pilot-verification final_praxis/003_adaptive_investigation_stopping/artifacts/pilot/qwen_20260908_v2/INDEPENDENT_VERIFICATION.json > "$LOG" 2>&1
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/evaluate_policies.py "$OUT" >> "$LOG" 2>&1
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/independent_verify.py "$OUT" >> "$LOG" 2>&1
