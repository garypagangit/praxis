"""Rank saved detector scores at a declared node budget; tie policy is explicit."""
import argparse,pathlib,json,hashlib
import numpy as np
def rank(scores,budget,seed=17):
 scores=np.asarray(scores)
 if scores.ndim!=1 or not np.isfinite(scores).all() or not 1<=budget<=len(scores):raise ValueError('Require finite vector and valid integer node budget')
 # Random ordering is independent of labels and node IDs; equal-score groups use seed.
 tie_order=np.random.default_rng(seed).permutation(len(scores));order=tie_order[np.argsort(-scores[tie_order],kind='stable')];selected=order[:budget]
 return selected,{'nodes':len(scores),'budget':budget,'seed':seed,'boundary_score':float(scores[selected[-1]]),'boundary_ties':int((scores==scores[selected[-1]]).sum())}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--scores',type=pathlib.Path,required=True);p.add_argument('--key',default='score');p.add_argument('--budget',type=int,required=True);p.add_argument('--seed',type=int,default=17);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 z=np.load(a.scores,allow_pickle=False);selected,receipt=rank(z[a.key],a.budget,a.seed);receipt['selected_node_indices']=selected.tolist();receipt['input_sha256']=hashlib.sha256(a.scores.read_bytes()).hexdigest();a.output.write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='selected_node_indices'}))
