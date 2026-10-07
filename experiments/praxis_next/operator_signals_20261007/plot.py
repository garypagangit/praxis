"""Optional publication figure; run with matplotlib (not used for experiment fits)."""
import json,statistics
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

p=Path(__file__).resolve().parent;r=json.loads((p/'evidence/RESULTS.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
colors=['#176b87','#c36b24'];x=np.arange(4);w=.36
for j,(kind,label) in enumerate([('lexical','Commands'),('lexical_recovery','Commands + behavior')]):
 vals=[100*statistics.mean(z['macro_f1'] for z in r if z['study']=='S1' and z['setting'].startswith(g+'_') and z['model']==kind) for g in ['iid','env','prompt','cells']]
 bars=axes[0].bar(x+(j-.5)*w,vals,w,label=label,color=colors[j]);axes[0].bar_label(bars,fmt='%.1f',fontsize=9)
axes[0].set_xticks(x,['Ordinary\nsplits','Unseen\nenvironments','Unseen\nprompts','Unseen\ncombinations'])
axes[0].set_title('Family identification depends on context',fontsize=12)
for j,(setting,label) in enumerate([('iid_17','Ordinary split'),('env_backend_pool_cowrie','Unseen environment')]):
 keys=[f'S1|{setting}|lexical',f'S2_frozen|{setting}/verbs|lexical',f'S2_adapted|{setting}/verbs|lexical']
 vals=[100*next(z['macro_f1'] for z in r if z['key']==k) for k in keys]
 bars=axes[1].bar(np.arange(3)+(j-.5)*w,vals,w,label=label,color=colors[j]);axes[1].bar_label(bars,fmt='%.1f',fontsize=9)
axes[1].set_xticks(np.arange(3),['Complete\ncommands','Verbs only:\nfrozen model','Verbs only:\nretrained'])
axes[1].set_title('Training on the observed log view helps',fontsize=12)
for ax in axes:
 ax.set_ylim(0,112);ax.set_yticks(np.arange(0,101,20));ax.set_ylabel('Macro F1 (%)');ax.legend(loc='upper center',bbox_to_anchor=(.5,1.01),ncol=2,fontsize=9,frameon=False)
 ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True)
fig.suptitle('Existing-data exploration: four known AI families',fontsize=15)
fig.supxlabel('Point estimates on selected Honey sessions; synthetic log reduction. These are not human-versus-AI detection rates.',fontsize=9)
fig.savefig(p/'OVERVIEW.png',dpi=170)
fig.savefig(p/'OVERVIEW.svg',metadata={'Title':'Existing-data AI family fingerprint experiments','Description':'Known-family macro F1 by context and log representation; not human-versus-AI detection.'})
plt.close(fig)
svg=p/'OVERVIEW.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
print('figure created')
