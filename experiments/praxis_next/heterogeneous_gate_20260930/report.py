"""Post-audit presentation only; decisions are computed by the frozen audit."""
import csv,gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def main():
    audit=json.loads((HERE/'AUDIT.json').read_text());assert audit['status']=='PASS';rows=json.loads((HERE/'RESULTS.json').read_text())
    flat=[]
    for r in rows:
        x={k:v for k,v in r.items() if not isinstance(v,(list,dict))};x['members']=';'.join(r['members'])
        for stage in ['other_attack','movement','exfiltration']:
            if stage in r:x.update({stage+'_'+k:v for k,v in r[stage].items()})
        flat.append(x)
    with (HERE/'RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=sorted(set().union(*(r.keys() for r in flat))));w.writeheader();w.writerows(flat)
    (HERE/'RESULTS.json.gz').write_bytes(gzip.compress((HERE/'RESULTS.json').read_bytes(),mtime=0))
    def get(ex,set,agg='OR'):return next(r for r in rows if r['execution']==ex and r['set']==set and r['condition']=='clean' and r['budget']==2 and r['aggregator']==agg)
    lines=['# PX-093: heterogeneous gates — results','', '| Hypothesis | Outcome |','|---|---|']+[f'| {h} | {v} |' for h,v in audit['hypotheses'].items()]
    lines+=['','All metrics below are clean budget 2; UNRAVELED is four-class, AIT is the adapted three-class task. Counts refer to flows. The CSV retains all conditions, budgets, mean controls and oracle comparisons.','', '| Source | Set | Exfil warning recall | Exfil misses | Benign false alerts | OR overlap | Additional exfil warnings vs base OR | Additional false alerts vs base OR |','|---|---|---:|---:|---:|---:|---:|---:|']
    for ex in ['UNRAVELED','wilson','harrison','pooled']:
        for name in ['base3','plus_current','plus_lr','A6_full','heterogeneous3','duplicate_control','lr_only','current_only']:
            r=get(ex,name);ov='undefined' if r['overlap_ratio'] is None else f"{r['overlap_ratio']:.6f}"
            lines.append(f"| {ex} | {name} | {r['exfiltration']['warning_recall']*100:.6f}% | {r['exfiltration']['missed']} | {r['false_alerts']} | {ov} | {r['OR_marginal_exfil_warnings']} | {r['OR_marginal_false_alerts']} |")
    lines+=['','Additional warnings count recovered rows, not net gain for non-superset arms such as LR alone. For the full A6 set, every base member is retained, so its additions cannot be offset by lost base warnings. The overlap column describes OR, not the mean gate.','', '## Frozen fixed-denominator workload guard','', '| Source | Full A6 false alerts | Maximum allowed (2 × original mean) | Best constituent exfil recall | Full A6 exfil recall |','|---|---:|---:|---:|---:|']
    for ex in ['UNRAVELED','wilson','harrison','pooled']:
        r=get(ex,'A6_full');lines.append(f"| {ex} | {r['false_alerts']} | {2*r['fixed_base_mean_false_alerts']:.3f} | {r['best_single_warning_recall']*100:.6f}% | {r['exfiltration']['warning_recall']*100:.6f}% |")
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fits={d:json.loads((HERE/f'FIT_{d}.json').read_text()) for d in ['UNRAVELED','AIT']}
    compute={'local_CPU_only':True,'new_fits':2,'new_LightGBM_fits':0,'fit_seconds':{d:f['fit_seconds'] for d,f in fits.items()},'training_rows':{d:f['training_rows'] for d,f in fits.items()},'convergence':{d:f['converged'] for d,f in fits.items()},'cloud_allocations':0,'model_API_calls':0,'test_executions_refitted':False}
    (HERE/'COMPUTE.json').write_text(json.dumps(compute,indent=2)+'\n')
    u=get('UNRAVELED','A6_full');ub=get('UNRAVELED','base3');dup=get('UNRAVELED','duplicate_control')
    findings=['# PX-093 — Plan B decision','',f"H1: **{audit['hypotheses']['H1']}**; H2: **{audit['hypotheses']['H2']}**; H3: **{audit['hypotheses']['H3']}**. The original PX-092 Part C / H3 remains **not supported**; this extension is a separate, later development study.",'','## What was run','','Two new logistic-regression fits with train-only imputation/scaling and fixed parameters, one per source. The existing current-only LightGBM was reused. Eight ensemble sets were evaluated across nine UNRAVELED condition/budget settings and Wilson, Harrison and pooled AIT. Both fits converged; no held-out rows entered training. No cloud or model API was used.','', '## Main comparison','', '| Source | Base-three OR recall | Full heterogeneous OR recall | Base false alerts | Full false alerts | Recovered exfiltration flows | Added false alerts per recovered exfiltration flow |','|---|---:|---:|---:|---:|---:|---:|']
    for ex in ['UNRAVELED','wilson','harrison','pooled']:
        r=get(ex,'A6_full');b=get(ex,'base3');rate=r['OR_added_false_alerts_per_exfil_recovery'];rate='undefined (no recovery)' if rate is None else f'{rate:.3f}'
        findings.append(f"| {ex} | {b['exfiltration']['warning_recall']*100:.6f}% | {r['exfiltration']['warning_recall']*100:.6f}% | {b['false_alerts']} | {r['false_alerts']} | {r['OR_marginal_exfil_warnings']} | {rate} |")
    findings+=['','## Overlap is not a success criterion by itself','',f"The duplicate control leaves UNRAVELED's {ub['false_alerts']} false alerts and {ub['exfiltration']['warning_recall']*100:.6f}% exfiltration warning recall unchanged, yet lowers overlap from {ub['overlap_ratio']:.6f} to {dup['overlap_ratio']:.6f}. It adds no information. The full heterogeneous set's overlap is {u['overlap_ratio']:.6f}; its absolute false-alert count and marginal recovery must be examined separately.",'','## Mechanism and limits','','OR structurally preserves constituent warnings. Mean can erase warnings through competing class scores; a confident benign member is one possible cause, not an absolute veto. A synthetic boundary test also demonstrates mean selecting benign when all members warn on different attack classes. Empirical counts for both cases are retained in RESULTS.csv. These mechanisms alone are not a novel ensemble algorithm.','', 'The heterogeneous members use existing features and shared training observations. They provide algorithm/input differences, not independent campaigns. UNRAVELED and AIT test results had already been examined. AIT retains its adapted three-class/history contract. No analyst outcome, safe-deployment guarantee, universally bounded operational burden or unique superiority over every alternative has been established.','',f"Audit: {audit['checks']:,} checks, {audit['cells']} cells and {audit['result_rows']} result rows. The independent script reproduced every saved gate decision and both LR models' full evaluation probabilities; source hashes, row identities, training separation and per-row costs were checked.",'','## Evidence','','[Full comparison](RESULTS.md) | [Every arm CSV](RESULTS.csv) | [Frozen protocol](PROTOCOL.md) | [Audit and hypothesis components](AUDIT.json) | [Literature and claim corrections](LITERATURE_AND_CLAIMS.md)']
    (HERE/'FINDINGS.md').write_text('\n'.join(findings)+'\n',encoding='utf-8')
    registry=HERE.parent/'REGISTRY.json';d=json.loads(registry.read_text());assert not any(e['id']=='PX-093' for e in d['experiments'])
    d['experiments'].append({'id':'PX-093','directory':HERE.name,'title':'Heterogeneous Warning Gates and False-Alert Accounting','status':'COMPLETE_EXPLORATORY_TWO_FIT_EXTENSION_AUDIT_PASS','protocol':HERE.name+'/PROTOCOL.md','results':HERE.name+'/FINDINGS.md','hypotheses':audit['hypotheses'],'novelty':'UNCONFIRMED','finding':'Heterogeneous extension completed with a fixed original-model workload denominator and duplicate-member control; PX-092 H3 remains failed.'});registry.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    p=HERE.parent/'README.md';p.write_text('> **PX-093 completed:** [Heterogeneous warning-gate extension and Plan B assessment](heterogeneous_gate_20260930/FINDINGS.md). Two new local fits; all ablations and duplicate control retained.\n\n'+p.read_text(encoding='utf-8'),encoding='utf-8')
    print(json.dumps(audit['hypotheses']));print('\n'.join(findings[:19]))
if __name__=='__main__':main()
