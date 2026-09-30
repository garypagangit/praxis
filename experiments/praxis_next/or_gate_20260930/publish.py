"""Post-run presentation and registry update; no experiment decisions or tuning."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent
def main():
    h=json.loads((HERE/'HYPOTHESES.json').read_text());a=json.loads((HERE/'AUDIT.json').read_text());assert a['status']=='PASS'
    rows=json.loads((HERE/'partB/GROUPS.json').read_text());ns=[1,2,3,5,7,10]
    fig,axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for agg,color in [('OR','#166f89'),('MEAN','#bd6132')]:
        rs=[next(r for r in rows if r['cell']==f'B_n{n}_clean_b2' and r['aggregator']==agg) for n in ns]
        axes[0].plot(ns,[r['exfiltration']['warning_recall']*100 for r in rs],'-o',label=agg,color=color)
        axes[1].plot(ns,[r['false_alerts'] for r in rs],'-o',label=agg,color=color)
    axes[0].set_ylabel('Exfiltration warning recall (%)');axes[0].set_ylim(0,101);axes[1].set_ylabel('Benign false alerts (flow count)')
    for ax in axes:ax.set_xlabel('Number of roles-model seeds');ax.set_xticks(ns);ax.grid(alpha=.2);ax.legend(frameon=False)
    fig.suptitle('PX-092: clean UNRAVELED, budget 2\nPreviously examined campaign; nested seed sets',fontsize=12)
    fig.savefig(HERE/'partB/SEED_CURVE.png',dpi=180);fig.savefig(HERE/'partB/SEED_CURVE.pdf');plt.close(fig)
    fit=json.loads((HERE/'partB/FIT_LOG.json').read_text());compute={'execution':'Local CPU only','new_fits':fit['completed_fits'],'summed_fit_and_prediction_seconds':sum(r['seconds'] for r in fit['fits']),'threads_per_fit':2,'cloud_allocations':0,'model_api_calls':0,'replay_cells':a['cells'],'result_rows':a['result_rows'],'private_artifact_root':'C:/w/px092_or_gate_20260930'}
    (HERE/'COMPUTE.json').write_text(json.dumps(compute,indent=2)+'\n')
    p=HERE.parent/'REGISTRY.json';d=json.loads(p.read_text());assert not any(e['id']=='PX-092' for e in d['experiments'])
    d['experiments'].append({'id':'PX-092','directory':HERE.name,'title':'Warning-Preserving OR-Gate: Generalization, Seed-Count and Adversity','status':'COMPLETE_EXPLORATORY_AND_ADAPTED_EXECUTION_REPLAY_AUDIT_PASS','protocol':HERE.name+'/PROTOCOL.md','execution_clarifications':HERE.name+'/EXECUTION_NOTES.md','results':HERE.name+'/FINDINGS.md','hypotheses':h['status'],'novelty':'UNCONFIRMED','finding':'Known clean seed-union benefit reproduced; AIT strict per-execution improvement criterion not met. See frozen seed-count and adversity outcomes; no universal benefit claimed.'})
    p.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8')
    p=HERE.parent/'README.md';s=p.read_text(encoding='utf-8');p.write_text('> **PX-092 completed:** [OR-gate generalization, seed-count and adversity results](or_gate_20260930/FINDINGS.md), including seven new roles fits, all 120 triples, adapted AIT results and an independent per-row audit.\n\n'+s,encoding='utf-8')
    print('PUBLISHED registry, compute receipt and seed-curve figure')
if __name__=='__main__':main()
