import numpy as np
from .run import anchor_rows, fingerprints, sample, paired_bootstrap

def test_anchor_only_later_rows_and_at_least_one_each_supported_capture_class():
    d={'capture':np.repeat([0,6,7],8),'split':np.repeat([0,2,2],8),'y':np.tile(np.repeat(np.arange(4),2),3),'group_sha256':np.array([f'{i:064x}' for i in range(24)])}
    a=anchor_rows(d)
    assert len(a)==8 and np.all(d['split'][a]==2)
    assert np.array_equal(np.bincount(d['y'][a]),[2,2,2,2])

def test_feature_hash_excludes_label_and_normalizes_signed_zero():
    x=np.array([[0.,2.],[-0.,2.],[0.,3.]])
    h=fingerprints(x)
    assert h[0]==h[1] and h[0]!=h[2]

def test_sampling_matches_counts_and_cannot_include_outside_pool():
    d={'y':np.repeat(np.arange(4),6),'group_sha256':np.array([f'{i:064x}' for i in range(24)])}
    pool=np.array([i for i in range(24) if i%6!=0])
    a=sample(d,pool,[2,3,4,5],7)
    assert np.array_equal(np.bincount(d['y'][a]),[2,3,4,5])
    assert set(a)<=set(pool) and len(set(a))==len(a)

def test_paired_identical_predictions_have_zero_difference_and_interval():
    y=np.tile(np.arange(4),5);p=np.eye(4)[y];capture=np.repeat(np.arange(5),4)
    result=paired_bootstrap(y,p,p,capture,7)
    assert result['difference_mixed_minus_past']==0
    assert result['conditional_capture_bootstrap_95_interval']==[0,0]
