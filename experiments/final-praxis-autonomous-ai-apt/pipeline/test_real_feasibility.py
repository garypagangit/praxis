import numpy as np
import pandas as pd
from real_archive_feasibility import extract,weights,evaluate,ALL,N

def test_fixed_window_ignores_later_commands_and_rejects_short():
    cs=['ls -l']*10
    assert extract(cs)==extract(cs+['curl example'])
    assert extract(cs[:9]) is None
    assert len(extract(cs))==len(ALL)

def test_group_weighting_prevents_large_groups_dominating():
    d=pd.DataFrame({'group':['a']*20+['b']+['c']*3,'label':[0]*21+[1]*3})
    w=weights(d)
    assert np.isclose(w[:20].sum(),w[20])
    assert np.isclose(w[:21].sum(),w[21:].sum())
    assert evaluate(d,d.label.to_numpy())['group_balanced_accuracy']==1
    assert evaluate(d,np.zeros(len(d)))['group_balanced_accuracy']==.5
