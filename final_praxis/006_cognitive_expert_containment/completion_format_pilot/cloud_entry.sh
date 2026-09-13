#!/bin/bash
set -uo pipefail
runroot="$1"
preregsha="$2"
scratch=/mnt/praxis-20260912-005
case "$runroot" in "$scratch"/fp006-format-*) ;; *) exit 70;; esac
study="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
"$scratch/venv/bin/python" "$runroot/code/final_praxis/shared_20260912/supervisor.py" \
  --root "$runroot" --run-id "$(basename "$runroot")" --prereg "$study/PREREGISTRATION.md" \
  --prereg-sha256 "$preregsha" --seconds 6300 -- /bin/bash "$study/bootstrap.sh" "$runroot"
code=$?
# The supervisor has completed its final S3 sync before requesting an early stop.
sync
/sbin/shutdown -h +1
exit "$code"
