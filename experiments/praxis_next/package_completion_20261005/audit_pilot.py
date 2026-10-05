"""Recount container test outcomes without using reported policy success totals."""
import hashlib,json,re,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('PX116_OUTPUT','C:/w/px116_aws_20261005_attempt2/collected/outputs'))
checks=[]
def ck(name,ok):
    checks.append({'check':name,'pass':bool(ok)})
    assert ok,name
rows=[json.loads(p.read_text()) for p in sorted(OUT.glob('task_*.json'))]
frozen=json.loads((HERE/'PILOT_FREEZE.json').read_text())
ids={r['id'] for r in frozen['tasks']}
ck('all 48 unique task-form cases',len(rows)==48 and len({(r['task_id'],r['form']) for r in rows})==48)
ck('only frozen tasks and four forms',{r['task_id'] for r in rows}==ids and {r['form'] for r in rows}=={0,1,2,3})
valid_results={}; reference=set();test_counts={}
for row in rows:
    messages=[]
    for line in row['actual']['stdout'].splitlines():
        try:messages.append(json.loads(line))
        except ValueError:pass
    install=next((r for r in messages if 'install_exit' in r),None)
    tests=next((r for r in messages if 'tests_exit' in r),None)
    ok=row['actual']['exit']==0
    if ok:
        ck('install and test exits '+row['task_id']+str(row['form']),install is not None and tests is not None and install['install_exit']==tests['tests_exit']==0)
        found=re.search(r'Ran (\d+) tests?',tests['tests_stderr'])
        ck('nonzero tests executed '+row['task_id']+str(row['form']),found is not None and int(found[1])>0)
        test_counts[row['task_id']]=int(found[1])
    valid_results[(row['task_id'],row['form'])]=ok
    if row['form']==0 and ok:reference.add(row['task_id'])
summary=json.loads((OUT/'PILOT_RESULTS.json').read_text())
ck('recount reference qualification',len(reference)==summary['reference_qualified'])
ck('recount actual functional successes',sum(valid_results.values())==summary['actual_passes'])
for method,reported in summary['by_policy'].items():
    eligible=[r for r in rows if r['task_id'] in reference]
    complete=sum(r['policy_decisions'][method]=='allow' and valid_results[(r['task_id'],r['form'])] for r in eligible)
    ck('recount '+method,complete==reported['completed'] and len(eligible)==reported['qualified_task_form_cases'])
ck('worker completed',(OUT/'WORKER_EXIT.txt').read_text().strip()=='0')
result={'status':'PASS','checks':checks,'tests_per_qualified_task':test_counts,
 'scope':'Artifact/count audit of controlled source qualification; not an independent human review or confirmatory efficacy test.'}
(HERE/'PILOT_AUDIT.json').write_text(json.dumps(result,indent=2))
print(f'{len(checks)} checks passed; {sum(test_counts.values())} distinct author test cases across {len(test_counts)} tasks')
