"""Select source qualification tasks before sandbox outcomes; not confirmation."""
import ast,hashlib,json,sys,tarfile
from pathlib import Path
import pandas as pd
HERE=Path(__file__).resolve().parent; OUT=Path('C:/w/px116_20261005')
data=pd.read_parquet(OUT/'bigcodebench_v014.parquet')
eligible=[]
for row in data.to_dict('records'):
    libraries=set(ast.literal_eval(row['libs']))
    if libraries-sys.stdlib_module_names=={'numpy'}:
        eligible.append(row)
selected=sorted(eligible,key=lambda r:hashlib.sha256(('11601|'+r['task_id']).encode()).hexdigest())[:12]
tasks=[]
for row in selected:
    source=row['code_prompt']+row['canonical_solution']+'\n'+row['test']+'\nif __name__ == "__main__":\n    unittest.main()\n'
    ast.parse(source)
    tasks.append({'id':row['task_id'],'source':source,'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'libraries':ast.literal_eval(row['libs'])})
(OUT/'pilot_tasks.json').write_text(json.dumps(tasks,indent=2),encoding='utf-8')
record={'id':'PX-116','stage':'DEVELOPMENT_SANDBOX_QUALIFICATION','dataset_rows':len(data),'numpy_only_eligible':len(eligible),
 'selection':'first 12 eligible tasks ordered by sha256(11601|task_id); before sandbox outcomes',
 'tasks':[{'id':r['id'],'sha256':r['source_sha256']} for r in tasks],
 'scope':'Author reference implementations/tests with controlled install forms, not model-generated tasks or confirmatory method comparison.',
 'command_forms':['pip install numpy==2.2.6','pip install -r requirements.txt','pip install --no-deps numpy==2.2.6','python -m pip install numpy==2.2.6'],
 'reference_qualification':'Direct pinned installation then all author unit tests must pass; do not count install exit alone.',
 'resources':'12 source tasks; parallelism 4; 90 sec per reference/container; no network during test; unprivileged UID; CPU/memory/process limits',
 'invalid_controls':'Two historical empty-operand forms, one local nonexistent package and one nonexistent version; offline resolver only; no package registration.'}
(HERE/'PILOT_FREEZE.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='tasks'},indent=2))
