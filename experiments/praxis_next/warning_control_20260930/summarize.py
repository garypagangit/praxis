"""Audit cloud outputs against historical replay and publish aggregate findings."""
import csv, gzip, hashlib, json
from pathlib import Path
import numpy as np
from common import save,STAGES

HERE=Path(__file__).resolve().parent
PRIVATE=Path('C:/w/warning_control_20260930')
def mean_rows(rows):
    out={m:float(np.mean([r[m] for r in rows])) for m in ['macro_f1','false_alerts','benign_fpr','warnings_per_100k','mean_spend']}
    for s in STAGES[1:]:
        out[s+'_warning']=float(np.mean([r[s]['warning_recall'] for r in rows]))
        out[s+'_range']=[float(min(r[s]['warning_recall'] for r in rows)),float(max(r[s]['warning_recall'] for r in rows))]
    return out

def table(rows):
    result=['| Policy | Cost | F1 | Exfil warning % | Movement warning % | Benign false alerts |','|---|---:|---:|---:|---:|---:|']
    for r in rows:result.append(f"| {r['policy']} | {r['mean_spend']:.2f} | {r['macro_f1']:.4f} | {r['exfiltration_warning']*100:.2f} | {r['movement_warning']*100:.2f} | {r['false_alerts']:.1f} |")
    return '\n'.join(result)

