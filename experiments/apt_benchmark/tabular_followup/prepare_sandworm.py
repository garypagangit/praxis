"""Prepare fresh external binary transfer data; do not fit or select any model."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CSV_SHA='c2669e324fe94076a148d2942e86be97acfd7f39322e89bf267c554c530330b4'
SOURCE_DATA_SHA='8e8a7474d4db03b78977a3c6a48be083d60d7648dd7548788037db721e80e565'
SOURCE_MANIFEST_SHA='772edbce9548a1dc87a0e9dd835f9002dfd5a2bb7b3cc37de212d7b3c43791e3'
EXPECTED_LABEL_COUNTS={'Normal':2096,'PHP_insecure_intrusion':16,'smb_intrusion':8,'rdp_intrusion':7,'ssh_intrusion':5,'remote_system_discovery':1}


def sha(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def canonical_features(frame,features):
    values=frame[features].apply(pd.to_numeric,errors='raise').to_numpy(dtype='<f8',copy=True)
    nonfinite=~np.isfinite(values);values[nonfinite]=np.nan;values[values==0]=0.0
    fingerprints=np.asarray([hashlib.sha256(row.tobytes()).hexdigest() for row in values],dtype='U64')
    return values,fingerprints,int(nonfinite.sum())


def unique_view(values,fingerprints,procedures):
    table=pd.DataFrame({'fingerprint':fingerprints,'procedure':procedures})
    if (table.groupby('fingerprint')['procedure'].nunique()>1).any():
        raise ValueError('Conflicting procedure labels within identical predictor rows; requalify, never silently relabel.')
    first=table.drop_duplicates('fingerprint').sort_values('fingerprint').index.to_numpy(dtype=np.int64)
    unique_fingerprints=fingerprints[first]
    raw_to_unique=np.searchsorted(unique_fingerprints,fingerprints).astype(np.int64)
    if not np.array_equal(unique_fingerprints[raw_to_unique],fingerprints):raise ValueError('Raw-to-unique reconstruction failed.')
    return first,raw_to_unique


def prepare(source_csv,scvic_prepared,output):
    if output.exists() and any(output.iterdir()):raise ValueError('Use a fresh output; prepared evidence is immutable.')
    if sha(source_csv)!=CSV_SHA:raise ValueError('Author source CSV hash changed.')
    source_data=scvic_prepared/'DATA.npz';source_manifest=scvic_prepared/'MANIFEST.json'
    if sha(source_data)!=SOURCE_DATA_SHA or sha(source_manifest)!=SOURCE_MANIFEST_SHA:raise ValueError('SCVIC source binding changed.')
    manifest=json.loads(source_manifest.read_text(encoding='utf-8'));features=manifest['feature_columns']
    frame=pd.read_csv(source_csv);frame.columns=frame.columns.str.strip()
    if frame['Label'].value_counts().to_dict()!=EXPECTED_LABEL_COUNTS:raise ValueError('Author label counts changed.')
    if len(features)!=73 or any(c not in frame for c in features):raise ValueError('Required source predictor schema missing.')
    values,fingerprints,bad=canonical_features(frame,features);procedures=np.asarray(frame['Label'].astype(str),dtype=str)
    first,raw_to_unique=unique_view(values,fingerprints,procedures)
    with np.load(source_data,allow_pickle=False) as archive:
        source_fingerprints=set(archive['group_sha256'].tolist())
        if archive['feature_names'].tolist()!=features:raise ValueError('Source manifest and array feature order differ.')
    overlap=int(sum(g in source_fingerprints for g in fingerprints))
    if overlap:raise ValueError('External source shares exact predictors with SCVIC; requalify before transfer.')
    output.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(output/'DATA.npz',X=values[first],y_binary=(procedures[first]!='Normal').astype(np.int8),
                        procedure_labels=procedures[first],group_sha256=fingerprints[first],
                        feature_names=np.asarray(features),raw_to_unique=raw_to_unique)
    time=pd.to_datetime(frame['Timestamp'],format='%Y-%m-%d %H:%M:%S.%f',errors='raise')
    receipt={'schema_version':1,'dataset':'APT Sandworm Dataset v1','dataset_doi':'10.5281/zenodo.16911636',
             'paper_doi':'10.1016/j.future.2025.108308','source_csv_sha256':CSV_SHA,'source_csv_bytes':source_csv.stat().st_size,
             'source_data_npz_sha256':SOURCE_DATA_SHA,'source_manifest_sha256':SOURCE_MANIFEST_SHA,
             'target_data_npz_sha256':sha(output/'DATA.npz'),'feature_names':features,'feature_count':len(features),
             'raw_rows':len(frame),'unique_rows':len(first),'raw_procedure_counts':EXPECTED_LABEL_COUNTS,
             'unique_procedure_counts':{str(label):int(n) for label,n in pd.Series(procedures[first]).value_counts().items()},
             'binary_labels':{'0':'Normal','1':'Any author-labeled attack procedure'},
             'duplicate_rows':len(frame)-len(first),'conflicting_procedure_groups':0,'exact_scvic_overlap_rows':overlap,
             'nonfinite_predictor_cells':bad,'unique_query_order':'Ascending SHA256 of the canonical ordered73 float64 predictor values; labels not used in ordering',
             'raw_sensitivity':'Use raw_to_unique to reweight predictions from the fixed unique-query execution. This does not claim that querying raw batches would reproduce identical foundation probabilities.',
             'first_timestamp':str(time.min()),'last_timestamp':str(time.max()),'capture_days':int(time.dt.date.nunique()),
             'dropped_columns':[c for c in frame if c not in features],'preparation_fits':0,
             'preprocessing':'Exact E1 ordered predictor names; numeric conversion; nonfinite->canonical NaN; signedzero->positivezero. No learned transform or external-data imputation/scaling. Source-fitted imputer required at inference.',
             'rights':'API and license field CC-BY4.0; landing copyright field CC-BY-NC-ND4.0. Private noncommercial evaluation; aggregates only; raw and derived data are not published.',
             'adapter_sha256':sha(Path(__file__)),
             'scope':'Fresh cross-dataset binary transfer only; no SCVIC stage labels are inferred from Sandworm procedures.',
             'feature_semantics_limit':'CICFlowMeter names and documented meanings align; exact extractor revisions/settings and bitwise implementation equivalence remain unqualified.'}
    (output/'MANIFEST.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:receipt[k] for k in ('raw_rows','unique_rows','unique_procedure_counts','exact_scvic_overlap_rows','target_data_npz_sha256')},indent=2))
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-csv',type=Path,required=True)
    parser.add_argument('--scvic-prepared',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();prepare(args.source_csv,args.scvic_prepared,args.output)
