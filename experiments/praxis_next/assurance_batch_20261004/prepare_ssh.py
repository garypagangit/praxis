"""Bundle unchanged scientific inputs and freeze the current SSH runtime."""
import json,hashlib,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PRIVATE=Path('C:/w/assurance_aws_20261004_attempt6')
PRIVATE.mkdir(exist_ok=True)
settings=json.loads(Path('C:/w/px107_aws_pilot/settings.json').read_text())
settings['prefix']='praxis-next/assurance/20261004-attempt6/'
(PRIVATE/'settings.json').write_text(json.dumps(settings,indent=2))
with tarfile.open(PRIVATE/'bundle.tar.gz','w:gz') as a:
    a.add(HERE/'run_language.py',arcname='run_language.py')
    for name in ['receipts.json','narrative_inputs.json']:
        a.add(Path('C:/w/assurance_batch_20261004')/name,arcname='inputs/'+name)
files=['run_language.py','cloud.sh','cloud_run.py','CLOUD_PROTOCOL.txt','recover_ssh.py']
freeze={'bundle_sha256':hashlib.sha256((PRIVATE/'bundle.tar.gz').read_bytes()).hexdigest(),
        'runtime_files':{(HERE/f).relative_to(ROOT).as_posix():hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in files},
        'model_digest':'357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b',
        'ollama_version':'0.17.0','reason':'Infrastructure repair: SSH launch and persistent data disk; unchanged scientific protocol.'}
(HERE/'CLOUD_FREEZE.json').write_text(json.dumps(freeze,indent=2))
print(PRIVATE)
