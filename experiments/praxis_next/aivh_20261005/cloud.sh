#!/bin/bash
set -euo pipefail
base=/mnt/praxis-20260912-004
mountpoint -q "$base"
input_url="$1"; input_sha="$2"; output_url="$3"; run_name="$4"
mkdir -p "$base/$run_name"
cd "$base/$run_name"
mkdir -p outputs tmp
export TMPDIR="$PWD/tmp"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
publish() {
  rc=$?
  echo "$rc" > outputs/WORKER_EXIT.txt
  tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  aws s3 cp result.tar.gz "$output_url/result.tar.gz" --only-show-errors || true
  aws s3 cp result.sha256 "$output_url/result.sha256" --only-show-errors || true
  exit "$rc"
}
trap publish EXIT
aws s3 cp "$input_url" bundle.tar.gz --only-show-errors
echo "$input_sha  bundle.tar.gz" | sha256sum -c -
tar -xzf bundle.tar.gz
python3 -m venv venv
venv/bin/python -m pip install numpy==1.26.4 scipy==1.13.1 scikit-learn==1.5.2 joblib==1.4.2 > outputs/install.log 2>&1
venv/bin/python -m pip freeze > outputs/requirements-lock.txt
timeout --signal=TERM --kill-after=10s 900 venv/bin/python -u train_development.py > outputs/run.log 2>&1
