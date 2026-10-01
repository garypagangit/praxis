"""Post-audit reporting; no model fitting or selection."""
import csv,gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def main():
    audit=json.loads((HERE/'AUDIT.json').read_text());assert audit['status']=='PASS';rows=json.loads((HERE/'RESULTS.json').read_text());qs=json.loads((HERE/'QUEUE_RESULTS.json').read_text())
    csvwrite(HERE/'RESULTS.csv',rows);flat=[]
    for q in qs:
        r={k:v for k,v in q.items() if k!='episode_review_slots'}
        for gap,v in q['episode_review_slots'].items():r.update({f'gap{gap}_{k}':a for k,a in v.items()})
        flat.append(r)
    csvwrite(HERE/'QUEUE_RESULTS.csv',flat)
    for name in ['RESULTS','QUEUE_RESULTS']:(HERE/(name+'.json.gz')).write_bytes(gzip.compress((HERE/(name+'.json')).read_bytes(),mtime=0))
    def get(ex,arm):return next(r for r in rows if r['execution']==ex and r['arm']==arm and r['window_minutes']==15 and r['grouping']=='pair' and r['episode_gap_minutes']==60)
    def qget(ex,arm,staff=1,minutes=15):return next(r for r in qs if r['execution']==ex and r['arm']==arm and r['window_minutes']==15 and r['grouping']=='pair' and r['staff']==staff and r['minutes_per_case']==minutes)
    arms=['base_mean','base_OR','plus_current_OR','full_OR'];sources=['UNRAVELED','wilson','harrison']
    lines=['# PX-094: exfiltration episode coverage and SOC workload','', '**Scope:** source/client-host episodes inferred from flow labels and timing, plus simulated review cases. These are not independently confirmed SOC incidents or measured analyst outcomes. Zero new fits and no cloud/API use.','', '## Primary grouping: source–destination, 15-minute windows; 60-minute episode gap','', '| Source | Policy | Exfil episodes warned / total | Raw warning flows | Grouped cases | Benign-only-warning cases | New episodes vs base OR | Earlier episodes vs base OR |','|---|---|---:|---:|---:|---:|---:|---:|']
    for ex in sources:
        for arm in arms:
            r=get(ex,arm);lines.append(f"| {ex} | {arm} | {r['episodes_warned']} / {r['episodes']} | {r['warning_flows']} | {r['cases']} | {r['benign_only_warning_cases']} | {r['new_episodes_vs_base']} | {r['earlier_episodes_vs_base']} |")
    lines+=['','A case is released at its fixed window end. Benign-only-warning means all warned flows in that case are labeled benign; an unflagged attack sharing the group is not credited as detected. Episode boundaries are evaluation proxies; captures/executions are never silently pooled into one campaign.','', '## Reference scenario: one analyst, 15 minutes per case, 09:00–17:00 UTC daily','', '| Source | Policy | Analyst-hours of service | Cases unfinished at observation end | Median wait (hours) | P95 wait (hours) | Episodes with a review slot completed within 60 minutes | Within 240 minutes |','|---|---|---:|---:|---:|---:|---:|---:|']
    for ex in sources:
        for arm in arms:
            q=qget(ex,arm);e=q['episode_review_slots']['60'];lines.append(f"| {ex} | {arm} | {q['analyst_hours']:.2f} | {q['unresolved_by_horizon']} | {q['wait_median_hours']:.2f} | {q['wait_p95_hours']:.2f} | {e['served_within_60min']} / {e['episodes']} | {e['served_within_240min']} / {e['episodes']} |")
    lines+=['','Service hours sum analyst effort, not elapsed calendar hours. A completed slot does not establish a correct analyst verdict. Delays include batch-window release and staffing shifts; real SOC schedules, priority triage and case complexity are not measured.','', '## Marginal heterogeneous-gate workload','', '| Source | Added grouped cases vs base OR | Added service hours at 5 min | At 15 min | At 30 min | Additional primary episodes |','|---|---:|---:|---:|---:|---:|']
    summary=[]
    for ex in sources:
        r=get(ex,'full_OR');b=get(ex,'base_OR');d=r['cases']-b['cases'];lines.append(f"| {ex} | {d} | {d*5/60:.2f} | {d*15/60:.2f} | {d*30/60:.2f} | {r['new_episodes_vs_base']} |")
        variants=[x for x in rows if x['execution']==ex and x['arm']=='full_OR'];summary.append({'source':ex,'primary_new_episodes':r['new_episodes_vs_base'],'primary_extra_cases':d,'episode_new_min':min(x['new_episodes_vs_base'] for x in variants),'episode_new_max':max(x['new_episodes_vs_base'] for x in variants),'case_extra_min':min(x['additional_cases_vs_base'] for x in variants),'case_extra_max':max(x['additional_cases_vs_base'] for x in variants),'primary_base_OR_episodes':b['episodes_warned'],'primary_episodes_total':b['episodes'],'primary_mean_episodes':get(ex,'base_mean')['episodes_warned'],'reference_base_review_within_60':qget(ex,'base_OR')['episode_review_slots']['60']['served_within_60min'],'reference_full_review_within_60':qget(ex,'full_OR')['episode_review_slots']['60']['served_within_60min']})
    lines+=['','## Sensitivity, all retained','', '| Source | Full-OR new episodes: minimum–maximum | Additional grouped cases: minimum–maximum |','|---|---:|---:|']
    for s in summary:lines.append(f"| {s['source']} | {s['episode_new_min']}–{s['episode_new_max']} | {s['case_extra_min']}–{s['case_extra_max']} |")
    lines+=['','Ranges span all declared 5/15/60-minute windows, source or pair grouping, and 30/60/120-minute episode gaps. Repeated views are dependent. Staff and service-time grids are in QUEUE_RESULTS.csv; no favorable scenario is promoted after inspection.','', '## Evidence and interpretation limits','', f"Independent audit: {audit['checks']:,} checks across 72 case cells, 216 episode-result rows and 648 queue scenarios. Frozen source hashes, native endpoint mapping, all group/episode counts and every simulated queue were checked. No actual staffing record or confirmed incident ID was available.", '', 'This experiment tests whether flow-level gains become new episode coverage under stated definitions, and what case/queue burden follows. It cannot determine the number of real incidents rescued or the probability of an analyst reaching a correct conclusion. Evidence needed for that next claim is a case-linked incident ground truth and timed analyst review; additional replay or model tuning cannot substitute for those observations.','', '[Frozen protocol](PROTOCOL.md) | [Episode results CSV](RESULTS.csv) | [Queue scenarios CSV](QUEUE_RESULTS.csv) | [Audit](AUDIT.json)']
    (HERE/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');(HERE/'SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    registry=HERE.parent/'REGISTRY.json';d=json.loads(registry.read_text());assert not any(e['id']=='PX-094' for e in d['experiments']);d['experiments'].append({'id':'PX-094','directory':HERE.name,'title':'Exfiltration Episode Coverage and Grouped SOC Workload','status':'COMPLETE_PROXY_EPISODE_AND_QUEUE_REPLAY_AUDIT_PASS','protocol':HERE.name+'/PROTOCOL.md','results':HERE.name+'/RESULTS.md','novelty':'UNCONFIRMED','scope':'Label-defined episodes and simulated review slots; no confirmed incident or analyst effectiveness claim','finding':summary});registry.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    p=HERE.parent/'README.md';p.write_text('> **PX-094 completed:** [Exfiltration episode coverage, grouped investigations and SOC workload scenarios](soc_workload_20261001/RESULTS.md). Existing predictions only; qualified episode proxies and simulated review times.\n\n'+p.read_text(encoding='utf-8'),encoding='utf-8');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
