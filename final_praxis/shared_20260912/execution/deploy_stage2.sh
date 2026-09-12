set -eu
scratch=/mnt/praxis-20260912-004
test -d "$scratch/venv006"
mountpoint -q "$scratch"
shutdown -c || true
shutdown -h +230

runroot=$scratch/fp007-selective-20260912-1c47aca
mkdir -p "$runroot"
export RUNROOT="$runroot"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json
from pathlib import Path
root=Path(os.environ['RUNROOT']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/fp007-selective-1c47aca.zip',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='9196aa05e523c416962e5188502155f4da71578a45375dc481f147e83e6dcbec'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
for name,sha in json.loads((root/'bundle_manifest.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
PY
study=$runroot/final_praxis/007_overthinking_revision
export PRAXIS_PREREG_PATH="$study/selective_update/PREREGISTRATION.md"
export PRAXIS_PREREG_SHA256=1f7b8637b8cb8e7c248c78506a2a2d91e8c498dcda3bc7d7209326f09273d0fe
"$scratch/venv/bin/python" "$study/selective_update/run_selective.py" --out "$runroot/outputs"
systemd-run --unit=praxis007-stage2 --property=RuntimeMaxSec=10920 --property=WorkingDirectory="$runroot" --setenv=HF_HOME="$scratch/hf006" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id fp007-selective-20260912-1c47aca --prereg "$study/selective_update/PREREGISTRATION.md" --prereg-sha256 1f7b8637b8cb8e7c248c78506a2a2d91e8c498dcda3bc7d7209326f09273d0fe --seconds 10800 -- "$scratch/venv/bin/python" "$study/selective_update/run_selective.py" --out "$runroot/outputs" --execute
systemctl is-active praxis007-stage2

runroot=$scratch/fp006-containment-20260912-dd8a05a
mkdir -p "$runroot"
export RUNROOT="$runroot"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json
from pathlib import Path
root=Path(os.environ['RUNROOT']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/fp006-containment-dd8a05a.zip',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e0cf8da68efe1db810917427d1d7c51a6b0dff66f0d867b3c3c0d6775a41d19f'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
for name,sha in json.loads((root/'bundle_manifest.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
PY
study=$runroot/final_praxis/006_cognitive_expert_containment
export PRAXIS_PREREG_PATH="$study/containment/PREREGISTRATION.md"
export PRAXIS_PREREG_SHA256=2d9aa238530e50e2c33b2cefff652fe46ae8a832e3626715713c5b9c66631eea
"$scratch/venv006/bin/python" "$study/containment/run_stage2.py" --data "$study/containment/data" --arc-runner "$study/arc_qualification/run_arc.py" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs"
systemd-run --unit=praxis006-stage2 --property=RuntimeMaxSec=8220 --property=WorkingDirectory="$runroot" --setenv=HF_HOME="$scratch/hf006" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id fp006-containment-20260912-dd8a05a --prereg "$study/containment/PREREGISTRATION.md" --prereg-sha256 2d9aa238530e50e2c33b2cefff652fe46ae8a832e3626715713c5b9c66631eea --seconds 8100 -- "$scratch/venv006/bin/python" "$study/containment/run_stage2.py" --data "$study/containment/data" --arc-runner "$study/arc_qualification/run_arc.py" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs" --execute
systemctl is-active praxis006-stage2
