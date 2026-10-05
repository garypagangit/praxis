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
       'configs/px069_gate_blind_command_audit_preregistration_20260731.json',
       'scripts/px069_independent_adjudicator.py','scripts/px069_blinded_consensus.py',
       'tests/test_px069_gate_blind_audit.py']
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
bcb_commit='09dd993f46c3fbf3a799465bb96d524edcb0b199'
req_url=f'https://raw.githubusercontent.com/bigcode-project/bigcodebench/{bcb_commit}/Requirements/requirements-eval.txt'
response=requests.get(req_url,timeout=30);response.raise_for_status();(OUT/'bcb_requirements-eval.txt').write_bytes(response.content)
manifest['author_environment']={'commit':bcb_commit,'url':req_url,'sha256':hashlib.sha256(response.content).hexdigest(),'numpy_pin':'1.21.2'}
manifest['comparators']={name:{'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=OUT/name,text=True).strip(),'path':str(OUT/name)} for name in ['PackMonitor','AgentSpec']}
assert manifest['dataset']['sha256']=='d9a4965821c9507ebdfb551c288656b2d5fe553234f5183044333ca8a4018267'
assert manifest['author_environment']['sha256']=='a4d01fb12cbce5223b51f982265cb7975bea770b758cd85cc91b803d3293e39f'
assert manifest['comparators']['PackMonitor']['commit']=='8808362e14891fe692b17b8192ed123dff4d64d2'
assert manifest['comparators']['AgentSpec']['commit']=='e6fa3902e2cfb9681f454b355691b771f70543f8'
(HERE/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'historical_files':len(paths),'dataset_bytes':target.stat().st_size,'comparators':manifest['comparators']},indent=2))
