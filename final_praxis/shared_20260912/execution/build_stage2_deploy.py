from pathlib import Path
import hashlib
root=Path(__file__).resolve().parent
runs=[('007','fp007-selective-20260912-1c47aca','fp007-selective-1c47aca.zip','9196aa05e523c416962e5188502155f4da71578a45375dc481f147e83e6dcbec','C:/w/fp007','007_overthinking_revision','selective_update',10800),
      ('006','fp006-containment-20260912-dd8a05a','fp006-containment-dd8a05a.zip','e0cf8da68efe1db810917427d1d7c51a6b0dff66f0d867b3c3c0d6775a41d19f','C:/w/fp006','006_cognitive_expert_containment','containment',8100)]
header='''set -eu
scratch=/mnt/praxis-20260912-004
test -d "$scratch/venv006"
mountpoint -q "$scratch"
shutdown -c || true
shutdown -h +230
'''
parts=[header]
for option,run,archive,digest,repo,study,sub,seconds in runs:
    prereg=Path(repo)/'final_praxis'/study/sub/'PREREGISTRATION.md'
    preregsha=hashlib.sha256(prereg.read_bytes()).hexdigest()
    setup=f'''runroot=$scratch/{run}
mkdir -p "$runroot"
export RUNROOT="$runroot"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json
from pathlib import Path
root=Path(os.environ['RUNROOT']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/{archive}',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='{digest}'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
for name,sha in json.loads((root/'bundle_manifest.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
PY
study=$runroot/final_praxis/{study}
export PRAXIS_PREREG_PATH="$study/{sub}/PREREGISTRATION.md"
export PRAXIS_PREREG_SHA256={preregsha}
'''
    if option=='007':
        command='"$scratch/venv/bin/python" "$study/selective_update/run_selective.py" --out "$runroot/outputs"'
    else:
        command='"$scratch/venv006/bin/python" "$study/containment/run_stage2.py" --data "$study/containment/data" --arc-runner "$study/arc_qualification/run_arc.py" --qualification "$study/qualification" --previous-out "$scratch/fp006-20260912-11227b8/outputs" --out "$runroot/outputs"'
    setup+=command+'\n'
    setup+=f'''systemd-run --unit=praxis{option}-stage2 --property=RuntimeMaxSec={seconds+120} --property=WorkingDirectory="$runroot" --setenv=HF_HOME="$scratch/hf006" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id {run} --prereg "$study/{sub}/PREREGISTRATION.md" --prereg-sha256 {preregsha} --seconds {seconds} -- {command} --execute
systemctl is-active praxis{option}-stage2
'''
    parts.append(setup)
(root/'deploy_stage2.sh').write_text('\n'.join(parts),encoding='utf-8',newline='\n')
print(root/'deploy_stage2.sh')
