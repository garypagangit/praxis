"""Package the bounded AWS run without starting compute."""
import hashlib,json,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=HERE.parent/'aivh_20261005';PRIVATE=Path('C:/w/px117c_aws_20261005')
settings=json.loads(Path('C:/w/px117_aws_20261005/settings.json').read_text())
settings['prefix']='praxis-next/aivh/20261005-gambit1/'
(PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
run=(OLD/'cloud_run.py').read_text().replace('C:/w/px117_aws_20261005',str(PRIVATE)).replace('praxis-aivh-','praxis-gambit-')
run=run.replace('HERE/\'CLOUD_PROTOCOL.txt\'','HERE/\'PROTOCOL.txt\'')
(HERE/'cloud_run.py').write_text(run)
(HERE/'recover_ssh.py').write_text((OLD/'recover_ssh.py').read_text())
(HERE/'cloud.sh').write_text((OLD/'cloud.sh').read_text().replace('train_development.py','train.py'))
with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
    a.add(PRIVATE/'records.json',arcname='records.json')
    for name in ['train.py','common.py']:a.add(HERE/name,arcname=name)
files=['cloud_run.py','recover_ssh.py','cloud.sh','train.py','common.py','PROTOCOL.txt','DATA.json','build_data.py']
freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),
        'runtime_files':{(HERE/n).relative_to(ROOT).as_posix():hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in files},
        'stage':'DEVELOPMENT_COMMON_COMMANDS_NOT_APT_CONFIRMATION'}
(HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n')
print(json.dumps({'bundle_bytes':(PRIVATE/'bundle.tar.gz').stat().st_size,'private':str(PRIVATE)}))
