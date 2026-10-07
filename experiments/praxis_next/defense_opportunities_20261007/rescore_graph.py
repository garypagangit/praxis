import argparse,pathlib,json
import numpy as np
from screen import HERE,save,sha
def run(root):
 out=[];sources={};decisions=HERE/'evidence/graph_existing_decisions';decisions.mkdir(exist_ok=True)
 for ds in ['cadets','theia']:
  p=root/ds;report=json.loads((p/'RESULTS.json').read_text());sources[ds+'/RESULTS.json']=sha(p/'RESULTS.json')
  for seed in [101,211,307]:
   for view in ['clean','drop_0.5_mask_20260920']:
    f=p/'private'/f'predictions_{seed}_{view}.npz';assert sha(f)==report['private_artifact_sha256'][f.name];sources[ds+'/'+f.name]=sha(f);z=np.load(f);y=z['y'];budget=int(np.ceil(.01*len(y)))
    for model in ['local_knn','mlp_knn','gin_knn']:
     s=z['score_'+model];order=np.lexsort((np.arange(len(y)),-s));top=order[:budget];k=z['margin_'+model]>=0
     out.append({'dataset':ds,'seed':seed,'view':view,'model':model,'n':len(y),'positives':int(y.sum()),'budget':budget,'budget_tp':int(y[top].sum()),'budget_recall':float(y[top].sum()/y.sum()),'budget_precision':float(y[top].mean()),'boundary_ties':int((s==s[top[-1]]).sum()),'threshold_alerts':int(k.sum()),'threshold_recall':float(k[y==1].mean()),'threshold_fpr':float(k[y==0].mean())})
     above=s>s[top[-1]];tie=s==s[top[-1]];need=budget-int(above.sum());tp=int(y[above].sum());positives=int(y[tie].sum());total=int(tie.sum())
     out[-1].update(tie_expected_budget_recall=float((tp+need*positives/total)/y.sum()),tie_min_budget_recall=float((tp+max(0,need-(total-positives)))/y.sum()),tie_max_budget_recall=float((tp+min(need,positives))/y.sum()),boundary_needed=need,boundary_positives=positives,strictly_above_tp=tp)
     np.savez_compressed(decisions/f'{ds}_{seed}_{view}_{model}.npz',top=top.astype(np.int32),threshold_flags=np.packbits(k),labels=np.packbits(y.astype(bool)),n=np.array(len(y)),above=np.packbits(above),tie=np.packbits(tie))
 save(HERE/'evidence/GRAPH_EXISTING.json',{'scope':'New budget analysis of previously fitted saved scores; not new model fitting or independent confirmation','results':out,'sources':sources,'code_sha256':sha(pathlib.Path(__file__))})
 print('rescored',len(out))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--data',type=pathlib.Path,required=True);run(p.parse_args().data)
