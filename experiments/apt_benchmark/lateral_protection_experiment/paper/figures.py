"""Descriptive publication figures, with plotted values exported as JSON."""
import argparse
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

COLORS={'natural':'#17365d','balanced':'#008597','lateral2':'#d4872b','lateral4':'#a4383b'}

def build(results, out):
    results,out=Path(results),Path(out);out.mkdir(parents=True,exist_ok=True)
    evidence=json.loads((results/'EVIDENCE.json').read_text()); cells=json.loads((results/'CELL_METRICS.json').read_text())
    if evidence['status']!='AUDITED_COMPLETE_DEVELOPMENT_STUDY':raise ValueError('Complete audited results required')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold'})
    saved={}
    fig, axes=plt.subplots(1,2,figsize=(10,4.2),layout='constrained')
    for family,ax in zip(['xgboost','lightgbm'],axes):
        for scheme,color in COLORS.items():
            xs,ys=[],[]
            for budget in [32,128,512,1024]:
                rows=[r['metrics']['verification']['argmax_alert'] for r in cells if r['budget']==budget and r['seed']<=20260923 and r['cell_id']==family+'/'+scheme]
                if len(rows)!=3:raise ValueError('Matched three-seed budget curve is incomplete')
                x=100*np.mean([r['benign_fpr'] for r in rows]);y=100*np.mean([r['per_stage']['LateralMovement']['recall'] for r in rows]);xs.append(x);ys.append(y)
                saved[f'{family}/{scheme}/{budget}']={'benign_fpr_pct':float(x),'lateral_recall_pct':float(y),'n_fitting_seeds':3,'partition':'verification','policy':'argmax'}
            ax.plot(xs,ys,'o-',color=color,label=scheme,linewidth=1.4,markersize=4)
            ax.annotate('32',(xs[0],ys[0]),xytext=(4,5),textcoords='offset points',fontsize=8,color=color)
            ax.annotate('1024',(xs[-1],ys[-1]),xytext=(4,-10),textcoords='offset points',fontsize=8,color=color)
        ax.axvline(1,color='#999999',linestyle='--',linewidth=.8);ax.axhline(90,color='#999999',linestyle='--',linewidth=.8)
        ax.set_xlabel('Benign flows flagged (%)');ax.set_ylabel('Lateral flows detected (%)');ax.set_title({'xgboost':'XGBoost','lightgbm':'LightGBM'}[family]);ax.grid(alpha=.15)
        ax.set_xlim(left=0);ax.set_ylim(0,102)
    axes[1].legend(title='Training weights',loc='lower right',frameon=False)
    fig.suptitle('More benign examples change the false-alarm / detection tradeoff',fontsize=12)
    fig.savefig(out/'budget_tradeoff.png',dpi=180);fig.savefig(out/'budget_tradeoff.pdf');plt.close(fig)
    rows=[r for r in json.loads((results/'SUMMARY.json').read_text())['groups'] if r['budget']==1024]
    fig,axes=plt.subplots(2,1,figsize=(9,6),sharex=True,layout='constrained')
    labels=[]
    for pos,g in enumerate(rows):
        labels.append(str(g['seed'])[-2:])
        for offset,name,color,marker in [(-.16,'cv_natural_argmax','#17365d','o'),(0,'cv_natural_benign_threshold','#008597','s'),(.16,'candidate','#a4383b','D')]:
            m=g['partitions']['verification'].get(name)
            if m is None:continue
            axes[0].scatter(pos+offset,100*m['benign_fpr'],color=color,marker=marker,s=35,label=name if pos==0 else None)
            axes[1].scatter(pos+offset,100*m['per_stage']['LateralMovement']['recall'],color=color,marker=marker,s=35)
    for ax,value in zip(axes,[1,90]):ax.axhline(value,color='#666666',linestyle='--',linewidth=1);ax.grid(axis='y',alpha=.15)
    axes[0].set_ylabel('Benign FPR (%)');axes[1].set_ylabel('Lateral detection (%)');axes[1].set_xlabel('Fitting seed suffix (202609xx)')
    axes[1].set_xticks(range(len(labels)),labels);axes[1].set_ylim(0,102);axes[0].set_ylim(bottom=0)
    from matplotlib.lines import Line2D
    axes[0].legend(handles=[Line2D([],[],color=c,marker=m,linestyle='',label=n) for c,m,n in [('#17365d','o','Natural argmax'),('#008597','s','Natural 1% threshold'),('#a4383b','D','Candidate when feasible')]],loc='upper right',frameon=False,fontsize=9)
    fig.suptitle('Primary verification: all ten fitting seeds',fontsize=12)
    fig.savefig(out/'primary_seeds.png',dpi=180);fig.savefig(out/'primary_seeds.pdf');plt.close(fig)
    if 'external' in evidence:
        ext=evidence['external'];metrics=[ext['metrics'][x] for x in ['cv_natural_argmax','cv_natural_benign_threshold']]
        fig,axes=plt.subplots(1,2,figsize=(9,3.6),layout='constrained');labels=['Natural\nargmax','Source 1%\nthreshold'];colors=['#17365d','#008597']
        values=[m['fp'] for m in metrics];axes[0].bar(labels,values,color=colors,width=.55)
        for i,v in enumerate(values):axes[0].text(i,v+700,f'{v:,}',ha='center',fontsize=11)
        axes[0].set_ylim(0,max(values)*1.22);axes[0].set_ylabel('False alerts / 100,000 benign groups')
        values=[m['per_stage']['LateralMovement']['detected'] for m in metrics];axes[1].bar(labels,values,color=colors,width=.55)
        for i,v in enumerate(values):axes[1].text(i,v+.12,f'{v} of 4',ha='center',fontsize=11)
        axes[1].set_ylim(0,4.8);axes[1].set_yticks(range(5));axes[1].set_ylabel('Detected lateral flows (one execution)')
        fig.suptitle('DEDALE: source thresholds did not transfer the 1% false-alarm target',fontsize=11)
        fig.savefig(out/'external_stress.png',dpi=180);fig.savefig(out/'external_stress.pdf');plt.close(fig)
    (out/'PLOTTED_VALUES.json').write_text(json.dumps(saved,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--results',required=True);p.add_argument('--out',required=True);a=p.parse_args();build(a.results,a.out)
