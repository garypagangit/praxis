"""Prepare the bounded AWS development audit using the verified stop controller."""
import hashlib,json,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PRIVATE=Path('C:/w/px117_aws_20261005');PRIVATE.mkdir(exist_ok=True)
OLD=HERE.parent/'package_completion_20261005'
source=(OLD/'cloud_run.py').read_text().replace('C:/w/px116_aws_20261005_attempt2',str(PRIVATE).replace('\\','/')).replace('praxis-package-','praxis-aivh-')
source=source.replace('isolated container qualification and results','development classifier and source-confounding audit')
(HERE/'cloud_run.py').write_text(source)
(HERE/'recover_ssh.py').write_text((OLD/'recover_ssh.py').read_text())
settings=json.loads(Path('C:/w/px116_aws_20261005_attempt2/settings.json').read_text())
settings['prefix']='praxis-next/aivh/20261005-development1/'
(PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
(HERE/'CLOUD_PROTOCOL.txt').write_text((HERE/'DEVELOPMENT_PROTOCOL.txt').read_text())
with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
    a.add(HERE/'train_development.py',arcname='train_development.py')
    a.add(PRIVATE/'records.json',arcname='records.json')
    for name in ['predict.py','build_development_data.py']:
        a.add(HERE/name,arcname=name)
    for p in (HERE/'supplied/aivh').glob('*.py'):
        a.add(p,arcname='supplied/aivh/'+p.name)
names=['cloud_run.py','recover_ssh.py','cloud.sh','train_development.py','predict.py','build_development_data.py','CLOUD_PROTOCOL.txt','DEVELOPMENT_DATA.json']
freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),
    'runtime_files':{(HERE/n).relative_to(ROOT).as_posix():hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in names},
    'stage':'DEVELOPMENT_SOURCE_CONFOUNDED_NOT_CONFIRMATION'}
(HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2))
print(json.dumps({'private':str(PRIVATE),'bundle_bytes':(PRIVATE/'bundle.tar.gz').stat().st_size}))
