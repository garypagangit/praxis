import json,pathlib,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=pathlib.Path(__file__).resolve().parent;r=json.loads((P/'evidence/RESULTS.json').read_text());s=json.loads((P/'evidence/SUMMARY.json').read_text())
fig,axes=plt.subplots(1,3,figsize=(17,5.6),gridspec_kw={'width_ratios':[1.5,1,1]},layout='constrained')
xs=[x for x in r if x['study']=='version' and x['model']=='lexical'];names=[x['setting'] for x in xs];y=np.arange(len(xs))
axes[0].barh(y,[100*x['accuracy'] for x in xs],color='#285f7e');axes[0].set_yticks(y,names);axes[0].invert_yaxis();axes[0].set_xlim(0,105);axes[0].set_xlabel('Accuracy on withheld version (%)');axes[0].set_title('Familiar family, unfamiliar version')
for i,x in enumerate(xs):axes[0].text(100*x['accuracy']+1,i,f"{100*x['accuracy']:.1f}",va='center',fontsize=9)
for ax,key,title in [(axes[1],'tie_expected_budget_recall','Useful detections at a 1% node budget'),(axes[2],'threshold_fpr','False alarms at the fixed threshold')]:
 for j,(view,label,color) in enumerate([('clean','Complete graph','#285f7e'),('drop_0.5_mask_20260920','50% edge loss','#cf7842')]):
  vals=[100*next(x for x in s['graph'] if x['dataset']==d and x['view']==view)[key] for d in ['cadets','theia']];pos=np.arange(2)+(j-.5)*.35;bars=ax.bar(pos,vals,.35,label=label,color=color);ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=9)
 ax.set_xticks([0,1],['CADETS','THEIA']);ax.set_ylim(0,15 if key.startswith('tie') else 72);ax.set_title(title,fontsize=11);ax.set_ylabel('Recall (%)' if key.startswith('tie') else 'False-positive rate (%)');ax.legend(loc='upper center',fontsize=8,frameon=False)
for ax in axes:ax.spines[['top','right']].set_visible(False)
fig.suptitle('Where attribution and detection stop being dependable',fontsize=16)
fig.supxlabel('Exploratory existing-data results. Graph panels: frozen GIN/KNN, three-seed means; budget recall averages uniform selection within score ties. No deployment validation.',fontsize=9)
fig.savefig(P/'OVERVIEW.png',dpi=170);plt.close(fig)
print('figure created')
