"""Freeze a deduplicated SCVIC within-training development split; fit no model.

This is NOT the author test set, a chronological split, or an incident-held-out
evaluation. Three-way 60/20/20 allocation is label stratified at unique feature
group level. Features and preprocessing exclusions are fixed before fitting.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXCLUDE = {
    'Flow ID', 'Src IP', 'Src Port', 'Dst IP', 'Dst Port', 'Timestamp',
    'Activity', 'Stage', 'Label', 'Idle Mean', 'Idle Std', 'Idle Max', 'Idle Min',
}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare(source: Path, output: Path, seed=20260921):
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f'Refusing to replace frozen output: {output}')
    df = pd.read_csv(source, low_memory=False)
    df.columns = df.columns.str.strip()
    if df['Label'].isna().any():
        raise ValueError('Unexpected missing labels')
    features = [c for c in df.columns if c not in EXCLUDE and not c.startswith('Unnamed')]
    values = df[features].apply(pd.to_numeric, errors='raise').to_numpy(dtype='<f8',copy=True)
    bad_cells = ~np.isfinite(values)
    bad_rows = bad_cells.any(axis=1)
    # Fixed missing-value convention before fingerprints; no fitted imputation.
    values[bad_cells] = np.nan
    values[values == 0] = 0.0  # canonicalize signed zero
    groups = np.array([hashlib.sha256(row.tobytes()).hexdigest() for row in values], dtype='U64')
    labels = df['Label'].astype(str).str.strip().to_numpy()
    table = pd.DataFrame({'group':groups,'label':labels})
    conflict = table.groupby('group')['label'].nunique()
    conflict_ids = set(conflict[conflict > 1].index)
    conflict_mask = table['group'].isin(conflict_ids).to_numpy()
    kept_mask = (~conflict_mask) & (~table['group'].duplicated().to_numpy())
    values, labels, groups = values[kept_mask], labels[kept_mask], groups[kept_mask]
    classes = sorted(set(labels.tolist()))
    y = np.array([classes.index(label) for label in labels],dtype=np.int32)
    split = np.full(len(y), -1, dtype=np.int8)
    for i, label in enumerate(classes):
        ids = np.flatnonzero(y == i)
        ids = sorted(ids, key=lambda j:hashlib.sha256(f'{seed}|{groups[j]}'.encode()).digest())
        nfit, ncal = int(.6*len(ids)), int(.2*len(ids))
        split[ids[:nfit]] = 0
        split[ids[nfit:nfit+ncal]] = 1
        split[ids[nfit+ncal:]] = 2
    assert np.all(split >= 0)
    assert len(set(groups)) == len(groups)
    counts = {name:{label:int(np.sum((y==i)&(split==j))) for i,label in enumerate(classes)}
              for j,name in enumerate(['fit','calibration','test'])}
    minimum_fit = min(counts['fit'].values())
    output.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output/'DATA.npz',X=values,y=y,split=split,group_sha256=groups,
                        classes=np.array(classes),feature_names=np.array(features))
    receipt = {
        'schema_version':1,'dataset':'SCVIC-APT-2021 local author training CSV',
        'evaluation_scope':'within-training feature-deduplicated development only',
        'source':{'path':str(source),'sha256':digest(source),'bytes':source.stat().st_size},
        'split_seed':seed,'split_allocation':'60% fit / 20% calibration / remaining test per label; SHA256-ranked unique feature groups',
        'split_codes':{'fit':0,'calibration':1,'test':2},
        'raw_rows':int(len(df)), 'retained_unique_feature_rows':int(len(values)),
        'excluded_columns':sorted(set(df.columns)&EXCLUDE),'feature_columns':features,
        'feature_count':len(features),'classes':classes,
        'raw_stage_counts':df['Label'].value_counts().sort_index().to_dict(),
        'nonfinite_feature_cells_canonicalized_to_nan':int(bad_cells.sum()),
        'rows_with_nonfinite_features_before_dedup':int(bad_rows.sum()),
        'conflicting_feature_groups_removed':len(conflict_ids),
        'rows_in_conflicting_feature_groups_removed':int(conflict_mask.sum()),
        'duplicate_rows_removed_excluding_conflicts':int((~conflict_mask).sum()-kept_mask.sum()),
        'split_stage_counts':counts, 'max_feasible_equal_per_class_fit_budget':minimum_fit,
        'requested_fit_budgets_feasible':{str(n):n<=minimum_fit for n in [32,64,128,256,512,1024]},
        'cross_split_feature_duplicate_count':0,
        'data_npz_sha256':digest(output/'DATA.npz'),
        'preprocessing_policy':'No fitted imputation, scaling or feature selection in preparation. Models must fit transforms on their selected fit rows only. All four Idle summaries excluded due to epoch-scale values.',
        'limitations':[
            'Author test CSV is not present or acquired; this is not an author holdout result.',
            'No execution-round identifiers qualified. Grouping removes exact predictor duplicates only, not all correlated incident or near-duplicate flows.',
            'No chronological, independent incident, population coverage, next-stage, or early-warning claim.',
            'Calibration/test class imbalance follows deduplicated source proportions; balanced fit budgets alter training priors.',
            'InitialCompromise has very small calibration/test support; class-conditional 95% conformal sets can be vacuous.',
            'Do not select model or hyperparameters using test. If calibration selects models or thresholds, require separate conformal calibration or disclaim its validity.',
        ],
    }
    (output/'MANIFEST.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
    print(json.dumps(receipt,indent=2))
    return receipt


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('C:/Users/garyp/Downloads/SCVIC-APT-2021-Training.csv'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,default=20260921)
    args=parser.parse_args()
    prepare(args.source,args.output,args.seed)
