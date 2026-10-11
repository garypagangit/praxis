"""Read-only re-audit. Archived command strings are never executed or published."""
import argparse, collections, gzip, hashlib, io, json, pathlib, zipfile
from boundary import design_gate

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(b): return hashlib.sha256(b).hexdigest()
def run(raw_root, replay):
    inputs=[]; raw=[]; errors=[]
    for kind in ('human','ai'):
        mp=raw_root/(kind+'_manifest.json'); mb=mp.read_bytes()
        inputs.append({'path':str(mp),'sha256':sha(mb)})
        for entry in json.loads(mb):
            path=pathlib.Path(entry['local']); b=path.read_bytes()
            ok=sha(b)==entry['sha256'] and len(b)==entry['bytes']
            inputs.append({'path':str(path),'sha256':sha(b),'bytes':len(b),'manifest_match':ok})
            if not ok: errors.append('hash:'+str(path)); continue
            z=zipfile.ZipFile(io.BytesIO(gzip.decompress(b) if b[:2]==b'\x1f\x8b' else b))
            for name in z.namelist():
                if name.startswith('samples/') and name.endswith('.json'):
                    s=json.loads(z.read(name));logs=s.get('store',{}).get('HumanAgentState:logs',{})
                    raw.append({'kind':kind,'has_terminal_input':any(k.endswith('.input') for k in logs),
                      'has_terminal_output':any(k.endswith('.output') for k in logs),
                      'has_terminal_timing':any(k.endswith('.timing') for k in logs),
                      'tool_event_count':sum(e.get('event')=='tool' for e in s.get('events',[]))})
    rb=replay.read_bytes();inputs.append({'path':str(replay),'sha256':sha(rb)})
    rows=json.loads(rb); summaries={}; matched=[]
    for minimum in (1,3,5,10):
        eligible=[r for r in rows if len(r['shell_commands'])>=minimum]
        shared={r['task'] for r in eligible if r['label']==0}&{r['task'] for r in eligible if r['label']==1}
        paired=[r for r in eligible if r['task'] in shared]
        summaries[str(minimum)]={'shared_tasks':len(shared),'human':sum(r['label']==0 for r in paired),
          'ai':sum(r['label']==1 for r in paired),'human_groups':len({r['group'] for r in paired if r['label']==0}),
          'scripted':0,'hybrid_verified':0}
        if minimum==3: matched=paired
    # A deliberately forbidden feature, not a new detector experiment.
    shortcut_correct=sum(('human' if r['has_terminal_input'] else 'ai')==r['kind'] for r in raw)
    view_collisions={}
    for prefix in (1,3,5):
        buckets=collections.defaultdict(set)
        for r in rows:
            if len(r['shell_commands'])>=prefix:
                key=sha(json.dumps(r['shell_commands'][:prefix],ensure_ascii=False).encode())
                buckets[key].add(r['label'])
        view_collisions[str(prefix)]={'distinct_exact_prefixes':len(buckets),'cross_label_exact_prefixes':sum(len(v)>1 for v in buckets.values())}
    records=[{'origin':'H' if r['label']==0 else 'A','runtime_ai':bool(r['label']),
       'offline_ai_assistance':'no' if r['label']==0 else 'unknown',
       'origin_evidence_ref':'published-study-protocol','synthetic_fixture':False,
       'recorder_revision':'human-terminal' if r['label']==0 else 'ai-tool-events',
       'capture_equivalence_verified':False,'prior_inspection_status':'development',
       'task_template':r['task'],'actor_group':r['group'],'environment_group':'InterCode'} for r in matched]
    result={'date':'2026-10-11','integrity_errors':errors,'archive_count':sum('manifest_match' in x for x in inputs),
       'raw_summary':{kind:{'samples':sum(r['kind']==kind for r in raw),
         **{f:sum(bool(r[f]) for r in raw if r['kind']==kind) for f in ('has_terminal_input','has_terminal_output','has_terminal_timing')},
         'samples_with_tool_events':sum(r['tool_event_count']>0 for r in raw if r['kind']==kind),
         'total_tool_events':sum(r['tool_event_count'] for r in raw if r['kind']==kind)} for kind in ('human','ai')},
       'matched_by_minimum_submissions':summaries,'exact_prefix_collision_diagnostic':view_collisions,
       'forbidden_collector_shortcut':{'correct':shortcut_correct,'total':len(raw),'fraction':shortcut_correct/len(raw),
          'rule':'terminal-input key present => human, absent => AI',
          'interpretation':'Descriptive dataset-origin shortcut. Prohibited as an attribution feature; not evidence that normalized command models necessarily use it.'},
       'four_arm_confirmation_gate':design_gate(records),'inputs':inputs,
       'new_genuine_sessions':0,'new_model_fits':0,
       'decision':'PUBLISHED_DATA_USABLE_FOR_DEVELOPMENT_AND_BOUNDED_RELIABILITY_STUDY; FOUR_ARM_CONFIRMATION_NOT_READY'}
    dest=HERE/'results';dest.mkdir(exist_ok=True)
    (dest/'READINESS.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k!='inputs'},indent=2))
    if errors: raise SystemExit('Archive integrity failed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw-root',type=pathlib.Path,default=pathlib.Path('C:/w/px120_lyptus_20261007'))
    p.add_argument('--replay',type=pathlib.Path,default=pathlib.Path('C:/w/operator_signals_20261007/experiments/praxis_next/defense_opportunities_20261007/evidence/FILTERED_REPLAY_INPUT.json'))
    args=p.parse_args();run(args.raw_root,args.replay)
