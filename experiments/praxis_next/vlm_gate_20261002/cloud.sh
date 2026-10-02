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
mkdir -p tmp pip-cache
export TMPDIR="$PWD/tmp"
export PIP_CACHE_DIR="$PWD/pip-cache"
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
# A venv created from another venv does not inherit that parent's packages.
# Add its package directories after our own pinned overlay; never replace CUDA.
site_dir=$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
"$python_bin" -c 'import sys; print("\n".join(p for p in sys.path if p.endswith(("site-packages","dist-packages"))))' > "$site_dir/borrowed_gpu_environment.pth"
timeout 180 venv/bin/python -m pip install --no-cache-dir --no-deps 'transformers==4.51.3' 'accelerate==1.6.0' 'pillow==11.2.1' 'tokenizers==0.21.4' 'huggingface-hub==0.30.2' > outputs/install.log 2>&1
venv/bin/python -c 'import torch; from transformers import Qwen2_5_VLForConditionalGeneration; print(torch.__version__,torch.cuda.is_available(),torch.__file__)' > outputs/import_check.txt 2>&1
timeout --signal=TERM --kill-after=10s 1050 venv/bin/python -u infer.py --inputs inputs --out outputs --seconds 900 > outputs/inference.log 2>&1 &
worker_pid=$!
while kill -0 "$worker_pid" 2>/dev/null; do
  tail -c 3000 outputs/inference.log > outputs/progress.txt
  timeout 10 aws s3 cp outputs/progress.txt "$output_url/progress.txt" --only-show-errors || true
  sleep 20
done
wait "$worker_pid"
