set -eu
scratch=/mnt/praxis-20260912-004
runroot=$scratch/fp006-empathy-20260912-5c33bc4
mkdir -p "$runroot"
export RUNROOT="$runroot"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json
from pathlib import Path
root=Path(os.environ['RUNROOT']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/fp006-empathy-5c33bc4.zip',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='f462d06b62dcff96175157ab73e138f56fc6a5ede36877ed25b38215684d8eac'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
for name,sha in json.loads((root/'bundle_manifest.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
PY
study=$runroot/final_praxis/006_cognitive_expert_containment
systemd-run --unit=praxis006-empathy --property=RuntimeMaxSec=1920 --property=WorkingDirectory="$runroot" --setenv=HF_HOME="$scratch/hf006" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id fp006-empathy-20260912-5c33bc4 --prereg "$study/empathy_qualification/PREREGISTRATION.md" --prereg-sha256 09a057ed7460908a00393bdad7fac4e371e0ed359bb83013bef69979c7f4b1b1 --seconds 1800 -- "$scratch/venv006/bin/python" "$study/empathy_qualification/run_empathy.py" --data "$study/empathy_qualification/data" --arc-runner "$study/arc_qualification/run_arc.py" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs" --execute
systemctl is-active praxis006-empathy
