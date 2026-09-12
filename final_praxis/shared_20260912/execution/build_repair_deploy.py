from pathlib import Path
import hashlib,json,zipfile
source=Path('C:/w/fp005/final_praxis/005_defense_distillation/environment_repair')
here=Path(__file__).resolve().parent
archive=here/'fp005-protobuf-09f90d7.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for path in source.glob('*'):
        if path.is_file():z.write(path,path.name)
digest=hashlib.sha256(archive.read_bytes()).hexdigest()
script=f'''set -eu
scratch=/mnt/praxis-20260912-005
runroot=$scratch/fp005-20260912-37fdd3f
repair=$runroot/environment_repair_09f90d7
mkdir -p "$repair"
export REPAIR_DIR="$repair"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json,shutil
from pathlib import Path
root=Path(os.environ['REPAIR_DIR']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/fp005-protobuf-09f90d7.zip',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='{digest}'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
status=json.loads((root.parent/'cloud_status.json').read_text())
assert status['state']=='FAILED',status['state']
for name in ('cloud_status.json','driver.log'):
    target=root/('before_repair_'+name)
    if target.exists():raise RuntimeError('Prior repair launch found')
    shutil.copy2(root.parent/name,target)
prereg=root.parent/'code/final_praxis/005_defense_distillation/PREREGISTRATION.md'
(root/'prereg.sha256').write_text(hashlib.sha256(prereg.read_bytes()).hexdigest())
PY
prereg=$runroot/code/final_praxis/005_defense_distillation/PREREGISTRATION.md
preregsha=$(cat "$repair/prereg.sha256")
systemd-run --unit=praxis005-protobuf-repair --property=RuntimeMaxSec=7320 --property=WorkingDirectory="$runroot" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/code/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id fp005-20260912-37fdd3f --prereg "$prereg" --prereg-sha256 "$preregsha" --seconds 7200 -- "$scratch/venv/bin/python" "$repair/resume_evaluation.py" --execute
systemctl is-active praxis005-protobuf-repair
'''
(here/'deploy005repair.sh').write_text(script,encoding='utf-8',newline='\n')
print(json.dumps({'archive':str(archive),'sha256':digest,'bytes':archive.stat().st_size}))
