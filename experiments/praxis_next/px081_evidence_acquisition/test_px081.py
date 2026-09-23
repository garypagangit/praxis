import importlib.util
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('px081',Path(__file__).with_name('run.py'))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def setup(n=3):
    gain={k:np.ones((4,n,2)) for k in ('harm','entropy')}
    return gain,np.ones((n,2),bool),np.broadcast_to([.25,.75],(n,2)).copy(),np.broadcast_to([.9,.1],(n,2)).copy()

def test_unavailable_queries_are_charged_and_not_delivered():
    g,a,d,o=setup(); a[:]=False
    t=m.replay('roles_first',g,a,d,o,3,'clean')
    assert np.all(t['spent']==3) and np.all(t['attempted']==3) and np.all(t['state']==0)

def test_late_query_spends_budget_and_cannot_change_evidence_state():
    g,a,d,o=setup(); d[:,0]=1.5
    t=m.replay('roles_first',g,a,d,o,3,'clean')
    assert np.all(t['spent']==1) and np.all(t['state']==0)
    assert np.all(t['actions'][:,1]==-1)

def test_budget_and_deadline_enforced_in_clean_condition():
    g,a,d,o=setup()
    for budget in (1,2,3):
        t=m.replay('history_first',g,a,d,o,budget,'clean')
        assert np.all(t['spent']<=budget)
        assert np.all(t['elapsed']<=1)
    assert np.all(m.replay('roles_first',g,a,d,o,3,'clean')['state']==3)

def test_hidden_actual_schedule_cannot_change_first_choice():
    g,a,d,o=setup(); first=m.replay('harm',g,a,d,o,3,'delayed_unavailable')['actions'][:,0]
    a[:]=False; d[:]=10
    second=m.replay('harm',g,a,d,o,3,'delayed_unavailable')['actions'][:,0]
    np.testing.assert_array_equal(first,second)

def test_unacquired_feature_values_cannot_enter_observed_state():
    d={k:np.ones((3,2)) for k in ('current','roles','history','wrong_history')}
    p=np.tile([.7,.1,.1,.1],(3,1)); idx=np.arange(3)
    before=m.observed_x(d,idx,0,p)
    d['roles'][:]=99; d['history'][:]=-55
    np.testing.assert_array_equal(before,m.observed_x(d,idx,0,p))
    assert not np.array_equal(m.observed_x(d,idx,1,p),m.observed_x({**d,'roles':np.zeros((3,2))},idx,1,p))

def test_low_expected_utility_can_choose_no_queries():
    g,a,d,o=setup(); g['harm'][:]=-1
    t=m.replay('harm',g,a,d,o,3,'clean')
    assert np.all(t['attempted']==0) and np.all(t['spent']==0)

def test_harm_target_represents_prespecified_stage_costs():
    y=np.array([0,2,3]); before=np.eye(4)[[1,0,3]]; after=np.eye(4)[[0,2,0]]
    np.testing.assert_array_equal(m.stage_loss(y,before)-m.stage_loss(y,after),[1,4,-4])

def test_schedule_reproducible_and_label_free():
    keys=np.array(['a','b','c']); x=m.schedule(keys,8101,'delayed_unavailable'); y=m.schedule(keys,8101,'delayed_unavailable')
    for a,b in zip(x,y): np.testing.assert_array_equal(a,b)
    assert np.any(x[1]>m.NOMINAL)

def test_same_budget_does_not_imply_same_acquired_information():
    g,a,d,o=setup(); a[:,1]=False
    t=m.replay('history_first',g,a,d,o,2,'clean')
    assert np.all(t['spent']==2) and np.all(t['state']==0)

def test_entropy_is_high_for_uniform_predictions():
    assert m.entropy(np.array([[.25]*4]))[0]>m.entropy(np.array([[1.,0,0,0]]))[0]
