#!/usr/bin/env bash
set -euo pipefail
bundle_uri="$1"
bundle_sha="$2"
output_uri="$3"
run_id="$4"
[[ "$run_id" =~ ^praxis-px107-[a-f0-9]{16}$ ]]
base=/opt/dlami/nvme
test -d "$base"
run_dir="$base/px107-runs/$run_id"
test ! -e "$run_dir"
mkdir -p "$run_dir/outputs"
cd "$run_dir"
export AWS_DEFAULT_REGION=us-east-1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=1
publish() {
  rc=$?
  trap - EXIT TERM INT
  cd "$run_dir"
  printf '%s\n' "$rc" > outputs/WORKER_EXIT.txt
  timeout 40 tar -czf result.tar.gz outputs
  sha256sum result.tar.gz | cut -d ' ' -f1 > result.sha256
  timeout 90 aws s3 cp result.tar.gz "${output_uri}/result.tar.gz" --only-show-errors || rc=91
  timeout 20 aws s3 cp result.sha256 "${output_uri}/result.sha256" --only-show-errors || rc=92
  exit "$rc"
}
trap publish EXIT
trap 'exit 124' TERM INT
timeout 90 aws s3 cp "$bundle_uri" bundle.tar.gz --only-show-errors
printf '%s  bundle.tar.gz\n' "$bundle_sha" | sha256sum -c -
python3 - <<'PY'
import tarfile,pathlib,hashlib,json
root=pathlib.Path.cwd().resolve()
with tarfile.open('bundle.tar.gz') as a:
    members=a.getmembers()
    assert len(members)<60 and sum(m.size for m in members)<300000000
    for m in members:
        assert m.isfile() and not m.name.startswith('/') and '..' not in pathlib.PurePosixPath(m.name).parts and '\\' not in m.name
        assert (root/m.name).resolve().is_relative_to(root)
    a.extractall(root)
manifest=json.loads(pathlib.Path('CONTENTS.json').read_text())
assert set(manifest)=={m.name for m in members}-{'CONTENTS.json'}
for name,h in manifest.items():assert hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()==h,name
pathlib.Path('outputs/VERIFIED_CONTENTS.json').write_text(json.dumps(manifest,indent=2))
PY
python_bin=''
for candidate in /opt/pytorch/bin/python /usr/bin/python3; do
  if test -x "$candidate" && "$candidate" -c 'import numpy,lightgbm,sklearn' > outputs/ENV.log 2>&1; then python_bin="$candidate"; break; fi
done
if test -z "$python_bin"; then
  python3 -m venv venv
  timeout 180 venv/bin/pip install numpy==2.2.6 lightgbm==4.6.0 scikit-learn==1.7.2 > outputs/INSTALL.log 2>&1
  python_bin="$run_dir/venv/bin/python"
fi
timeout --signal=TERM --kill-after=10s 1050 "$python_bin" -u run_pilot.py --data input --out outputs/results > outputs/worker.log 2>&1
