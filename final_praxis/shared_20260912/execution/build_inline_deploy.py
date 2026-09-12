from pathlib import Path
import hashlib
here=Path(__file__).resolve().parent
prereg=Path('C:/w/fp007/final_praxis/007_overthinking_revision/selective_update_inline/PREREGISTRATION.md')
digest=hashlib.sha256(prereg.read_bytes()).hexdigest()
text=f'''set -eu
scratch=/mnt/praxis-20260912-004
runroot=$scratch/fp007-inline-20260912-648cdcd
test -d "$scratch/venv"
mountpoint -q "$scratch"
mkdir -p "$runroot"
export RUNROOT="$runroot"
"$scratch/venv/bin/python" - <<'PY'
import boto3,hashlib,os,zipfile,json
from pathlib import Path
from datetime import datetime,timezone
assert datetime.now(timezone.utc)<datetime.fromisoformat('2026-09-12T12:50:00+00:00'),'Insufficient remaining scheduled host time'
root=Path(os.environ['RUNROOT']);archive=root/'source.zip'
boto3.client('s3',region_name='us-east-1').download_file('praxis-garypagan-272615233626-us-east-1','final-praxis/20260912/bundles/fp007-inline-648cdcd.zip',str(archive))
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='0cb81b55b6cbeb32ee2e8b655d191e49ccee75549889875933e33502e5d1e41b'
with zipfile.ZipFile(archive) as z:
    assert all((root/n).resolve().is_relative_to(root.resolve()) for n in z.namelist())
    z.extractall(root)
for name,sha in json.loads((root/'bundle_manifest.json').read_text())['files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
PY
study=$runroot/final_praxis/007_overthinking_revision/selective_update_inline
export PRAXIS_PREREG_PATH="$study/PREREGISTRATION.md"
export PRAXIS_PREREG_SHA256={digest}
"$scratch/venv/bin/python" "$study/run_selective.py" --out "$runroot/outputs"
systemd-run --unit=praxis007-inline --property=RuntimeMaxSec=3720 --property=WorkingDirectory="$runroot" --setenv=PYTHONUNBUFFERED=1 "$scratch/venv/bin/python" "$runroot/final_praxis/shared_20260912/supervisor.py" --root "$runroot" --run-id fp007-inline-20260912-648cdcd --prereg "$study/PREREGISTRATION.md" --prereg-sha256 {digest} --seconds 3600 -- "$scratch/venv/bin/python" "$study/run_selective.py" --out "$runroot/outputs" --source-out "$scratch/fp007-selective-20260912-1c47aca/outputs" --execute
systemctl is-active praxis007-inline
'''
(here/'deploy007inline.sh').write_text(text,encoding='utf-8',newline='\n')
print(digest)
