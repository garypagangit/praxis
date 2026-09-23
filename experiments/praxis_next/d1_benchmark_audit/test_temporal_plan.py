import numpy as np
import pytest
from .temporal_plan import plan


def fixture():
    n=24
    return dict(current=np.arange(n,dtype=float)[:,None], labels=np.tile([0,1,2],8),
        class_names=['normal','stage_a','stage_b'],benign_index=0,
        row_ids=np.array([f'row{i:02}' for i in range(n)]),
        event_hashes=np.array([f'event{i:02}' for i in range(n)]),
        groups=np.array(['past']*12+['later_a']*6+['later_b']*6),
        starts=np.arange(n)*10,ends=np.arange(n)*10+1,
        splits=np.array([0]*12+[2]*12),clock_validated=True,groups_validated=True)


def test_same_anchor_and_class_budgets():
    r=plan(**fixture())
    assert r['summary']['eligible_closed_set_contrast']
    assert r['summary']['anchor_counts']==[2,2,2]
    assert r['matched_counts'].tolist()==[4,4,4]
    assert not set(r['anchor'])&set(r['mixed_pool'])


def test_duplicate_fingerprint_removed_from_both_pools():
    d=fixture();d['current'][0]=d['current'][12]
    r=plan(**d)
    assert 0 not in r['past_pool'] and 0 not in r['mixed_pool']
    assert r['matched_counts'].tolist()==[3,4,4]


def test_missing_training_stage_is_reported_without_repair():
    d=fixture();d['labels'][:12]=np.tile([0,1],6)
    r=plan(**d)
    assert not r['summary']['eligible_closed_set_contrast']
    assert r['matched_counts'][2]==0
    assert r['summary']['anchor_counts'][2]==2


def test_future_event_and_unqualified_clock_are_rejected():
    d=fixture();d['ends'][0]=1000
    with pytest.raises(ValueError,match='finish before'):plan(**d)
    d=fixture();d['clock_validated']=False
    with pytest.raises(ValueError,match='qualified'):plan(**d)


def test_reserved_calibration_never_enters_pools():
    d=fixture();d['splits'][9:12]=1
    r=plan(**d)
    assert not set([9,10,11])&set(r['mixed_pool'])
    assert r['matched_counts'].tolist()==[3,3,3]


def test_row_reordering_does_not_change_anchor_identity():
    d=fixture();d['event_hashes'][:]='tied';r=plan(**d);want=set(d['row_ids'][r['anchor']])
    ix=np.arange(24)[::-1]
    for k in ['current','labels','row_ids','event_hashes','groups','starts','ends','splits']:d[k]=d[k][ix]
    actual=plan(**d)
    assert set(d['row_ids'][actual['anchor']])==want


@pytest.mark.parametrize('field,value',[
    ('groups',np.nan),('row_ids',None),('event_hashes',True),('groups','')])
def test_invalid_metadata_is_rejected_before_anchor_selection(field,value):
    d=fixture();d[field]=d[field].astype(object);d[field][13]=value
    with pytest.raises(ValueError):plan(**d)


@pytest.mark.parametrize('field,value',[
    ('benign_index',False),('clock_validated','yes'),('groups_validated',1),
    ('class_names',['normal','', 'stage_b'])])
def test_invalid_schema_or_qualification_assertions_are_rejected(field,value):
    d=fixture();d[field]=value
    with pytest.raises(ValueError):plan(**d)


def test_no_actual_later_training_pool_is_not_an_eligible_temporal_contrast():
    d=fixture()
    # Each later source group now contains one row per class: all become anchors.
    d['groups'][12:]=np.repeat(['late1','late2','late3','late4'],3)
    r=plan(**d)
    assert not r['summary']['eligible_closed_set_contrast']
    assert r['summary']['later_non_anchor_pool_after_purge']==0
    assert np.array_equal(r['past_pool'],r['mixed_pool'])
