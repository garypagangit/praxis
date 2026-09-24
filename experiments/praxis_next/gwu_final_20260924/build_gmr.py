"""Draw the current study's GMR using the reference's numbered What/Why/How cards."""
from pathlib import Path
import hashlib
import json
import textwrap
import shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle

HERE=Path(__file__).resolve().parent
FIG=HERE/'figures'
FIG.mkdir(parents=True,exist_ok=True)
cards=[
 ('Qualify the evidence', '#00616d',
  'Inspect datasets, labels and time records.',
  'Confirm that each source supports the question.',
  'Record versions, class counts and dependencies.'),
 ('Prepare the evaluation', '#087e86',
  'Build current-flow, role and history features.',
  'Compare methods on the same later records.',
  'Use forward folds and matched class budgets.'),
 ('Fit the comparison models', '#087e86',
  'Fit flow experts and evidence selectors.',
  'Test how information choices change decisions.',
  'Use fixed LightGBM settings and three seeds.'),
 ('Record error destinations', '#00616d',
  'Measure correct stage, wrong stage and benign.',
  'Expose missed warnings behind overall scores.',
  'Report stage recall, warning recall and false alerts.'),
 ('Check uncertainty and scope', '#aa7b05',
  'Reanalyse paired predictions and source support.',
  'Show variation, repeated evidence and limits.',
  'Use capture resampling and seed/capture omissions.'),
 ('Deliver the praxis evidence', '#206d43',
  'Assemble findings, figures, tables and code.',
  'Make the evaluation procedure inspectable.',
  'Verify public arithmetic and bind artifact hashes.')]

fig=plt.figure(figsize=(6,7.45),facecolor='white')
ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,6);ax.set_ylim(0,7.45);ax.axis('off')
for index,(title,color,what,why,how) in enumerate(cards):
    col=index%2;row=index//2;x=.02+col*3.02;y=7.42-(row+1)*2.46
    w=2.92;h=2.37
    ax.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor='#d0d8dc',lw=.6))
    ax.add_patch(Rectangle((x,y+h-.42),w,.42,facecolor=color,edgecolor='none'))
    ax.add_patch(Circle((x+.2,y+h-.21),.14,facecolor='white',edgecolor='none'))
    ax.text(x+.2,y+h-.21,str(index+1),color=color,fontsize=10,fontweight='bold',ha='center',va='center')
    ax.text(x+.42,y+h-.21,title,color='white',fontsize=9.6,fontweight='bold',ha='left',va='center')
    for j,(label,body) in enumerate([('What?',what),('Why?',why),('How?',how)]):
        top=y+h-.55-j*.59
        if j==0:
            ax.add_patch(Rectangle((x+.01,top-.46),w-.02,.60,facecolor='#eaf2f5',edgecolor='none'))
        ax.text(x+.11,top,label,color=color,fontweight='bold',fontsize=9,va='top')
        ax.text(x+.11,top-.18,textwrap.fill(body,36),color='#1c252d',fontsize=9,linespacing=1.2,va='top')
fig.savefig(FIG/'gmr_current.png',dpi=300)
fig.savefig(FIG/'gmr_current.pdf')
fig.savefig(FIG/'gmr_current.svg')
plt.close(fig)
original=Path('C:/w/gwu_reference_qa_20260924/original_gmr.png')
assert hashlib.sha256(original.read_bytes()).hexdigest()=='5d055b17fd9ff91041a9a12aa6d909931e250f7d838e3cc8084b6cb84a128f50'
shutil.copyfile(original,FIG/'gmr_original_reference.png')
receipt={'adaptation':'New study diagram using numbered What/Why/How card convention; historical image reproduced unchanged for reference appendix only.',
 'original_source_sha256':'5873d64833e648da6226e56258e043e2cc3dae0f22afca2da478b6e0dac3807c',
 'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FIG.glob('gmr_*')},
 'new_scientific_calculations':0}
(HERE/'GMR_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
