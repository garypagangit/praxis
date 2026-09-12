set -eu
scratch=/mnt/praxis-20260912-005
run_id=fp005-20260912-37fdd3f
run_root="$scratch/$run_id"
test "$(findmnt -n -o TARGET --target "$scratch")" = "$scratch"
mkdir -p "$run_root"
aws s3 cp s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/bundles/fp005-37fdd3f-ab381d74.zip "$run_root/source_bundle.zip" --region us-east-1 --no-progress
python3 - <<'PY'
import hashlib,json,pathlib,subprocess,zipfile
from datetime import datetime,timezone
root=pathlib.Path('/mnt/praxis-20260912-005/fp005-20260912-37fdd3f')
bundle=root/'source_bundle.zip'
expected='ab381d7439a706b5a3852e949588a19cfdae4394aefb7651d03c12727aa590f8'
if hashlib.sha256(bundle.read_bytes()).hexdigest()!=expected:raise RuntimeError('Source bundle hash mismatch')
code=root/'code';code.mkdir(exist_ok=True)
with zipfile.ZipFile(bundle) as archive:
    for name in archive.namelist():
        target=(code/name).resolve()
        if code.resolve() not in target.parents:raise RuntimeError('Unsafe archive path')
    archive.extractall(code)
manifest=json.loads((code/'bundle_manifest.json').read_text())
if manifest['git_commit']!='37fdd3f154a78017f9eb313385e25379c36affde':raise RuntimeError('Unexpected source commit')
for name,digest in manifest['files'].items():
    if hashlib.sha256((code/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Extracted source changed')
prereg=code/'final_praxis/005_defense_distillation/PREREGISTRATION.md'
prereg_sha='21d3fee055f08fc916f0a0fbab6a6ae4437f05e1dc4d8cd23ff2a1b13c681b9b'
if hashlib.sha256(prereg.read_bytes()).hexdigest()!=prereg_sha:raise RuntimeError('Preregistration hash mismatch')
stop=datetime.fromisoformat('2026-09-12T15:55:49.634894+00:00')
remaining=int((stop-datetime.now(timezone.utc)).total_seconds())-300
seconds=min(25200,remaining-60)
if seconds<1800:raise RuntimeError('Insufficient remaining cloud budget')
subprocess.run(['shutdown','-P','+'+str(remaining//60)],check=True)
command=['systemd-run','--unit=fp005-20260912-37fdd3f','--collect',
    '--property=RuntimeMaxSec='+str(seconds+30),'--property=KillMode=control-group',
    '/usr/bin/python3',str(code/'final_praxis/shared_20260912/supervisor.py'),
    '--root',str(root),'--run-id','fp005-20260912-37fdd3f','--prereg',str(prereg),
    '--prereg-sha256',prereg_sha,'--seconds',str(seconds),'--',
    '/bin/bash',str(code/'final_praxis/005_defense_distillation/cloud/bootstrap.sh'),
    str(root.parent),str(root)]
receipt={'run_id':'fp005-20260912-37fdd3f','instance':'i-039ed976444ade397',
    'git_commit':manifest['git_commit'],'bundle_sha256':expected,'preregistration_sha256':prereg_sha,
    'stop_at_utc':stop.isoformat(),'supervisor_seconds':seconds,'command':command,
    'recorded_utc':datetime.now(timezone.utc).isoformat(),
    's3_uri':'s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260912/runs/fp005-20260912-37fdd3f/'}
(root/'launch.json').write_text(json.dumps(receipt,indent=2))
subprocess.run(command,check=True)
print(json.dumps(receipt))
PY
