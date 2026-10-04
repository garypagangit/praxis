"""Refresh local run report and scoped registry entries; optional bounded watcher."""
import json, sys, time, datetime, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
OUT=Path('C:/w/assurance_batch_20261004')
TITLES={112:'Deferred explanation cost and sampling assumptions',
        113:'Explanation stability as a model-release gate',
        114:'Verification claims checked against tool receipts',
        115:'SHAP narrative consistency versus deterministic rendering'}
def refresh():
    contextfile=HERE/'RUN_CONTEXT.json'
    context=json.loads(contextfile.read_text()) if contextfile.exists() else {}
    data_dir=Path(context.get('data_dir',str(OUT)))
    registry=HERE.parent/'REGISTRY.json'; reg=json.loads(registry.read_text(encoding='utf-8-sig'))
    entries={r['id']:r for r in reg['experiments']}
    lines=['ASSURANCE FEASIBILITY BATCH: PX-112 THROUGH PX-115',
           'Updated UTC: '+datetime.datetime.now(datetime.timezone.utc).isoformat(),
           context.get('compute_note','AWS/API spending: $0. Local CPU and Ollama only.'),
           'Broad novelty is NOT established for any of the four ideas.',
           'The protocol was frozen before results. No thresholds were tuned to outcomes.','']
    complete=0
    for n,title in TITLES.items():
        ident=f'PX-{n}'; file=HERE/f'PX{n}_RESULTS.json'
        entry=entries.get(ident,{'id':ident,'title':title,'directory':HERE.name,'protocol':HERE.name+'/PROTOCOL.txt'})
        if file.exists():
            r=json.loads(file.read_text()); complete+=1
            if n==112:
                finding=(f'200 evaluation rows. Eager batch {r["eager_seconds"]*1000:.2f} ms; '
                    'single-row on-demand scenarios (requests: milliseconds): '+
                    ', '.join(f'{z["requests"]}: {z["seconds"]*1000:.2f}' for z in r['lazy'])+
                    f'. Exact replay in all cases. Input/probability JSON {r["base_records_bytes"]} bytes; '
                    f'with contributions {r["records_with_phi_bytes"]} bytes. Lazy is not always cheaper. '
                    'One timing per condition; no deployment-cost or Article86 compliance claim.')
            elif n==113:
                finding=('Three chronological releases: performance gate accepted all; combined stability gate accepted '+
                    str(sum(c['gate_PE'] for c in r['cycles']))+'. Evaluation accuracy changes: '+
                    ', '.join(f'{c["eval_change_pp"]:+.2f} pp' for c in r['cycles'])+
                    '. Stability rejected both beneficial updates. No release crossed the frozen >1 pp harm threshold. '
                    'No evidence the explanation gate improves release decisions; only three dependent cycles.')
            elif n==114:
                finding=(f'{r["generated"]} answers; {r["malformed"]} malformed; '
                    f'{r["unsupported_verification_claims"]} unsupported verified claims across '
                    f'{r["unsupported_unique_targets"]} targets. Headroom passed: {r["headroom_passed"]}. '
                    f'Gate accepted {r["gate_accepted"]}. '+r['status']+
                    '. Snapshot-backed structured task, not deployed-agent prevalence. Direct prior art exists.')
                if 'comparison' in r: finding+=' Comparison: '+json.dumps(r['comparison'])
            else:
                finding=(f'{r["generated"]} generated explanations; {r["sidecar_pass"]} exact top3/sign/order passes; '
                    f'{r["sidecar_fail"]} failures. Deterministic templates consistent on {r["template_consistent"]}. '
                    'Injected wrong feature/sign/order accepted: '+str([r['injections'][k] for k in ['wrong_feature_accepted','wrong_sign_accepted','wrong_order_accepted']])+
                    f'; correct-sidecar/contradictory-prose accepted {r["injections"]["contradictory_prose_accepted"]}/32. '
                    'Unrestricted prose semantics NOT CERTIFIED; no causal, legal or comprehension claim.')
            entry.update(status='COMPLETE_FEASIBILITY_NOVELTY_UNESTABLISHED',results=HERE.name+'/'+file.name,finding=finding)
        else:
            log=data_dir/('verification_answers.jsonl' if n==114 else 'narrative_answers.jsonl')
            done=len(log.read_text(encoding='utf-8').splitlines()) if log.exists() else 0
            finding=f'Qwen2.5:3b pilot on {context.get("backend","local CPU")}; {done} answers collected locally. Results pending; no efficacy finding.'
            entry.update(status='RUNNING_AWS_FEASIBILITY' if context else 'RUNNING_LOCAL_FEASIBILITY',finding=finding)
        if ident not in entries: reg['experiments'].append(entry)
        lines.extend([ident+' - '+title,entry['status'],finding,''])
    lines += ['DATA FIT',
        'UCI522 South German Credit: 1000 actual historical observations, corrected coding; no real AI decisions, requests, chronology or costs.',
        'OpenML151 Electricity: 45312 chronological measurements, published normalized benchmark; contemporaneous direction classification, not forecasting or APT.',
        'PyPI: 20 read-only snapshots, ten real package names and ten declared nonexistent controls. No installs or registrations.',
        'Neither corrected German Credit nor model-generated text supplies a new independent APT replication.','',
        'DECISION',
        'Do not promote these as four novel doctoral contributions. PX112 is an engineering cost/replay study; PX113 currently fails to show gate benefit.',
        'PX114/115 require actual generated results and stronger comparisons before a contribution claim. Generic tool-receipt gates and SHAP narrative audits already exist.',
        'A constrained reason-code renderer may provide a limited, testable consistency guarantee; that is narrower than verifying arbitrary prose or satisfying Article86.',
        'See ASSURANCE_PRIOR_ART.txt and NARRATIVE_PRIOR_ART.txt for closest papers and exclusions.','',
        'EVIDENCE',str(data_dir),'Frozen protocol: PROTOCOL.txt / FREEZE.json; AWS amendment: CLOUD_PROTOCOL.txt / CLOUD_FREEZE.json',
        'Numeric replay audit: NUMERIC_AUDIT.json. Language raw records remain outside git; outputs preserve every completion and error.']
    registry.write_text(json.dumps(reg,indent=2)+'\n',encoding='utf-8')
    (HERE/'FINDINGS.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    manifest={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(OUT.iterdir())+(list(data_dir.iterdir()) if data_dir!=OUT and data_dir.exists() else []) if p.is_file()}
    (HERE/'EVIDENCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f'{complete}/4 studies have results',flush=True)
    return complete==4
if __name__=='__main__':
    if '--watch' in sys.argv:
        deadline=time.monotonic()+6*3600
        while time.monotonic()<deadline:
            if refresh(): break
            time.sleep(60)
    else: refresh()
