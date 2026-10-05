"""Prepare bounded AWS source qualification from the proven SSH launcher."""
import json,hashlib,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
DATA=Path('C:/w/px116_20261005');PRIVATE=Path('C:/w/px116_aws_20261005');PRIVATE.mkdir(exist_ok=True)
old=HERE.parent/'assurance_batch_20261004'
source=(old/'cloud_run.py').read_text().replace('C:/w/assurance_aws_20261004_attempt6',str(PRIVATE).replace('\\','/')).replace('praxis-assurance-','praxis-package-')
(HERE/'cloud_run.py').write_text(source,encoding='utf-8')
(HERE/'recover_ssh.py').write_text((old/'recover_ssh.py').read_text(),encoding='utf-8')
settings=json.loads(Path('C:/w/assurance_aws_20261004_attempt6/settings.json').read_text());settings['prefix']='praxis-next/package-completion/20261005/'
(PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
    a.add(HERE/'sandbox_pilot.py',arcname='sandbox_pilot.py')
    a.add(DATA/'pilot_tasks.json',arcname='pilot_tasks.json')
    for p in (DATA/'historical/cloud_jobs').rglob('*.py'):a.add(p,arcname=p.relative_to(DATA).as_posix())
files=['cloud_run.py','cloud.sh','recover_ssh.py','sandbox_pilot.py','CLOUD_PROTOCOL.txt','PILOT_FREEZE.json']
freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),
 'runtime_files':{(HERE/f).relative_to(ROOT).as_posix():hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in files},
 'stage':'SOURCE_AND_SANDBOX_QUALIFICATION_NO_NEW_MODEL_EFFICACY'}
(HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2))
print(PRIVATE)
