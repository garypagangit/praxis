#!/usr/bin/env bash
set -euo pipefail
umask 077
WORK=/opt/dlami/nvme/praxis-final/20260908
PY=/opt/praxis/venvs/frontier-exp02-guardian-step-20260618/bin/python
BUCKET=praxis-garypagan-272615233626-us-east-1
aws s3 cp "s3://$BUCKET/final-praxis/20260908/code/fp002-94c2830575e9.zip" "$WORK/fp002-code.zip" --only-show-errors
echo "5a7e70926543ada230b0a1d158cd24f5667f4e4ce6d738c0c01e85871583a26f  $WORK/fp002-code.zip" | sha256sum -c -
python3 -m zipfile -e "$WORK/fp002-code.zip" "$WORK/source-v1"
cd "$WORK/source-v1"
export PYTHONPATH="$PWD"
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
OUT=final_praxis/002_cascade_containment/runs/pilot-v1
finish() {
  status=$?
  trap - EXIT
  if [ -d "$OUT" ]; then
    python3 - "$OUT" "$WORK/fp002-pilot-v1.zip" <<'PY'
import sys,zipfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[2],'w',zipfile.ZIP_DEFLATED) as z:
 for p in Path(sys.argv[1]).rglob('*'):
  if p.is_file(): z.write(p,p.as_posix())
PY
    aws s3 cp "$WORK/fp002-pilot-v1.zip" "s3://$BUCKET/final-praxis/20260908/002/pilot_v1.zip" --only-show-errors
  fi
  echo "FINAL_PRAXIS_002_PILOT_EXIT=$status"
  exit "$status"
}
trap finish EXIT
"$PY" -m final_praxis.002_cascade_containment.harness.run_workflow --mode pilot --output "$OUT" --base-url http://127.0.0.1:8765
"$PY" -m final_praxis.002_cascade_containment.harness.independent_verify "$OUT"
