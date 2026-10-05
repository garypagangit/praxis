"""Read-only source acquisition. Does not execute downloaded code or commands."""
import hashlib,json,subprocess
from pathlib import Path
import requests
HERE=Path(__file__).resolve().parent
OUT=Path('C:/w/px116_20261005'); OUT.mkdir(exist_ok=True)
OLD=Path('C:/Users/garyp/OneDrive/Documents/codex')
COMMIT='720d9e7'
paths=['cloud_jobs/px067_noop_canonicalization_20260731/px067_design.py',
       'cloud_jobs/px067_noop_canonicalization_20260731/run_px067_blackbox.py',
       'cloud_jobs/px050y_packmonitor_blackbox_20260731/run_px050y_blackbox.py',
       'configs/px067_noop_canonicalization_preregistration_20260731.json',
       'configs/px069_gate_blind_command_audit_preregistration_20260731.json']
manifest={'old_git_commit':subprocess.check_output(['git','rev-parse',COMMIT],cwd=OLD,text=True).strip(),'files':[]}
for name in paths:
    content=subprocess.check_output(['git','show',f'{COMMIT}:{name}'],cwd=OLD)
    target=OUT/'historical'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    manifest['files'].append({'source':name,'local':str(target),'sha256':hashlib.sha256(content).hexdigest()})
revision='b74c0d0bf70d2c0bc459be537895cca163007f1a'
url=f'https://huggingface.co/datasets/bigcode/bigcodebench/resolve/{revision}/data/v0.1.4-00000-of-00001.parquet'
target=OUT/'bigcodebench_v014.parquet'
if not target.exists():
    r=requests.get(url,timeout=90);r.raise_for_status();target.write_bytes(r.content)
manifest['dataset']={'repo':'bigcode/bigcodebench','revision':revision,'url':url,'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
manifest['comparators']={name:{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=OUT/name,text=True).strip(),'path':str(OUT/name)} for name in ['PackMonitor','AgentSpec']}
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'historical_files':len(paths),'dataset_bytes':target.stat().st_size,'comparators':manifest['comparators']},indent=2))
