"""Exposed historical diagnosis only. Never executes a generated command."""
import csv,json,sys,hashlib,collections,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=Path('C:/w/px116_20261005')
OLD=Path('C:/Users/garyp/OneDrive/Documents/codex/runs')
sys.path.insert(0,str(OUT/'historical/cloud_jobs/px050y_packmonitor_blackbox_20260731'))
sys.path.insert(0,str(OUT/'historical/cloud_jobs/px067_noop_canonicalization_20260731'))
import run_px050y_blackbox as common
import run_px067_blackbox as repair
with (OLD/'px050y/blackbox-confirmatory/sanitized_action_scores.csv').open(encoding='utf-8-sig',newline='') as f: scored=list(csv.DictReader(f))
review=[r for r in scored if r['hardened_decision']=='review']
lookup={}
for line in (OLD/'px050y/blackbox-confirmatory/private_raw_model_outputs.jsonl').read_text(encoding='utf-8').splitlines():
    row=json.loads(line)
    for command in common.extract_install_commands(row['output_text']):
        lookup[(row['model_id'],row['task_id'],hashlib.sha256(command.encode()).hexdigest())]=command
resolved=[]
for r in review:
    key=(r['model_id'],r['task_id'],r['command_sha256']);command=lookup[key]
    parsed=repair.parse_command(command)
    decision=repair.hardened_decision(parsed,set())
    resolved.append({'command_sha256':r['command_sha256'],'command':command,'original_reason':r['reason'],
        'repaired_decision':decision[0],'repaired_reason':decision[2]})
(OUT/'historical_review_commands.private.json').write_text(json.dumps(resolved,indent=2),encoding='utf-8')
disagreements=[json.loads(x) for x in (OLD/'px069/gate-blind-audit/disagreements.private.jsonl').read_text().splitlines()]
exceptions=collections.Counter(z['exception_class'] for r in disagreements for z in r.get('internal_failure_records',[]))
sys.path.insert(0,str(OUT/'historical/scripts'))
import px069_independent_adjudicator as a
import bashlex
reproduced=[]
for r in disagreements:
    regions={hashlib.sha256(str(z['text']).encode()).hexdigest():str(z['text']) for z in a.markdown_regions(r['response_text'])}
    for failure in r.get('internal_failure_records',[]):
        if failure['region_sha256'] not in regions:
            reproduced.append({'old':failure['exception_class'],'now':'REGION_HASH_NOT_RECONSTRUCTED'})
            continue
        text=regions[failure['region_sha256']]
        assert hashlib.sha256(text.encode()).hexdigest()==failure['region_sha256']
        try:
            bashlex.parse(text)
            reproduced.append({'old':failure['exception_class'],'now':'parsed'})
        except Exception as exc:
            # Store class/message, not the original command or package names.
            reproduced.append({'old':failure['exception_class'],'now':type(exc).__name__,'message':str(exc)[:180]})
summary={'status':'EXPOSED_DIAGNOSTIC_NOT_NEW_EFFICACY','px050y_review_actions':len(review),
 'matched_original_command_hashes':len(resolved),'unique_review_commands':len({r['command_sha256'] for r in resolved}),
 'repair_decisions':dict(collections.Counter(r['repaired_decision'] for r in resolved)),
 'repair_reasons':dict(collections.Counter(r['repaired_reason'] for r in resolved)),
 'px069_review_items':len(disagreements),'old_exception_regions':dict(exceptions),
 'reproduced_exception_regions':dict(collections.Counter(r['now'] for r in reproduced)),
 'attribute_error_messages':dict(collections.Counter(r.get('message','') for r in reproduced if r['now']=='AttributeError')),
 'scope':'No labels resolved by fiat, no gate efficacy rescored, no generated commands executed. Old outcomes retained.'}
(HERE/'HISTORICAL_DIAGNOSTIC.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
(OUT/'audit_exception_replay.json').write_text(json.dumps(reproduced,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
