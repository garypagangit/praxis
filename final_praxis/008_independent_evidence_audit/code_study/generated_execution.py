"""Execute admitted generated proposals in the frozen qualification container.

Preparation hashes existing reference outputs only. Execution rechecks admission,
the exact callable signature, all code/data hashes, and Docker isolation. Invalid
proposal placeholders remain in the output manifest and are never executed.
"""
from __future__ import annotations
import argparse
import ast
import collections
import concurrent.futures
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
IMAGE_QUALIFICATION=Path('/app') if Path('/app/worker.py').exists() else HERE/'qualification'
sys.path.insert(0,str(IMAGE_QUALIFICATION))
from worker import assert_isolation, decode_value

FAILURES={'fail','exception','timeout','program_load_error'}
OBSERVED={'pass',*FAILURES}

def sha_bytes(data):return hashlib.sha256(data).hexdigest()
def sha(path):return sha_bytes(path.read_bytes())
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]

def signature(source,entry):
    tree=ast.parse(source)
    functions=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==entry]
    if len(functions)!=1:raise ValueError('entry_point_missing_or_repeated')
    fn=functions[0]
    return {'name':fn.name,'args':ast.dump(fn.args,include_attributes=False),'returns':ast.dump(fn.returns,include_attributes=False) if fn.returns else None,'type':'FunctionDef'}

def outcome_label(rows):
    reserved=[row for row in rows if row['split']=='outcome']
    if not reserved:return None
    if all(row['status']=='pass' for row in reserved):return True
    if any(row['status'] in FAILURES for row in reserved):return False
    return None

