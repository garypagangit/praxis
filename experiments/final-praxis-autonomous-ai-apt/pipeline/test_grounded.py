import json
from pathlib import Path
import numpy as np
import pandas as pd
from grounded_synthetic import command_stats, entropy, digest
from experiment import FEATURES, validate

HERE=Path(__file__).parent

def test_command_statistics_known_sequence():
    x=command_stats(['ls secret']*4+['cat secret']*4)
    assert x[0]==.25 and x[2]==6/7 and x[3]==2 and x[4]==0
    assert entropy(['a','b'])==1
    assert command_stats(['ls']) is None

def test_grounded_artifact_bounds_and_null_integrity():
    base=HERE/'grounded_20261019_final'
    d=pd.read_csv(base/'trials.csv'); n=pd.read_csv(base/'null_labels.csv')
    validate(d); validate(n)
    pd.testing.assert_frame_equal(d[FEATURES],n[FEATURES])
    assert len(d)==880 and d.dataset_kind.eq('synthetic').all()
    assert (d[FEATURES]>=0).all().all()
    for f in ['command_diversity','retry_fraction','outbound_fraction','tool_pattern_fraction']:
        assert d[f].between(0,1).all()
    assert d.peak_concurrency.ge(1).all()
    for part in ['train','validation','test_seen','test_unseen']:
        assert n[n.partition==part].arm.value_counts().nunique()==1
    manifest=json.loads((base/'source_manifest.json').read_text(encoding='utf-8'))
    assert manifest['generator_sha256']==digest(HERE/'grounded_synthetic.py')
    for file,sha in manifest['output_sha256'].items(): assert digest(base/file)==sha
