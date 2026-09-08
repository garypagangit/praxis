#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
aws s3 cp "s3://$BUCKET/final-praxis/20260908/code/fp003-a3db8e0ed25d.zip" "$WORK/fp003-code.zip" --only-show-errors
echo "318ed632be948e63755cfb3c8ad8499d20c1b65c3781e996aef91f5f592c0e38  $WORK/fp003-code.zip" | sha256sum -c -
python3 -m zipfile -e "$WORK/fp003-code.zip" "$WORK/source-v1"
cd "$WORK/source-v1"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/003_adaptive_investigation_stopping/artifacts/pilot/qwen_20260908
finish() {
  status=$?
  trap - EXIT
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp003-pilot-v1.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp003-pilot-v1.zip" "s3://$BUCKET/final-praxis/20260908/003/pilot_v1.zip" --only-show-errors
  fi
  echo "FINAL_PRAXIS_003_PILOT_EXIT=$status"
  exit "$status"
}
trap finish EXIT
"$PY" -c 'import numpy,scipy; print(numpy.__version__,scipy.__version__)'
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/run_traces.py --pilot --base-url http://127.0.0.1:8765 --run-dir "$OUT"
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/evaluate_policies.py "$OUT"
"$PY" final_praxis/003_adaptive_investigation_stopping/harness/independent_verify.py "$OUT"