def main():
    src=PRIVATE/'local_reference'
    done=json.loads((src/'COMPLETE.json').read_text());assert done['passed'] and done['parallel_workers']==2
    assert len(set(x['pid'] for x in done['jobs']))==2
    cloud=json.loads((HERE/'AWS_AUDIT.json').read_text());assert cloud['passed']
    active=json.loads((PRIVATE/'ACTIVE_RUN.json').read_text());assert active['stage'] in ['closed','stop_requested']
    base=[];controlled=[];decomp=[]
    for p in sorted(src.glob('8*.json')):
        z=json.loads(p.read_text());base+=z['baselines'];controlled+=z['controlled'];decomp+=z['decomposition']
    assert len(base)==189 and len(controlled)==2268 and len(decomp)==81
    old=json.loads(Path('C:/Users/garyp/OneDrive/Documents/codex/reports/praxis_evidence_diagnostic_20260930/RESULTS.json').read_text())
    checks=0
    for r in base:
        if r['policy'].startswith('roles_stop'):continue
        match=[o for o in old if all(o.get(k)==r[k] for k in ['seed','condition','budget','policy'])];assert len(match)==1
        assert match[0]['confusion']==r['confusion']
        assert abs(match[0]['mean_spend']-r['mean_spend'])<1e-7;checks+=1
    for r in controlled:
        b=next(b for b in base if all(b[k]==r[k] for k in ['seed','condition','budget','policy']))
        assert r['false_alerts']>=b['false_alerts']
        for s in STAGES[1:]:assert r[s]['missed']<=b[s]['missed']
        checks+=1
    ensemble=json.loads((src/'ENSEMBLES.json').read_text())
    for r in ensemble['diagnostics']:
        assert r['union_misses']<=min(r['single_seed_misses']);checks+=1
    summaries=[]
    for c in ['clean','delayed_unavailable','wrong_host_history']:
        for b in [1,2,3]:
            for p in ['none','roles_first','history_first','entropy','harm','roles_stop50','roles_stop90']:
                z=[r for r in base if r['condition']==c and r['budget']==b and r['policy']==p];assert len(z)==3
                summaries.append({'condition':c,'budget':b,'policy':p,**mean_rows(z)})
    gate_summaries=[]
    for c in ['clean','delayed_unavailable','wrong_host_history']:
        for b in [1,2,3]:
            for p in ['none','roles_first','history_first','entropy','harm','roles_stop50','roles_stop90']:
                for scope in ['pooled_attack','supported_stages','all_stages_fail_closed']:
                    for alpha in [.01,.02,.05,.1]:
                        z=[r for r in controlled if r['condition']==c and r['budget']==b and r['policy']==p and r['scope']==scope and r['alpha']==alpha]
                        gate_summaries.append({'condition':c,'budget':b,'policy':p,'scope':scope,'alpha':alpha,**mean_rows(z)})
    dest=HERE/'results';dest.mkdir(exist_ok=True)
    pareto=[]
    for r in base:
        peers=[b for b in base if all(b[k]==r[k] for k in ['seed','condition','budget']) and b['policy']!=r['policy']]
        def vector(b):return [b['mean_spend'],b['false_alerts']]+[-b[s]['warning_recall'] for s in STAGES[1:]]
        v=vector(r);dominators=[]
        for b in peers:
            bv=vector(b)
            if all(x<=y+1e-12 for x,y in zip(bv,v)) and any(x<y-1e-12 for x,y in zip(bv,v)):dominators.append(b['policy'])
        pareto.append({k:r[k] for k in ['seed','condition','budget','policy']}|{'dominated_by':dominators})
    save(dest/'PARETO.json',{'objectives':'minimize simulated acquisition cost and benign false alerts; maximize each of three stage warning recalls. Exact-stage recall and F1 are reported separately and excluded here.','rows':pareto})
    for p in src.glob('*.json'):
        (dest/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
    save(dest/'SUMMARY.json',{'baseline':summaries,'gated':gate_summaries})
    flat=[]
    for r in base+controlled+ensemble['baselines']+ensemble['controlled']:
        out={k:r.get(k) for k in ['seed','condition','budget','policy','scope','alpha','threshold','macro_f1','mean_spend','false_alerts','benign_fpr','warnings_per_100k']}
        for s in STAGES[1:]:out[s+'_miss_rate']=r[s]['miss_rate'];out[s+'_exact_recall']=r[s]['exact_recall']
        flat.append(out)
    with (dest/'ALL_ARMS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=flat[0].keys());w.writeheader();w.writerows(flat)
    save(HERE/'AUDIT.json',{'passed':True,'output_checks':checks,'preparation_checks':406,'prior_calibration_checks':54,'self_tests':done['self_test_checks'],'local_parallel_worker_pids':sorted(set(x['pid'] for x in done['jobs'])),'baseline_rows':len(base),'gated_rows':len(controlled),'decomposition_rows':len(decomp),'ensemble_baseline_rows':len(ensemble['baselines']),'ensemble_gated_rows':len(ensemble['controlled']),'aws_independent_audit_passed':True,'result_hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in src.glob('*.json')}})
    save(HERE/'COMPUTE.json',{k:active.get(k) for k in ['start_request_utc','stopped_observed_utc','usd_per_hour','approximate_compute_usd','approximate_total_with_allowance_usd','host_time_cap_observed','watchdog_cleanup'] }|{'aws_used':True,'aws_scope':'independent aggregate metric and rank-rule audit; full-data upload failed','gpu_used':False,'parallel_workers':2,'local_replay_wall_seconds':done['wall_seconds'],'aws_audit_wall_seconds':cloud['wall_seconds'],'new_model_fits':0,'is_invoice':False,'status':'CLOSED_VERIFIED_STOPPED' if active['stage']=='closed' else 'STOP_REQUESTED_NOT_YET_VERIFIED'})
    primary=[r for r in summaries if r['condition']=='clean' and r['budget']==2]
    gprimary=[r for r in gate_summaries if r['condition']=='clean' and r['budget']==2 and r['scope']=='supported_stages' and r['alpha']==.05]
    text=['# PX-085--087: local replay and independent AWS audit','Exploratory replay of the previously examined UNRAVELED campaign. Full replay ran locally; AWS independently recomputed aggregate metrics and rank-rule checks with two CPU processes after the large payload transfer failed. All arms are retained in results/ALL_ARMS.csv. Means below are across three fitting seeds, not independent campaigns.','## Original decisions and fixed stopping: clean, budget 2',table(primary),'## Supported-stage gate, target alpha 5%: same rows',table(gprimary),'Movement has zero calibration support. Its test recall is measured, but it has no supported-stage risk claim. All-stage fail-closed warns on every row. Chronological flow data do not establish exchangeability; no deployment risk guarantee is claimed.','## Mean-ensemble warning losses','For each fixed state, the table counts attack rows where some seed warned but the probability mean calls the row benign. This directly tests the supplied mean-retention claim.','| State | Stage | Single-seed misses | Mean misses | Union misses | Mean loses a seed warning |','|---|---|---|---:|---:|---:|']
    for r in ensemble['diagnostics']:
        if r['condition']=='clean':text.append(f"| {r['state']} | {r['stage']} | {r['single_seed_misses']} | {r['mean_misses']} | {r['union_misses']} | {r['mean_loses_any_seed_warning']} |")
    text+=['## Limits','No new fitting or independent dataset was included. Acquisition costs and delivery failures are inherited simulations. Fixed-state ensembles require three model evaluations and are unrestricted references under delayed delivery. Novelty remains unconfirmed. The oracle decomposition cannot be deployed because it inspects hypothetical expert outcomes. Conformal thresholds are established methods; empirical target attainment on this campaign would not prove a general guarantee.']
    (HERE/'RESULTS.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')
    print(table(primary));print('\n5% supported gate\n'+table(gprimary));print(json.dumps({'audit_checks':checks,'compute_usd_estimate':active.get('approximate_compute_usd')}))
if __name__=='__main__':main()
