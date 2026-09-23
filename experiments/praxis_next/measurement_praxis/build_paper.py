"""Build the measurement manuscript and figures from unchanged audited results."""
from pathlib import Path
from datetime import datetime, timezone
import csv
import hashlib
import importlib.metadata
import json
import re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime as DT

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
FIG=HERE/'figures'
TABLES=HERE/'tables'
INPUTS=[]


def read(path):
    INPUTS.append(path)
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def pick(rows,**where):
    found=[r for r in rows if all(r[k]==v for k,v in where.items())]
    if len(found)!=1:raise ValueError(where)
    return found[0]


def table(name,headers,rows):
    with (TABLES/(name+'.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(headers);writer.writerows(rows)
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
        ['| '+' | '.join(str(v).replace('|','/') for v in row)+' |' for row in rows])


def pct(v):return f'{v*100:.2f}%'


def build():
    FIG.mkdir(exist_ok=True);TABLES.mkdir(exist_ok=True)
    a=read(BASE/'px080_context_selector/results/MEANS.json')
    b=read(BASE/'px081_evidence_acquisition/AGGREGATE.json')
    c=read(BASE/'px082_temporal_audit/SUMMARY.json')
    supports=read(BASE/'d1_benchmark_audit/SUPPORT_CUTOFF_AUDIT.json')
    refs=read(HERE/'references.json')
    qa=read(HERE/'evidence/qualification_audit/VERIFICATION.json')
    if not qa.get('all_registered_verification_checks_passed'):raise ValueError('Independent qualification verification must pass')
    repl=read(HERE/'evidence/paired_reanalysis/PAPER_DATA.json')
    t={}
    t['STUDY_TABLE']=table('study_scope',['Component','Completed scope','Role in this paper'],[
        ['History selection','39 fits; 7 arms; 5 conditions; 3 seeds','Context tradeoffs and simple controls'],
        ['Evidence acquisition','84 fits; 3 budgets; 3 conditions; 3 seeds','Paired stage/warning outcomes'],
        ['Temporal comparison','18 fits; 2 feature views; 3 split arms; 3 seeds','Fixed-anchor protocol sensitivity'],
        ['Paired reanalysis','36 comparisons; no new fits','Retrospective, capture-conditional uncertainty'],
        ['Benchmark qualification','4 requested sources; no new fits','Native support, timing and dependencies'],
        ['Policy-transfer supplement','2 fits; T1105 recognition','Separate task; not stage replication']])
    rows=[]
    for view,vn in [('current','Current'),('current_history','Current + history')]:
        for arm,an in [('past_only_anchor','Past'),('time_mixed_anchor','Mixed'),('conventional_random','Random')]:
            r=pick(c,view=view,arm=arm)
            rows.append([vn+' / '+an,f"{r['macro_f1']:.4f}",pct(r['movement_recall']),f"{r['movement_f1']:.4f}",
                f"{r['exfiltration_f1']:.4f}",f"{r['normal_false_attacks']:.1f} ({100*r['normal_false_attack_rate']:.3f}%)"])
    t['TEMPORAL_TABLE']=table('temporal_results',['Features / fit','Macro-F1','Movement recall','Movement F1','Exfil. F1','Benign alerts (rate)'],rows)
    rows=[]
    for cond,cn in [('clean','Clean'),('delayed_unavailable','Delayed'),('wrong_host_history','Wrong host')]:
        for policy,pn in [('entropy','Entropy'),('harm','Error focused')]:
            r=pick(b,condition=cond,budget=3,policy=policy)
            rows.append([cn+' / '+pn,f"{r['macro_f1']:.4f}",pct(r['exfiltration_recall']),
                pct(r['exfiltration_any_attack_recall']),f"{r['benign_false_alerts']:.1f}"])
    t['WARNING_TABLE']=table('warning_results',['Condition / policy','Macro-F1','Exact exfil. recall','Exfil. warning recall','Benign alerts'],rows)
    rows=[]
    for cond,cn in [('clean','Clean'),('missing_half','Half missing'),('missing_all','All missing'),('stale_5min','Stale'),('wrong_host','Wrong host')]:
        o=pick(a,condition=cond,arm='ordinary_gate');h=pick(a,condition=cond,arm='stage_harm_gate');d=pick(a,condition=cond,arm='context_dropout')
        rows.append([cn,pct(o['movement_recall']),pct(h['movement_recall']),pct(d['movement_recall']),
            f"{o['normal_false_attacks']:.1f} / {h['normal_false_attacks']:.1f}"])
    t['HISTORY_TABLE']=table('history_results',['Condition','Ordinary recall','Weighted recall','Dropout recall','Alerts: ordinary / weighted'],rows)
    t['QUALIFICATION_TABLE']=table('qualification',['Source','Inspected rows','Native classes','Completed finding'],[
        ['SCVIC-APT-2021','259,120','6','Possible recorded-start support; clocks and execution mapping unqualified'],
        ['DAPT2020','86,691','5','No all-class single cutoff; 15 exfiltration rows'],
        ['DSRL-APT-2023','65,000','5','DAPT-derived synthetic source; no natural event chronology'],
        ['S-DAPT-2026','None acquired','Not verified','No qualified acquired release']])
    t['RELATED_WORK_TABLE']=table('related_work',['Closest work','Established contribution','Scope of this study'],[
        ['TESSERACT (2019)','Temporal and distribution constraints in malware evaluation','Same-anchor APT-flow training-pool contrast'],
        ['Bilot et al. (2025); Guerra et al. (2026)','Critical provenance/ APT benchmarking and practical controls','Flow-stage observations with explicit source support'],
        ['Uddin et al. (2025)','Attack-type errors versus attacks called normal','Measured metric/warning tradeoffs under evidence changes'],
        ['TAN-IDS (2026)','Flow-based cross-domain evaluation; binary scope','Stage-conditioned warning outcomes and temporal controls'],
        ['Othman et al. (2026)','DAPT stage timing and residual-time survival analysis','Necessary support for a different, all-class classifier split']])
    t['PARAMETER_TABLE']=table('parameters',['Study','Classifier trees / leaves','Fitting seeds','Key fixed choices'],[
        ['History selection','180 / 15','20260924-20260926','4 forward folds; class weights 1/1/4/4 for weighted selector'],
        ['Evidence acquisition','150 / 15','8101-8103','2 optional groups; costs 1/2; budgets 1/2/3; deadline 1'],
        ['Temporal comparison','200 / 15','20260923-20260925','Same anchor and class budgets; earlier/mixed/random arms'],
        ['Paired reanalysis','No fits','Bootstrap 20260923','2,000 whole-capture draws shared across fitting seeds']])
    t['FREEZE_TABLE']=table('freezes',['Artifact','Before-execution commit','Evidence'],[
        ['History-selection protocol/source','06c5037','Original model audit'],
        ['Acquisition and temporal protocol/source','2da1a1c','Original model audits'],
        ['D1 support diagnostic','ea9956c','Native-class necessary interval'],
        ['Independent source-count verifier','e6b5799','Direct timestamp-block sweep'],
        ['Retrospective paired reanalysis','c0d884e','Saved-prediction comparison; exploratory']])
    claimrows=[
        ['Temporal score sensitivity','+0.0632 macro-F1; +35.19 pp movement recall','[Temporal report](../px082_temporal_audit/REPORT.md)'],
        ['Metric/warning tradeoff','Clean budget 3: +0.0231 macro-F1; -8.93 pp warning recall','[Paired report](evidence/paired_reanalysis/REPORT.md)'],
        ['Chronological history gains','Macro-F1 .7365 to .7582; alerts 24.0 to 14.3','[Original means](../px082_temporal_audit/SUMMARY.json)'],
        ['Native-class cutoff limitation','DAPT lower bound exceeds upper bound','[Independent verification](evidence/qualification_audit/VERIFICATION.json)'],
        ['Source qualification','SCVIC uncertainty; DSRL dependency; S-DAPT unavailable','[Qualification report](../d1_benchmark_audit/DATASET_QUALIFICATION.md)'],
        ['Literature differentiation','Existing metrics; controlled measurement contribution','[Literature audit](LITERATURE_AND_CLAIMS.md)']]
    t['CLAIM_TABLE']=table('claim_traceability',['Claim','Measured support','Evidence location'],claimrows)
    formatted=[]
    for r in refs:
        entry=r['apa']
        if r['id']=='liu2022':entry=entry.replace('(2022).','(2022a).')
        if r['id']=='liu2022dataset':entry=entry.replace('(2022).','(2022b).')
        formatted.append(entry)
    t['REFERENCES']='\n\n'.join(sorted(formatted,key=str.casefold))
    for key in ['TEMPORAL_UNCERTAINTY','WARNING_REANALYSIS','HISTORY_REANALYSIS']:
        t[key]=repl[key]
    t['QUALIFICATION_AUDIT']='A separate CSV-parser implementation enumerated all tied-time membership states: 0 of 28,941 DAPT states met the all-native-class two-earlier/one-later rule, whereas 9,475 of 11,693 SCVIC states met recorded-start support. The latter did not resolve its clock or execution-identity limitations. Native-class totals and input hashes matched before and after the separate reads. The verifier did not import the original bound function. Its [verification receipt](evidence/qualification_audit/VERIFICATION.json) records all 16 checks and source identities.'
    # Publication plots: values come from original aggregates or paired outputs.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(8,3.8))
    for x,(v,lab,col) in enumerate([('current','Current features','#236b8e'),('current_history','Current + history','#c36a39')]):
        past=pick(c,view=v,arm='past_only_anchor');mixed=pick(c,view=v,arm='time_mixed_anchor')
        ax.bar(x-.17,past['macro_f1'],.32,color=col,alpha=.48,label='Past only' if x==0 else None)
        ax.bar(x+.17,mixed['macro_f1'],.32,color=col,label='Time mixed' if x==0 else None)
        ax.text(x,past['macro_f1']+.077,f"Delta +{mixed['macro_f1']-past['macro_f1']:.4f}",ha='center',fontweight='bold')
    ax.set_xticks([0,1],['Current features','Current + history']);ax.set_ylim(0,1);ax.set_ylabel('Macro-F1');ax.grid(axis='y',alpha=.15)
    ax.legend(loc='lower right',frameon=False);fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(FIG/('temporal_effects.'+ext),dpi=200)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,3.8));labels=['Entropy acquisition','Error-focused acquisition']
    exact=[];wrong=[];miss=[]
    for policy in ['entropy','harm']:
        r=pick(b,condition='clean',budget=3,policy=policy)
        exact.append(100*r['exfiltration_recall']);wrong.append(100*(r['exfiltration_any_attack_recall']-r['exfiltration_recall']));miss.append(100*(1-r['exfiltration_any_attack_recall']))
    left=np.zeros(2)
    for vals,lab,col in [(exact,'Exact stage','#286c74'),(wrong,'Other attack stage','#83b7aa'),(miss,'Benign: warning lost','#c87054')]:
        ax.barh(labels,vals,left=left,label=lab,color=col)
        for i,(start,val) in enumerate(zip(left,vals)):
            if val>4:ax.text(start+val/2,i,f'{val:.1f}%',ha='center',va='center',color='white' if col!='#83b7aa' else '#18252b',fontweight='bold')
        left+=vals
    ax.set_xlim(0,100);ax.set_xlabel('Percentage of 3,442 exfiltration-labeled rows (three-fit means)')
    ax.legend(loc='lower center',bbox_to_anchor=(.43,-.4),ncol=3,frameon=False,fontsize=9);fig.tight_layout(rect=(0,.12,1,1))
    for ext in ['png','pdf']:fig.savefig(FIG/('warning_destinations.'+ext),dpi=200)
    plt.close(fig)
    # Source support intervals supplied directly by the frozen support receipt.
    ds=supports['datasets']['DAPT2020'] if isinstance(supports['datasets'],dict) else next(x for x in supports['datasets'] if x['dataset']=='DAPT2020')
    fig,ax=plt.subplots(figsize=(8,4))
    # The published receipt provides second-earliest rather than earliest bounds;
    # mark exactly those necessary-support ranges and label them explicitly.
    colors={'Data Exfiltration':'#c87054','Reconnaissance':'#236b8e'}
    for i,(name,item) in enumerate(ds['classes'].items()):
        left=DT.fromisoformat(item['second_earliest_recorded_timestamp']);right=DT.fromisoformat(item['latest_recorded_timestamp'])
        ax.plot([left,right],[i,i],lw=8,solid_capstyle='butt',color=colors.get(name,'#849a9d'))
    ax.set_yticks(range(len(ds['classes'])),list(ds['classes']));ax.xaxis.set_major_locator(mdates.DayLocator(interval=1));ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax.set_xlabel('Recorded time, 2019: second-earliest start through latest start');ax.grid(axis='x',alpha=.2)
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(FIG/('dapt_stage_support.'+ext),dpi=200)
    plt.close(fig)
    template=HERE/'manuscript.template.md';INPUTS.append(template)
    text=template.read_text(encoding='utf-8')
    placeholders=set(re.findall(r'\{\{([A-Z_]+)\}\}',text))
    if placeholders!=set(t):raise ValueError({'missing':sorted(placeholders-set(t)),'unused':sorted(set(t)-placeholders)})
    for name,value in t.items():text=text.replace('{{'+name+'}}',value)
    for before,after in [('macro-F1 (pp)','macro-F1 (x100)'),('95% paired interval (pp)','95% F1 interval (x100)'),
                         ('Mean Δ F1 (pp)','Mean Δ F1 (x100)'),('Δ F1 (pp)','Δ F1 (x100)'),('Δ macro-F1 pp','Δ macro-F1 x100')]:
        text=text.replace(before,after)
    if '{{' in text:raise ValueError('Unexpanded template token')
    (HERE/'manuscript.md').write_text(text,encoding='utf-8')
    receipt={'utc':datetime.now(timezone.utc).isoformat(),'new_model_fits':0,
        'inputs':{p.relative_to(BASE).as_posix():sha(p) for p in INPUTS},
        'source_sha256':sha(Path(__file__)),'manuscript_sha256':sha(HERE/'manuscript.md'),
        'tables':{p.name:sha(p) for p in TABLES.glob('*.csv')},'figures':{p.name:sha(p) for p in FIG.iterdir()},
        'versions':{n:importlib.metadata.version(n) for n in ['numpy','matplotlib']}}
    (HERE/'BUILD_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'words':len(text.split()),'tables':len(receipt['tables']),'figures':len(receipt['figures'])}))


if __name__=='__main__':build()
