#!/bin/bash
set -euo pipefail
input_url="$1"
input_sha="$2"
output_url="$3"
run_name="$4"
base=/opt/dlami/nvme
test -d "$base"
mkdir -p "$base/$run_name"
cd "$base/$run_name"
mkdir -p outputs
publish() {
  rc=$?
  echo "$rc" > outputs/WORKER_EXIT.txt
  if test -x venv/bin/python; then venv/bin/python -m pip freeze > outputs/packages.txt 2>/dev/null || true; fi
  tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  aws s3 cp result.tar.gz "$output_url/result.tar.gz" --only-show-errors
  aws s3 cp result.sha256 "$output_url/result.sha256" --only-show-errors
  exit "$rc"
}
trap publish EXIT
nvidia-smi > outputs/gpu.txt
df -h > outputs/disk.txt
aws s3 cp "$input_url" bundle.tar.gz --only-show-errors
echo "$input_sha  bundle.tar.gz" | sha256sum -c -
tar -xzf bundle.tar.gz
export HF_HOME="$base/praxis_vlm_hf_cache"
export HF_HUB_DISABLE_XET=1
export OMP_NUM_THREADS=2
python_bin=''
for candidate in /opt/pytorch/bin/python /opt/praxis/venvs/sec-lord-relationship-evidence-defense-qwen25-7b-20260630/bin/python /usr/bin/python3; do
  if test -x "$candidate" && "$candidate" -c 'import torch; assert torch.cuda.is_available()' > outputs/torch_check.txt 2>&1; then python_bin="$candidate"; break; fi
done
test -n "$python_bin"
"$python_bin" -c 'import shutil; assert shutil.disk_usage(".").free > 20000000000'
"$python_bin" -m venv --system-site-packages venv
timeout 180 venv/bin/python -m pip install 'transformers==4.51.3' 'accelerate==1.6.0' 'pillow==11.2.1' > outputs/install.log 2>&1
timeout --signal=TERM --kill-after=10s 1050 venv/bin/python infer.py --inputs inputs --out outputs --seconds 900 > outputs/inference.log 2>&1
