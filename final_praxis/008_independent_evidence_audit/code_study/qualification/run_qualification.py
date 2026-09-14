"""Credential-free coordinator inside the prescribed Linux Docker isolation."""
from __future__ import annotations
import argparse
import collections
import concurrent.futures
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import time

from worker import assert_isolation

HERE=Path(__file__).resolve().parent
VARIANTS=('reference','canonical','buggy')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
def read_json(path):return json.loads(path.read_text(encoding='utf-8'))
def load_rows(path):
    rows=[]
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip():
                try:rows.append(json.loads(line))
                except json.JSONDecodeError:continue
    return rows

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tasks-file',type=Path,default=Path('/data/tasks.jsonl'))
    parser.add_argument('--bundle-manifest',type=Path,default=Path('/manifest.json'))
    parser.add_argument('--output-dir',type=Path,default=Path('/output'))
    parser.add_argument('--mode',choices=['pilot','full'],required=True)
    parser.add_argument('--workers',type=int,default=3)
    args=parser.parse_args();assert_isolation()
    if not 1<=args.workers<=3:raise ValueError('One to three task workers allowed')
    manifest=read_json(args.bundle_manifest)
    if sha(args.tasks_file)!=manifest['files']['data/tasks.jsonl']:raise ValueError('Task payload hash mismatch')
    checked={}
    for relative,digest in manifest['files'].items():
        if relative.startswith('qualification/'):
            path=HERE/relative.split('/',1)[1]
            if not path.exists() or sha(path)!=digest:raise ValueError('Qualification file hash mismatch:'+relative)
            checked[relative]=digest
    tasks=[json.loads(line) for line in args.tasks_file.read_text().splitlines() if line.strip()]
    if len(tasks)!=164 or {row['task_id'] for row in tasks}!={f'Python/{i}' for i in range(164)}:raise ValueError('Exact164-task cohort required')
    splits=read_json(HERE/'SPLIT_MANIFEST.json')
    selected_ids=set(splits['pilot_ids'] if args.mode=='pilot' else splits['task_order'])
    selected=[row for row in tasks if row['task_id'] in selected_ids]
    output=args.output_dir;output.mkdir(parents=True,exist_ok=True)
    config={'mode':args.mode,'workers':args.workers,'bundle_manifest_sha256':sha(args.bundle_manifest),'tasks_sha256':sha(args.tasks_file),'qualification_hashes':checked,'python':sys.version,'platform':platform.platform(),'image_id':os.environ.get('PRAXIS_IMAGE_ID'),'network':'none','uid':os.getuid(),'seed':splits['seed'],'selected_ids':sorted(selected_ids),'program_execution_location':'nonroot network-none Docker only'}
    config_path=output/'RUN_CONFIGURATION.json'
    if config_path.exists() and read_json(config_path)!=config:raise ValueError('Existing output directory belongs to a different frozen configuration')
    write_json(config_path,config)
    started=time.monotonic();lock=threading.Lock();finished=[]
    def one_task(task):
        task_number=task['task_id'].split('/')[1];directory=output/'private'/('task_'+task_number);directory.mkdir(parents=True,exist_ok=True)
        task_path=directory/'task.json';write_json(task_path,task)
        variants={};reference_path=None
        for variant in VARIANTS:
            base=directory/variant;base.mkdir(exist_ok=True)
            attempts=sorted(path for path in base.glob('attempt_*') if path.is_dir())
            complete=None
            for attempt in attempts:
                if (attempt/'summary.json').exists() and (attempt/'cases.jsonl').exists():
                    summary=read_json(attempt/'summary.json')
                    if summary.get('code_sha256')==hashlib.sha256(task['programs'][variant].encode()).hexdigest() and summary.get('assigned_cases')==len(task['cases']):complete=attempt
            if complete is None:
                attempt=base/f'attempt_{len(attempts)+1:03d}';attempt.mkdir()
                command=[sys.executable,str(HERE/'worker.py'),'--task-file',str(task_path),'--variant',variant,'--output-dir',str(attempt)]
                if variant!='reference':command+=['--expected-file',str(reference_path)]
                try:
                    with (attempt/'process.log').open('wb') as log:
                        process=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=135)
                    exit_code=process.returncode;process_state='exited'
                except subprocess.TimeoutExpired:exit_code=None;process_state='wall_timeout'
                write_json(attempt/'PROCESS_RECEIPT.json',{'command':command,'exit_code':exit_code,'state':process_state,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
                complete=attempt
            rows=load_rows(complete/'cases.jsonl');by_id={row['case_id']:row for row in rows}
            if len(by_id)!=len(rows):raise ValueError('Duplicate case IDs in worker results')
            normalized=[]
            for index,case in enumerate(task['cases']):
                row=by_id.get(case['case_id'])
                if row is None:row={'task_id':task['task_id'],'variant':variant,'case_index':index,'case_id':case['case_id'],'split':case['split'],'memberships':case['memberships'],'status':'not_run_worker_incomplete'}
                normalized.append(row)
            if set(by_id)-{case['case_id'] for case in task['cases']}:raise ValueError('Unexpected worker case ID')
            summary=read_json(complete/'summary.json') if (complete/'summary.json').exists() else {'original':None,'worker_incomplete':True}
            variants[variant]={'rows':normalized,'summary':summary,'attempt_path':str(complete.relative_to(output))}
            if variant=='reference':
                reference_path=directory/'reference_complete.jsonl'
                reference_path.write_text('\n'.join(json.dumps(row,ensure_ascii=False,allow_nan=False) for row in normalized)+'\n',encoding='utf-8')
        with lock:
            finished.append(task['task_id'])
            write_json(output/'PROGRESS.json',{'mode':args.mode,'completed_tasks':len(finished),'assigned_tasks':len(selected),'completed_ids':list(finished),'elapsed_seconds':time.monotonic()-started})
            print(json.dumps({'completed_tasks':len(finished),'assigned_tasks':len(selected),'last_task':task['task_id']}),flush=True)
        return task,variants
    results={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(one_task,task):task['task_id'] for task in selected}
        for future in concurrent.futures.as_completed(futures):
            identifier=futures[future]
            try:results[identifier]=future.result()[1]
            except Exception as error:results[identifier]={'coordinator_error':type(error).__name__}
    public=output/'public';public.mkdir(exist_ok=True);task_results=[]
    with gzip.open(public/'CASES.jsonl.gz','wt',encoding='utf-8') as cases_file:
        for task in tasks:
            identifier=task['task_id'];result=results.get(identifier)
            record={'task_id':identifier,'split':task['split'],'identity_eligible':task['identity_eligible'],'assigned':identifier in selected_ids,'eligible':False,'exclusion_reasons':[],'variants':{}}
            if result is None:record['exclusion_reasons'].append('not_assigned_pilot')
            elif 'coordinator_error' in result:record['exclusion_reasons'].append('coordinator_error:'+result['coordinator_error'])
            else:
                for variant,data in result.items():
                    rows=data['rows'];by_split={side:[row for row in rows if row['split']==side] for side in ('tool','outcome')}
                    record['variants'][variant]={'status_counts':dict(collections.Counter(row['status'] for row in rows)),'by_split':{side:dict(collections.Counter(row['status'] for row in part)) for side,part in by_split.items()},'original':data['summary'].get('original'),'attempt_path':data['attempt_path']}
                    for row in rows:
                        sanitized={key:value for key,value in row.items() if key!='expected'}
                        cases_file.write(json.dumps(sanitized,ensure_ascii=False,allow_nan=False)+'\n')
                ref=record['variants']['reference'];canon=record['variants']['canonical'];bug=record['variants']['buggy']
                outcome_total=sum(ref['by_split']['outcome'].values())
                reasons=record['exclusion_reasons']
                if not task['identity_eligible']:reasons.append('source_identity_or_signature_mismatch')
                if outcome_total==0:reasons.append('empty_reserved_outcomes')
                if ref['by_split']['outcome'].get('pass',0)!=outcome_total:reasons.append('reference_reserved_incomplete_or_error')
                if canon['by_split']['outcome'].get('pass',0)!=outcome_total:reasons.append('canonical_reserved_not_all_pass')
                if not canon['original'] or canon['original']['status']!='pass':reasons.append('canonical_original_suite_not_pass')
                demonstrated_fail=sum(bug['by_split']['outcome'].get(status,0) for status in ('fail','exception','timeout','program_load_error'))
                if demonstrated_fail==0:reasons.append('buggy_no_demonstrated_reserved_failure')
                record['eligible']=not reasons
            task_results.append(record)
    eligible=[row['task_id'] for row in task_results if row['eligible']]
    heldout=[row['task_id'] for row in task_results if row['eligible'] and row['split']=='heldout']
    assigned=[row for row in task_results if row['assigned']]
    all_completed=all(row['variants'] for row in assigned)
    hypothesis_pass=args.mode=='full' and all_completed and len(eligible)>=100 and len(heldout)>=60
    summary={'mode':args.mode,'all164_tasks_retained':len(task_results)==164,'assigned_tasks':len(assigned),'tasks_with_worker_results':sum(bool(row['variants']) for row in assigned),'eligible_pairs':len(eligible),'eligible_heldout_pairs':len(heldout),'eligible_ids':eligible,'eligible_heldout_ids':heldout,'qualification_hypothesis_evaluated':args.mode=='full','qualification_hypothesis_pass':hypothesis_pass if args.mode=='full' else None,'decision':'QUALIFIED_FOR_SEPARATELY_FROZEN_POLICY_STUDY' if hypothesis_pass else 'PILOT_COMPLETE_REVIEW_BEFORE_FULL' if args.mode=='pilot' and all_completed else 'HOLD_QUALIFICATION_THRESHOLD_OR_EXECUTION_FAILURE','exclusion_counts':dict(collections.Counter(reason for row in assigned for reason in row['exclusion_reasons'])),'elapsed_seconds':time.monotonic()-started,'model_calls':0,'network_requests':0,'policy_results_used_for_selection':False,'limitations':['Public benchmark training exposure is unresolved.','Qualification is not a novel intervention result.','Input fingerprints remove structural duplicates, not semantic equivalents.','Budget-censored buggy cases do not count as demonstrated failures.']}
    write_json(public/'TASK_RESULTS.json',{'tasks':task_results})
    write_json(public/'SUMMARY.json',summary)
    write_json(public/'RECEIPT.json',{'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'configuration_sha256':sha(config_path),'bundle_manifest_sha256':sha(args.bundle_manifest),'output_sha256':{path.name:sha(path) for path in sorted(public.iterdir()) if path.is_file() and path.name!='RECEIPT.json'},'image_id':config['image_id'],'qualification_hashes':checked,'private_results_published':False})
    print(json.dumps(summary,indent=2),flush=True)
    return 0 if all_completed else 2

if __name__=='__main__':raise SystemExit(main())