def prepare_references(tasks,arguments):
    records=[]
    for task_id,task in sorted(tasks.items(),key=lambda pair:int(pair[0].split('/')[1])):
        relative=f"task_{task_id.split('/')[1]}/reference_complete.jsonl"
        path=arguments.qualification_private/relative
        if not path.exists():
            records.append({'task_id':task_id,'path':relative,'present':False});continue
        rows=jsonl(path);ids=[row['case_id'] for row in rows]
        expected_cases={case['case_id']:case for case in task['cases']};expected_ids=set(expected_cases)
        if len(ids)!=len(set(ids)) or set(ids)!=expected_ids:raise ValueError('Reference case cohort mismatch:'+task_id)
        if any(row['task_id']!=task_id or row['variant']!='reference' for row in rows):raise ValueError('Reference identity mismatch:'+task_id)
        for row in rows:
            case=expected_cases[row['case_id']]
            if row['split']!=case['split'] or row['memberships']!=case['memberships']:raise ValueError('Reference case split/membership mismatch:'+task_id)
            if row['status']=='pass':
                decode_value(row['expected'])
                if not isinstance(row.get('elapsed_seconds'),(int,float)) or not math.isfinite(row['elapsed_seconds']) or row['elapsed_seconds']<0:raise ValueError('Invalid reference timing:'+task_id)
        records.append({'task_id':task_id,'path':relative,'present':True,'sha256':sha(path),'case_count':len(rows),'status_counts':dict(collections.Counter(row['status'] for row in rows)),'reserved_all_reference_pass':all(row['status']=='pass' for row in rows if row['split']=='outcome')})
    return {'schema_version':1,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Hashes existing qualification reference files before model calls; no program execution or model calls.','tasks_sha256':sha(arguments.tasks_file),'worker_sha256':sha(IMAGE_QUALIFICATION/'worker.py'),'generated_runner_sha256':sha(Path(__file__)),'admission_sha256':sha(HERE/'review/execution_admission.py'),'qualification_summary_sha256':sha(arguments.qualification_summary),'qualification_summary_decision':read_json(arguments.qualification_summary)['decision'],'eligible_ids':read_json(arguments.qualification_summary)['eligible_ids'],'records':records}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks-file',type=Path,default=Path('/data/tasks.jsonl'))
    parser.add_argument('--qualification-private',type=Path,default=Path('/qualification_private'))
    parser.add_argument('--qualification-summary',type=Path,default=Path('/qualification_summary.json'))
    parser.add_argument('--prepare-reference-manifest',type=Path)
    parser.add_argument('--reference-manifest',type=Path)
    parser.add_argument('--proposals',type=Path)
    parser.add_argument('--output-dir',type=Path,default=Path('/output'))
    parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args()
    tasks_list=jsonl(args.tasks_file);tasks={row['task_id']:row for row in tasks_list}
    if len(tasks_list)!=164 or set(tasks)!={f'Python/{i}' for i in range(164)}:raise ValueError('Exact164 source tasks required')
    if args.prepare_reference_manifest:
        report=prepare_references(tasks,args);write_json(args.prepare_reference_manifest,report)
        print(json.dumps({'reference_manifest':str(args.prepare_reference_manifest),'sha256':sha(args.prepare_reference_manifest),'records':len(report['records']),'programs_executed':False},indent=2));return 0
    if not args.reference_manifest or not args.proposals:parser.error('Execution requires --reference-manifest and --proposals')
    assert_isolation()
    if not 1<=args.workers<=3:raise ValueError('One to three concurrent proposals allowed')
    ref_manifest=read_json(args.reference_manifest)
    hash_checks={'tasks_sha256':sha(args.tasks_file),'worker_sha256':sha(IMAGE_QUALIFICATION/'worker.py'),'generated_runner_sha256':sha(Path(__file__)),'admission_sha256':sha(HERE/'review/execution_admission.py'),'qualification_summary_sha256':sha(args.qualification_summary)}
    if any(ref_manifest.get(key)!=value for key,value in hash_checks.items()):raise ValueError('Reference/source/execution freeze hash mismatch')
    if ref_manifest['qualification_summary_decision']!='QUALIFIED_FOR_SEPARATELY_FROZEN_POLICY_STUDY':raise ValueError('Full qualification has not passed')
    reference_by={row['task_id']:row for row in ref_manifest['records']};eligible=set(ref_manifest['eligible_ids'])
    admission_path=HERE/'review/execution_admission.py'
    spec=importlib.util.spec_from_file_location('frozen_execution_admission',admission_path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    proposals=[]
    for line_number,line in enumerate(args.proposals.read_text(encoding='utf-8').splitlines(),1):
        if not line.strip():continue
        try:
            row=json.loads(line)
            if not isinstance(row,dict):raise ValueError('row_not_object')
        except (json.JSONDecodeError,ValueError):row={'task_id':None,'proposal_id':f'line_{line_number}','status':'invalid_json'}
        proposals.append({**row,'source_line':line_number})
    counts=collections.Counter((str(row.get('task_id')),str(row.get('proposal_id'))) for row in proposals)
    output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
    config={'tasks_sha256':hash_checks['tasks_sha256'],'proposals_sha256':sha(args.proposals),'reference_manifest_sha256':sha(args.reference_manifest),'execution_hashes':hash_checks,'workers':args.workers,'image_id':os.environ.get('PRAXIS_IMAGE_ID'),'assigned_proposal_rows':len(proposals)}
    config_path=output/'RUN_CONFIGURATION.json'
    if config_path.exists() and read_json(config_path)!=config:raise ValueError('Output directory has a different frozen configuration')
    write_json(config_path,config);started=time.monotonic()
    def one(proposal):
        task_id=proposal.get('task_id');proposal_id=proposal.get('proposal_id');task=tasks.get(task_id)
        record={'source_line':proposal['source_line'],'task_id':task_id,'proposal_id':proposal_id,'manifest_status':proposal.get('status'),'declared_code_sha256':proposal.get('code_sha256'),'code_sha256':None,'code_hash_verified':False,'cases_path':None,'executed':False,'y1':None,'execution_status':'not_executed','rejection_reasons':[],'admission':None,'signature_matches':None,'original_test':None,'tool_status_vector':[]}
        reasons=record['rejection_reasons']
        if task is None:reasons.append('unknown_task')
        if not isinstance(proposal_id,str) or not proposal_id:reasons.append('invalid_proposal_id')
        if counts[(str(task_id),str(proposal_id))]!=1:reasons.append('duplicate_proposal_identity')
        if proposal.get('status')!='admitted':reasons.append('manifest_not_admitted')
        source=proposal.get('code')
        if not isinstance(source,str):reasons.append('code_not_text')
        else:
            record['code_sha256']=sha_bytes(source.encode())
            record['code_hash_verified']=record['code_sha256']==proposal.get('code_sha256')
            if not record['code_hash_verified']:reasons.append('code_hash_mismatch')
        if task_id not in eligible:reasons.append('task_not_qualified')
        if task is not None and isinstance(source,str):
            admission=module.admit_source(source,task['entry_point']);record['admission']={key:admission[key] for key in ('version','admitted','reasons','source_sha256')}
            if not admission['admitted']:reasons.append('source_admission_rejected')
            try:record['signature_matches']=signature(source,task['entry_point'])==signature(task['programs']['canonical'],task['entry_point'])
            except (SyntaxError,ValueError,RecursionError,MemoryError):record['signature_matches']=False
            if not record['signature_matches']:reasons.append('signature_mismatch')
        ref=reference_by.get(task_id)
        if not ref or not ref.get('present') or not ref.get('reserved_all_reference_pass'):reasons.append('reference_unqualified_or_missing')
        reference_path=None
        if ref and ref.get('present'):
            reference_path=args.qualification_private/ref['path']
            if not reference_path.exists() or sha(reference_path)!=ref['sha256']:reasons.append('reference_hash_mismatch')
        normalized=[]
        if reasons:
            if task is not None:
                normalized=[{'task_id':task_id,'proposal_id':proposal_id,'case_id':case['case_id'],'split':case['split'],'status':'not_executed_rejected'} for case in task['cases']]
        else:
            key=sha_bytes((task_id+'\0'+proposal_id).encode());directory=output/'private'/key;directory.mkdir(parents=True,exist_ok=True)
            copied=copy.deepcopy(task);copied['programs']['buggy']=source
            task_path=directory/'task.json';write_json(task_path,copied)
            attempts=sorted(path for path in directory.glob('attempt_*') if path.is_dir());complete=None
            for attempt in attempts:
                if (attempt/'summary.json').exists() and (attempt/'cases.jsonl').exists():
                    summary=read_json(attempt/'summary.json')
                    if summary.get('code_sha256')==proposal['code_sha256'] and summary.get('assigned_cases')==len(task['cases']):complete=attempt
            if complete is None:
                complete=directory/f'attempt_{len(attempts)+1:03d}';complete.mkdir()
                command=[sys.executable,str(IMAGE_QUALIFICATION/'worker.py'),'--task-file',str(task_path),'--variant','buggy','--expected-file',str(reference_path),'--output-dir',str(complete)]
                try:
                    with (complete/'process.log').open('wb') as log:process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=135)
                    process_receipt={'status':'exited','exit_code':process.returncode}
                except subprocess.TimeoutExpired:process_receipt={'status':'wall_timeout','exit_code':None}
                write_json(complete/'PROCESS_RECEIPT.json',{**process_receipt,'command':command})
            observed=[]
            if (complete/'cases.jsonl').exists():
                for line in (complete/'cases.jsonl').read_text().splitlines():
                    if line.strip():
                        try:observed.append(json.loads(line))
                        except json.JSONDecodeError:continue
            by_id={row['case_id']:row for row in observed}
            expected_ids={case['case_id'] for case in task['cases']}
            identity_ok=len(by_id)==len(observed) and not set(by_id)-expected_ids and all(row.get('task_id')==task_id and row.get('variant')=='buggy' for row in observed)
            if not identity_ok:
                record['rejection_reasons'].append('worker_result_identity_mismatch');by_id={}
            for case in task['cases']:
                row=by_id.get(case['case_id'],{'case_id':case['case_id'],'split':case['split'],'status':'not_run_worker_incomplete'})
                if row['split']!=case['split']:raise ValueError('Worker input split mismatch')
                normalized.append({**{key:value for key,value in row.items() if key!='expected'},'task_id':task_id,'proposal_id':proposal_id})
            if (complete/'summary.json').exists():record['original_test']=read_json(complete/'summary.json').get('original')
            normalized_path=directory/'normalized_cases.jsonl'
            normalized_path.write_text('\n'.join(json.dumps(row,ensure_ascii=False,allow_nan=False) for row in normalized)+'\n',encoding='utf-8')
            record['cases_path']=str(normalized_path.relative_to(output))
            record['normalized_cases_sha256']=sha(normalized_path)
            record.update(executed=True,execution_status='completed' if len(observed)==len(task['cases']) and identity_ok else 'worker_incomplete',private_attempt_path=str(complete.relative_to(output)))
            if identity_ok:record['y1']=outcome_label(normalized)
        record['tool_status_vector']=[{'case_id':row['case_id'],'status':row['status']} for row in normalized if row['split']=='tool']
        reserved=[row for row in normalized if row['split']=='outcome']
        record['case_completeness']={'assigned':len(normalized),'observed_statuses':sum(row['status'] in OBSERVED for row in normalized),'reserved_assigned':len(reserved),'reserved_observed':sum(row['status'] in OBSERVED for row in reserved),'all_reserved_observed':bool(reserved) and all(row['status'] in OBSERVED for row in reserved)}
        record['status_counts']=dict(collections.Counter(row['status'] for row in normalized))
        return record,normalized
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(one,proposal):proposal for proposal in proposals}
        for future in concurrent.futures.as_completed(futures):
            proposal=futures[future]
            try:results[proposal['source_line']]=future.result()
            except Exception as error:results[proposal['source_line']]=({'source_line':proposal['source_line'],'task_id':proposal.get('task_id'),'proposal_id':proposal.get('proposal_id'),'code_sha256':sha_bytes(proposal['code'].encode()) if isinstance(proposal.get('code'),str) else None,'cases_path':None,'executed':False,'execution_may_have_started':True,'y1':None,'execution_status':'coordinator_error','error_type':type(error).__name__,'tool_status_vector':[]},[])
            write_json(output/'PROGRESS.json',{'completed_proposals':len(results),'assigned_proposals':len(proposals),'elapsed_seconds':time.monotonic()-started})
            print(json.dumps({'completed_proposals':len(results),'assigned_proposals':len(proposals)}),flush=True)
    public=output/'public';public.mkdir(exist_ok=True)
    with (public/'PROPOSAL_RESULTS.jsonl').open('w',encoding='utf-8') as records_file,gzip.open(public/'CASES.jsonl.gz','wt',encoding='utf-8') as cases_file:
        for number in sorted(results):
            record,cases=results[number];records_file.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
            for case in cases:cases_file.write(json.dumps({'source_line':number,'proposal_id':record['proposal_id'],'task_id':record['task_id'],**case},ensure_ascii=False,allow_nan=False)+'\n')
    records=[results[number][0] for number in sorted(results)]
    summary={'assigned_proposals':len(proposals),'retained_proposals':len(records),'executed':sum(row['executed'] for row in records),'y1_true':sum(row['y1'] is True for row in records),'y1_false':sum(row['y1'] is False for row in records),'y1_unknown':sum(row['y1'] is None for row in records),'execution_status_counts':dict(collections.Counter(row['execution_status'] for row in records)),'elapsed_seconds':time.monotonic()-started,'model_calls':0,'network_requests':0,'scope':'Postgeneration evaluation only; reserved outcomes must not be fed back to generators or tool-selection policies.'}
    write_json(public/'SUMMARY.json',summary)
    write_json(public/'RECEIPT.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_configuration_sha256':sha(config_path),'execution_hashes':hash_checks,'proposals_sha256':sha(args.proposals),'reference_manifest_sha256':sha(args.reference_manifest),'output_sha256':{path.name:sha(path) for path in sorted(public.iterdir()) if path.is_file() and path.name!='RECEIPT.json'},'image_id':os.environ.get('PRAXIS_IMAGE_ID')})
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if all(row['execution_status']!='coordinator_error' for row in records) else 2

if __name__=='__main__':raise SystemExit(main())
