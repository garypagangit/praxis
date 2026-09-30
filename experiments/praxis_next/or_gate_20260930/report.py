"""Tables and hypothesis decisions; interpretation generated only after audit."""
import csv,gzip,json
import numpy as np
from common import HERE,save,sha

def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def main():
    assert (HERE/'FREEZE.json').exists();audit=json.loads((HERE/'AUDIT.json').read_text());assert audit['status']=='PASS'
    parts={p:json.loads((HERE/p/'GROUPS.json').read_text()) for p in ['partA','partB','partC']};allrows=sum(parts.values(),[])
    def find(part,cell,agg='OR'):return next(r for r in parts[part] if r['cell']==cell and r['aggregator']==agg)
    def wr(r):return r['exfiltration']['warning_recall']
    a=find('partA','A1_roles_clean_b2');h2=wr(a)>=.95 and a['false_alerts']<=2*a['sum_single_false_alerts']/3
    h3parts=[]
    for ex in ['wilson','harrison','pooled']:
        r=find('partC','C1_history_'+ex);h3parts.append({'execution':ex,'OR_warning_recall':wr(r),'best_single_warning_recall':r['best_single_exfiltration_warning_recall'],'strict_improvement':wr(r)>r['best_single_exfiltration_warning_recall'],'overlap_ratio':r['overlap_ratio'],'overlap_pass':r['overlap_ratio'] is not None and r['overlap_ratio']<.75})
    h3=all(x['strict_improvement'] for x in h3parts) and all(x['overlap_pass'] for x in h3parts[:2])
    h4parts=[]
    for cond in ['clean','delayed_unavailable','wrong_host_history']:
        for b in [1,2,3]:
            rs=[find('partB',f'B_n{n}_{cond}_b{b}') for n in [1,2,3,5,7,10]];vals=[wr(r) for r in rs];ov=[r['overlap_ratio'] for r in rs]
            h4parts.append({'condition':cond,'budget':b,'nondecreasing_recall':all(y>=x for x,y in zip(vals,vals[1:])),'gain_5_to_10_pp':100*(vals[-1]-vals[3]),'gain_under_1pp':vals[-1]-vals[3]<.01,'overlap_strictly_decreasing':all(x is not None and y is not None and y<x for x,y in zip(ov,ov[1:]))})
    primary=h4parts[1];h4=all(primary[k] for k in ['nondecreasing_recall','gain_under_1pp','overlap_strictly_decreasing'])
    h5parts=[]
    for b in [1,2,3]:
        clean=wr(find('partA',f'A1_roles_clean_b{b}'))
        for cond in ['delayed_unavailable','wrong_host_history']:
            r=find('partA',f'A1_roles_{cond}_b{b}');h5parts.append({'condition':cond,'budget':b,'clean_recall':clean,'adverse_recall':wr(r),'retained_fraction':wr(r)/clean if clean else None,'pass':wr(r)>=.9*clean})
    h5=all(r['pass'] for r in h5parts if r['budget']==2)
    triggers=[]
    for r in allrows:
        if r['aggregator']!='OR':continue
        base=r['best_single_exfiltration_warning_recall'];gain=wr(r)-base
        if gain>.1:
            m=find(r['part'],r['cell'],'MEAN');triggers.append({'part':r['part'],'cell':r['cell'],'or_gain_pp':gain*100,'mean_gain_pp':100*(wr(m)-base),'pass':wr(m)-base<=.02,'reference_only':r['reference_only']})
    status={'H1':'SUPPORTED_BY_CONSTRUCTION','H2':'SUPPORTED_KNOWN_RESULT' if h2 else 'NOT_SUPPORTED','H3':'SUPPORTED' if h3 else 'NOT_SUPPORTED','H4':'SUPPORTED' if h4 else 'PARTIALLY_SUPPORTED' if primary['nondecreasing_recall'] else 'NOT_SUPPORTED','H5':'SUPPORTED' if h5 else 'PARTIALLY_SUPPORTED' if any(r['pass'] for r in h5parts if r['budget']==2) else 'NOT_SUPPORTED','H6':'VACUOUS_NO_QUALIFYING_CELL' if not triggers else 'SUPPORTED' if all(r['pass'] for r in triggers) else 'NOT_SUPPORTED'}
    details={'status':status,'H2':{'OR_recall':wr(a),'false_alerts':a['false_alerts'],'mean_single_false_alerts':a['sum_single_false_alerts']/3},'H3':h3parts,'H4':h4parts,'H5':h5parts,'H6':triggers,'primary_scope':'H4 clean budget 2; H5 budget 2; secondary strata retained.'}
    save(HERE/'HYPOTHESES.json',details)
    for part,rows in parts.items():
        flat=[]
        for r in rows:
            q={k:r[k] for k in ['cell','aggregator','execution','condition','budget','model_count','subset_sensitivity','reference_only','n','macro_f1','false_alerts','benign_fpr','overlap_ratio','mean_evidence_cost','max_evidence_cost','nominal_member_evaluations','best_single_exfiltration_warning_recall']};q['members']=';'.join(f"{m['expert']}:{m['seed']}" for m in r['members'])
            for stage in ['other_attack','movement','exfiltration']:
                if stage in r:q.update({stage+'_'+k:v for k,v in r[stage].items()})
            for name,v in r['recovered_against'].items():q[name+'_recovered']=v['recovered'];q[name+'_lost']=v['lost']
            flat.append(q)
        csvwrite(HERE/part/'RESULTS.csv',flat)
        if part=='partB':
            csvwrite(HERE/part/'CURVE.csv',[r for r in flat if not r['subset_sensitivity'] and r['aggregator'] in ['OR','MEAN']])
            csvwrite(HERE/part/'SUBSETS_3.csv',[r for r in flat if r['subset_sensitivity'] and r['aggregator'] in ['OR','MEAN']])
        relevant={'partA':['H1','H2','H5','H6'],'partB':['H1','H4','H6'],'partC':['H1','H3','H6']}[part]
        lines=['| Hypothesis | Status |','|---|---|']+[f'| {h} | {status[h]} |' for h in relevant]
        lines+=['','| Cell | Gate | Exfil warning recall (%) | Exfil exact recall (%) | Macro-F1 | Benign FA | Overlap | Mean evidence cost |','|---|---|---:|---:|---:|---:|---:|---:|']
        for r in rows:
            ov='undefined' if r['overlap_ratio'] is None else f"{r['overlap_ratio']:.6f}"
            lines.append(f"| {r['cell']} | {r['aggregator']} | {wr(r)*100:.6f} | {r['exfiltration']['exact_recall']*100:.6f} | {r['macro_f1']:.6f} | {r['false_alerts']} | {ov} | {r['mean_evidence_cost']:.6f} |")
        (HERE/part/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        raw=(HERE/part/'GROUPS.json').read_bytes();(HERE/part/'GROUPS.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    triples=[r for r in parts['partB'] if r['subset_sensitivity'] and r['aggregator']=='OR'];dist={}
    for field,vals in [('warning_recall',[wr(r) for r in triples]),('false_alerts',[r['false_alerts'] for r in triples])]:dist[field]={'min':float(min(vals)),'median':float(np.median(vals)),'max':float(max(vals))}
    dist['original_triple']={'warning_recall':wr(a),'false_alerts':a['false_alerts'],'triples_with_recall_at_most_original':sum(wr(r)<=wr(a) for r in triples),'total':120}
    save(HERE/'partB/SUBSET_SUMMARY.json',dist)
    scope=(HERE/'PROTOCOL.md').read_text(encoding='utf-8').split('## 7. Scope statements to carry into FINDINGS.md verbatim')[1].split('## 8.')[0].strip()
    intro='; '.join(f'{k}: **{v}**' for k,v in status.items())+'. H1 is structural; H2 repeats an already observed result. H4 and H5 primary decisions use the prespecified primary slice, with all secondary outcomes retained.'
    lines=['# PX-092 findings','',intro,'','## Clean seed-count curve','','| Seeds | OR exfil warning recall | Mean exfil warning recall | OR false alerts | Mean false alerts | OR overlap |','|---:|---:|---:|---:|---:|---:|']
    for n in [1,2,3,5,7,10]:
        r=find('partB',f'B_n{n}_clean_b2');m=find('partB',f'B_n{n}_clean_b2','MEAN');lines.append(f"| {n} | {wr(r)*100:.3f}% | {wr(m)*100:.3f}% | {r['false_alerts']} | {m['false_alerts']} | {r['overlap_ratio']:.4f} |")
    lines+=['','## Adapted AIT execution validation','','| Execution | OR exfil warning recall | Best single seed | Overlap | Strict recall improvement |','|---|---:|---:|---:|---|']
    for r in h3parts:lines.append(f"| {r['execution']} | {r['OR_warning_recall']*100:.6f}% | {r['best_single_warning_recall']*100:.6f}% | {r['overlap_ratio']} | {r['strict_improvement']} |")
    lines+=['','## Adversity','','| Budget | Condition | Clean recall | Adverse recall | Fraction retained | Pass |','|---:|---|---:|---:|---:|---|']
    for r in h5parts:lines.append(f"| {r['budget']} | {r['condition']} | {r['clean_recall']*100:.3f}% | {r['adverse_recall']*100:.3f}% | {r['retained_fraction']:.4f} | {r['pass']} |")
    lines+=['','## Interpretation','','OR retention guarantees that combining the same warning decisions cannot remove a constituent warning. It does not guarantee extra attack coverage, a small false-alert burden, or useful independence among seeds. The empirical parts of H3 and H4 test those additional claims.', '',f"The gain from five to ten seeds is {primary['gain_5_to_10_pp']:.6f} percentage points in the clean primary slice. Saturation below 1 pp: {primary['gain_under_1pp']}; strictly decreasing overlap: {primary['overlap_strictly_decreasing']}. Non-decreasing recall alone is mathematical, not evidence of improved learning.", '',f"Across all 120 triples, OR exfiltration warning recall ranges from {dist['warning_recall']['min']*100:.3f}% to {dist['warning_recall']['max']*100:.3f}% (median {dist['warning_recall']['median']*100:.3f}%). False-alert counts range from {dist['false_alerts']['min']:.0f} to {dist['false_alerts']['max']:.0f} (median {dist['false_alerts']['median']:.1f}). These are sensitivity summaries, not independent confidence intervals.", '',f"H6 has {len(triggers)} qualifying cells. With none, its implication is vacuously true and provides no empirical aggregator-contrast evidence.", '', 'The delayed experiment shares the original seed-8101 acquisition schedule across every member; seven new roles seeds use the seed-8101 current model as fallback. Wrong-host history is unchanged input for roles-only experts. A4 is an acquisition-unconstrained reference, clearly excluded from budget-feasibility claims. No roles-corruption experiment was performed.', '',f"Audit: {audit['checks']:,} checks passed over {audit['cells']} cells / {audit['result_rows']} reported rows. Every saved OR/mean decision was recomputed independently from source probability arrays, and all seven new models' full test predictions were reproduced. No cloud allocation or model API was used.", '', '## Required scope statements','',scope,'','## Evidence','','[Protocol](PROTOCOL.md) | [Execution clarifications](EXECUTION_NOTES.md) | [Freeze](FREEZE.json) | [Audit](AUDIT.json) | [Hypothesis details](HYPOTHESES.json) | [Part A](partA/RESULTS.md) | [Part B](partB/RESULTS.md) | [Part C](partC/RESULTS.md)']
    (HERE/'FINDINGS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    manifest={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.suffix in ['.csv','.gz']};save(HERE/'OUTPUT_HASHES.json',manifest)
    print(json.dumps(status,indent=2));print('REPORT COMPLETE')
if __name__=='__main__':main()
