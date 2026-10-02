"""Render one diagnosed flow and a benign control; charts add no inference results."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
HERE=Path(__file__).resolve().parent;OUT=Path('C:/w/px098_local_followup_20261002')
def main():
    d=dict(np.load('C:/w/apt_benchmark_data_20260920/host_history_exfil_v1/prepared/DATA.npz'))
    diag=json.loads((HERE/'FLOW_DIAGNOSTICS.json').read_text())
    misses=sorted({r['flow_index'] for r in diag},key=lambda i:str(d['group_sha256'][i]))
    parent=pd.read_pickle(OUT/'parents.pkl')
    with np.load(OUT/'host_hour.npz') as z:
        pure=parent.benign.to_numpy(dtype=bool)[z['pid'][z['flowgid']]]
    benign=sorted(np.flatnonzero((d['split']==2)&pure),key=lambda i:str(d['group_sha256'][i]))
    views=['host_hour','host_5min','peer_service_hour','peer_service_5min']
    for category,i in [('diagnostic',misses[0]),('benign',int(benign[0]))]:
        fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
        for ax,view in zip(axes.flat,views):
            with np.load(OUT/(view+'.npz')) as z:
                j=z['flowgid'][i];matrix=z['raw'][j];fine=len(matrix)==1
            ticks=np.arange(len(matrix))*5+2.5
            ax.bar(ticks-1,matrix[:,0],width=2,label='Outgoing bytes');ax.bar(ticks+1,matrix[:,1],width=2,label='Incoming bytes')
            ax.set_title(view.replace('_',' '));ax.set_xlabel('Minutes since window start');ax.set_ylabel('Completed-flow bytes')
            ax.set_xlim(0,5 if fine else 60);ax.ticklabel_format(axis='y',style='sci',scilimits=(0,0));ax.legend(fontsize=8)
        fig.suptitle('Same endpoint traffic under four grouping rules ('+category+' example)\nBars show five-minute totals; horizontal offsets separate directions.')
        fig.savefig(HERE/(category+'_views.png'),dpi=135);plt.close(fig)
    rows=json.loads((HERE/'RESULTS.json').read_text())['rows']
    fig,ax=plt.subplots(figsize=(8,5),layout='constrained')
    for r in rows:
        x=r['base']['added_benign'];y=r['base']['added_exfil'];ax.scatter(x,y,s=70)
        ax.annotate(r['view'].replace('_',' '),(x,y),xytext=(5,8),textcoords='offset points',fontsize=9)
    ax.axvline(190,color='firebrick',linestyle='--',label='1 percentage-point research limit (190 alerts)')
    ax.set_xlim(0,750);ax.set_ylim(0,13);ax.set_xlabel('Additional benign host-hour alerts');ax.set_ylabel('Additional exfiltration-positive host-hours warned')
    ax.set_title('Added warnings beyond the original three-member gate');ax.legend(loc='lower right',fontsize=8)
    fig.savefig(HERE/'tradeoff.png',dpi=135);plt.close(fig)
    (HERE/'VISUAL_SELECTION.json').write_text(json.dumps({'diagnostic_flow_index':int(misses[0]),'benign_flow_index':int(benign[0]),
        'benign_control_entire_host_hour_benign':True,'scope':'Illustrative byte panels; models use all five measures. No VLM inference.'},indent=2)+'\n')
if __name__=='__main__':main()
