"""Exactly seven new final roles classifiers; no selector or OOF fits."""
import time,warnings
import joblib,numpy as np
from common import *
def main():
    verify();assert not (HERE/'partB/FIT_LOG.json').exists();px=pxmodule();d=dict(np.load(DATA));train=np.flatnonzero(d['split']==0);test=np.flatnonzero(d['split']==2);rows=[]
    assert np.max(d['end'][train])<np.min(d['start'][d['split']==1])
    for seed in SEEDS[3:]:
        dest=PRIVATE/f'roles_{seed}.joblib';assert not dest.exists();start=time.monotonic();ids=px.capped(train,d['y'],seed)
        assert not np.intersect1d(d['group_sha256'][ids],d['group_sha256'][test]).size
        model=px.classifier(seed);model.fit(px.subset_x(d,ids,1),d['y'][ids]);p=px.predict(model,px.subset_x(d,test,1))
        joblib.dump(model,dest);np.save(PRIVATE/f'roles_{seed}.npy',p);np.save(PRIVATE/f'train_{seed}.npy',ids)
        rows.append({'seed':seed,'kind':'final_roles','seconds':time.monotonic()-start,'training_rows':len(ids),'class_counts':np.bincount(d['y'][ids],minlength=4).tolist(),'captures':np.unique(d['capture'][ids]).tolist(),'training_indices_sha256':ah(ids),'training_events_sha256':ah(d['group_sha256'][ids]),'model_sha256':sha(dest),'probabilities_sha256':sha(PRIVATE/f'roles_{seed}.npy'),'params':model.get_params()})
        save(HERE/'partB/FIT_LOG.json',{'completed_fits':len(rows),'fits':rows,'forward_folds':'Not refitted: no new selector; seven final-fit cap.'});print('FIT',seed,round(rows[-1]['seconds'],2),flush=True)
    assert len(rows)==7
if __name__=='__main__':main()
