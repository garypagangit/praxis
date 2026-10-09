"""Read-only data qualification. Source commands are inert strings, never executed."""
import collections
import csv
import gzip
import hashlib
import io
import json
import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
PRIOR = pathlib.Path('C:/w/operator_signals_20261007/experiments/praxis_next')
RAW = pathlib.Path('C:/w/px120_lyptus_20261007')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')

def main():
    provenance = []
    raw_summary = collections.Counter()
    raw_rows = []
    for kind in ('human', 'ai'):
        manifest_path = RAW/(kind+'_manifest.json')
        manifest_bytes = manifest_path.read_bytes()
        provenance.append({'path':str(manifest_path), 'sha256':digest(manifest_bytes)})
        for entry in json.loads(manifest_bytes):
            p = pathlib.Path(entry['local'])
            item = {'kind':kind, 'source':entry['source'], 'local':str(p)}
            try:
                data = p.read_bytes()
                item.update(bytes=len(data), sha256=digest(data))
                item['hash_matches_manifest'] = item['sha256'] == entry['sha256']
                item['bytes_match_manifest'] = len(data) == entry['bytes']
                z = zipfile.ZipFile(io.BytesIO(gzip.decompress(data) if data[:2]==b'\x1f\x8b' else data))
                samples = []
                for name in z.namelist():
                    if not (name.startswith('samples/') and name.endswith('.json')):
                        continue
                    s = json.loads(z.read(name))
                    logs = s.get('store', {}).get('HumanAgentState:logs', {})
                    tools = [e for e in s.get('events', []) if e.get('event')=='tool']
                    samples.append({'id':str(s['id']), 'terminal_input':any(k.endswith('.input') for k in logs),
                        'terminal_output':any(k.endswith('.output') for k in logs),
                        'terminal_timing':any(k.endswith('.timing') for k in logs),
                        'tool_events':len(tools), 'timestamped_tool_events':sum(bool(e.get('timestamp')) for e in tools)})
                item['samples'] = samples
                raw_summary[kind+'_archives'] += 1
                raw_summary[kind+'_samples'] += len(samples)
                raw_summary[kind+'_hash_matches'] += item['hash_matches_manifest']
                for field in ('terminal_input','terminal_output','terminal_timing'):
                    raw_summary[kind+'_'+field+'_samples'] += sum(s[field] for s in samples)
                raw_summary[kind+'_tool_events'] += sum(s['tool_events'] for s in samples)
                raw_summary[kind+'_timestamped_tool_events'] += sum(s['timestamped_tool_events'] for s in samples)
            except Exception as exc:
                item['error'] = type(exc).__name__+': '+str(exc)
            raw_rows.append(item)
    write('RAW_PROVENANCE.json', {'summary':dict(raw_summary), 'manifests':provenance, 'archives':raw_rows})
    prior = PRIOR/'defense_opportunities_20261007/evidence'
    cohorts = {}
    for filename in ('REPLAY_INPUT.json', 'FILTERED_REPLAY_INPUT.json'):
        data = (prior/filename).read_bytes()
        rows = json.loads(data)
        outcome = {'source':str(prior/filename), 'sha256':digest(data), 'thresholds':{}}
        for minimum in (1,3,10):
            selected = [r for r in rows if len(r['shell_commands'])>=minimum]
            tasks = {label:{r['task'] for r in selected if r['label']==label} for label in (0,1)}
            shared = tasks[0]&tasks[1]
            result = {'shared_tasks':len(shared), 'human_only_tasks':len(tasks[0]-tasks[1]),
                'ai_only_tasks':len(tasks[1]-tasks[0]), 'scripted_control_sessions':0, 'labels':{}}
            for label in (0,1):
                all_rows = [r for r in rows if r['label']==label]
                eligible = [r for r in selected if r['label']==label]
                matched = [r for r in eligible if r['task'] in shared]
                result['labels'][str(label)] = {'all_rows':len(all_rows), 'eligible_rows':len(eligible),
                    'eligible_tasks':len(tasks[label]), 'matched_rows':len(matched),
                    'matched_groups':len({r['group'] for r in matched}),
                    'matched_families':dict(collections.Counter(r['family'] for r in matched))}
            signatures = collections.defaultdict(list)
            for r in selected:
                # Recompute: inherited fingerprint fields predate command filtering.
                fp = digest(json.dumps(r['shell_commands'][:10],ensure_ascii=False).encode())
                signatures[fp].append(r)
            result['duplicate_prefix_groups'] = sum(len(rs)>1 for rs in signatures.values())
            result['cross_label_duplicate_prefix_groups'] = sum(len({r['label'] for r in rs})>1 for rs in signatures.values())
            outcome['thresholds'][str(minimum)] = result
            if filename=='FILTERED_REPLAY_INPUT.json' and minimum==3:
                manifest = []
                for r in selected:
                    if r['task'] not in shared:
                        continue
                    manifest.append({'id':r['id'],'task':r['task'],'operator_group':r['group'],
                        'label':'human' if r['label']==0 else 'ai','family':r['family'],
                        'submissions':len(r['shell_commands']),
                        'prefix10_sha256':digest(json.dumps(r['shell_commands'][:10],ensure_ascii=False).encode()),
                        'status':'previously_inspected_development_only'})
                with (HERE/'MATCHED_DEVELOPMENT_COHORT.csv').open('w',newline='',encoding='utf-8') as f:
                    writer=csv.DictWriter(f,fieldnames=list(manifest[0]));writer.writeheader();writer.writerows(manifest)
                task_counts=[]
                for task in sorted(shared):
                    rs=[r for r in manifest if r['task']==task]
                    task_counts.append({'task':task,'human':sum(r['label']=='human' for r in rs),
                        'ai':sum(r['label']=='ai' for r in rs),'ai_families':sorted({r['family'] for r in rs if r['label']=='ai'})})
                write('MATCHED_TASK_COUNTS.json', task_counts)
        cohorts[filename] = outcome
    write('COHORT_AUDIT.json',cohorts)
    failures=[r for r in raw_rows if r.get('error') or not r.get('hash_matches_manifest') or not r.get('bytes_match_manifest')]
    # These checks establish artifact integrity, not origin-label validity.
    validation={'raw_archives_checked':len(raw_rows),'raw_integrity_failures':len(failures),
        'script_sha256':digest(pathlib.Path(__file__).read_bytes()),
        'scope':'Existing extraction inventory and raw archive metadata; no independent terminal reconstruction or model fitting.',
        'qualification':'HOLD: no scripted control arm, incompatible native observation layers, previously inspected development data.'}
    write('QUALIFICATION_CHECKS.json',validation)
    print(json.dumps({'raw':dict(raw_summary),'filtered_min3':cohorts['FILTERED_REPLAY_INPUT.json']['thresholds']['3'],'validation':validation},indent=2))

if __name__=='__main__':
    main()
