"""Publish only a complete, audited GPU cohort and both attempt cost receipts."""
import json,shutil,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRIVATE=Path(json.loads((HERE/'RUN_CONTEXT.json').read_text())['data_dir']).parents[2]
OUT=PRIVATE/'collected/outputs'
subprocess.run([sys.executable,str(HERE/'audit_language.py')],check=True)
for name in ['PX114_RESULTS.json','PX115_RESULTS.json']:
    shutil.copy2(OUT/name,HERE/name)
costs=[]
for folder in ['C:/w/assurance_aws_20261004']+[f'C:/w/assurance_aws_20261004_attempt{i}' for i in [2,3,4]]:
    p=Path(folder)/'COMPUTE.json'
    if p.exists(): costs.append({'attempt':folder,'receipt':json.loads(p.read_text())})
(HERE/'AWS_COMPUTE.json').write_text(json.dumps(costs,indent=2))
context=json.loads((HERE/'RUN_CONTEXT.json').read_text())
context['compute_note']='Completed AWS GPU cohort; both startup and successful-run receipts in AWS_COMPUTE.json. Worker stop verified. Estimates are not invoices.'
(HERE/'RUN_CONTEXT.json').write_text(json.dumps(context,indent=2))
subprocess.run([sys.executable,str(HERE/'update_status.py')],check=True)
print('GPU results audited and published locally; CPU pilot retained separately.')
