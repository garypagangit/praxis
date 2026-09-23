"""Meaningful synthetic checks of causal and selector invariants; no real fits."""
import numpy as np
from .run import gate_target, choose, selector_features, history_age, observe, COST
from experiments.apt_benchmark.host_history_exfil.context import history_features

def test_stage_cost_target_and_ties():
    y=np.array([0,2,3,1]);a=np.eye(4)[[0,2,0,1]];b=np.eye(4)[[1,0,3,1]]
    np.testing.assert_array_equal(gate_target(y,a,b,COST),[1,4,-4,0])
    np.testing.assert_array_equal(choose(a,b,np.array([False,False,True,False])),np.eye(4)[[0,2,3,1]])

def test_gate_has_observables_only():
    p=np.array([[.1,.2,.3,.4]]);q=p[:,::-1];s=np.array([[2.,1.]])
    x=selector_features(p,q,s)
    assert x.shape==(1,20) and np.isfinite(x).all()
    np.testing.assert_array_equal(x[:,-2:],s)

def test_missing_is_explicit_and_not_silent_zero():
    d=dict(history=np.ones((2,36)),latest_history_end=np.array([1.,2.]),start=np.array([3.,4.]),group_sha256=np.array(['00000000','00000001']))
    h,s=observe(d,np.arange(2),'missing_half',None,None)
    assert np.all(h[0]==0) and np.all(h[1,:36]==1) and s[1,1]==1
    h,s=observe(d,np.arange(2),'missing_all',None,None)
    assert not h.any() and not s.any()

def test_relative_age_no_absolute_clock():
    np.testing.assert_allclose(history_age(np.array([10000.,20000.]),np.array([9000.,-1.])),[np.log(2),0])
    np.testing.assert_allclose(history_age(np.array([10000.]),np.array([9000.])),history_age(np.array([900000.]),np.array([899000.])))

def test_stale_snapshot_excludes_recent_and_equal_cutoff():
    start=np.array([0.,200000.,300010.,400000.])+1000000.;end=np.array([10.,200010.,300020.,400010.])+1000000.
    src=np.array(['10.1.1.1']*4);dst=np.array(['10.1.1.2']*4);v=np.ones(4)
    h,_,latest,_=history_features(start-300000,end,src,dst,v,v,np.zeros(4))
    assert np.all(latest<start-300000)
    assert h[2,0]==0 # earlier first event ends exactly at snapshot cutoff
    np.testing.assert_allclose(h[3,0],np.log(2))

def test_future_change_does_not_change_stale_snapshot():
    start=np.array([0.,400000.,900000.])+1000000.;end=start+10;src=np.array(['a']*3);dst=np.array(['b']*3);v=np.ones(3)
    h,*_=history_features(start-300000,end,src,dst,v,v,v)
    newer=v.copy();newer[2]=1e8
    h2,*_=history_features(start-300000,end,src,dst,newer,newer,newer)
    np.testing.assert_array_equal(h[:2],h2[:2])
