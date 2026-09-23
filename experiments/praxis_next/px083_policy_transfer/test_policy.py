import numpy as np
from .run import features,target,score_arms,label

class Constant:
    def __init__(self,v):self.v=v
    def predict(self,x):return np.full(len(x),self.v)

def test_training_cost_changes_only_positive_errors():
    y=np.array([0,1,1,0]);c=np.array([.1,.9,.1,.9]);h=np.array([.9,.1,.9,.1])
    np.testing.assert_array_equal(target(y,c,h,1),[1,1,-1,-1])
    np.testing.assert_array_equal(target(y,c,h,4),[1,4,-4,-1])

def test_selector_uses_current_on_tie_and_cannot_alarm_invisible():
    c=np.array([.1,.2]);h=np.array([.9,.8]);observed=np.array([True,False])
    p,_,_,_=score_arms(c,h,observed,observed,c,Constant(0),Constant(-1))
    np.testing.assert_array_equal(p['ordinary_gate'],[.1,0]);np.testing.assert_array_equal(p['target_cost_gate'],[.9,0])
    assert all(v[1]==0 for v in p.values())

def test_features_no_label_or_dataset_argument():
    c=np.array([.3]);h=np.array([.7]);x=features(c,h,np.array([True]),np.array([True]))
    assert x.shape==(1,12) and np.isfinite(x).all()
    np.testing.assert_allclose(x[0,:4],[.3,.7,.4,.4])

def test_target_mapping_preserves_source_technique_meaning():
    assert label(['T1105: Ingress Tool Transfer'],'T1105')
    assert not label(['T1041: Exfiltration Over C2 Channel'],'T1105')
