"""Run synthetic indexed worker controls inside the already-qualified Linux image.

Invoke as the same nonroot user with network-none/cap-drop/read-only-root settings.
This does not download or execute benchmark programs and makes no model calls.
"""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import importlib.util
import json
import subprocess
import sys

CASES = [
    ("pass_pass", "return -coefficients[0] / coefficients[1]", ["pass", "pass"]),
    ("pass_fail", "return 1.0", ["pass", "fail"]),
    ("fail_pass", "return 0.0 if coefficients[0] == -1 else 2.0", ["fail", "pass"]),
]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path,default=Path('/app/worker.py'));parser.add_argument('--expected-worker-sha256',required=True);parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    worker_hash=hashlib.sha256(args.worker.read_bytes()).hexdigest()
    if worker_hash != args.expected_worker_sha256:raise RuntimeError('Frozen worker hash mismatch')
    spec=importlib.util.spec_from_file_location('isolated_worker_control',args.worker);worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)
    worker.assert_isolation()
    args.output_dir.mkdir(parents=True,exist_ok=True);results=[]
    for name,body,expected_status in CASES:
        root=args.output_dir/name;root.mkdir(parents=True,exist_ok=True)
        code='def find_zero(coefficients):\n    '+body+'\n'
        cases=[{'case_id':'case-0','input':[[-1,1]],'split':'tool','memberships':['synthetic']},{'case_id':'case-1','input':[[-2,1]],'split':'outcome','memberships':['synthetic']}]
        task={'task_id':'Synthetic/'+name,'entry_point':'find_zero','programs':{'canonical':code,'reference':code,'buggy':code},'original_test':'def check(candidate):\n    assert True\ncheck(find_zero)\n','cases':cases,'atol':1e-6}
        task_path=root/'task.json';task_path.write_text(json.dumps(task)+'\n',encoding='utf-8')
        expected_path=root/'expected.jsonl'
        expected_rows=[{'case_id':f'case-{i}','status':'pass','elapsed_seconds':0.001,'expected':{'t':'float','v':float(i+1).hex()}} for i in range(2)]
        expected_path.write_text(''.join(json.dumps(row)+'\n' for row in expected_rows),encoding='utf-8')
        output=root/'worker_output'
        run=subprocess.run([sys.executable,str(args.worker),'--task-file',str(task_path),'--variant','canonical','--expected-file',str(expected_path),'--output-dir',str(output)],capture_output=True,text=True,timeout=30)
        if run.returncode:
            results.append({'id':name,'passed':False,'exit_code':run.returncode,'stderr':run.stderr[-1000:]});continue
        observed=[json.loads(line) for line in (output/'cases.jsonl').read_text().splitlines() if line.strip()]
        summary=json.loads((output/'summary.json').read_text())
        actual=[row['status'] for row in observed]
        passed=actual==expected_status and [row['case_index'] for row in observed]==[0,1] and [row['case_id'] for row in observed]==['case-0','case-1'] and summary['assigned_cases']==2 and summary['status_counts']==dict(collections.Counter(expected_status)) and summary['original']['status']=='pass'
        results.append({'id':name,'passed':passed,'expected':expected_status,'actual':actual,'completed_case_indices':[row['case_index'] for row in observed],'assigned_cases':summary['assigned_cases'],'original_status':summary['original']['status'],'case_output_sha256':hashlib.sha256((output/'cases.jsonl').read_bytes()).hexdigest(),'summary_sha256':hashlib.sha256((output/'summary.json').read_bytes()).hexdigest()})
    report={'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Validator-authored synthetic linear-polynomial bookkeeping cases executed through actual worker.main under its required isolation; no benchmark/model calls.','worker_sha256':worker_hash,'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'controls':len(CASES),'passed':sum(r['passed'] for r in results),'results':results,'isolation_precheck_passed':True}
    (args.output_dir/'BOOKKEEPING_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps({'controls':report['controls'],'passed':report['passed']}));return 0 if report['passed']==report['controls'] else 1


if __name__=='__main__':raise SystemExit(main())
