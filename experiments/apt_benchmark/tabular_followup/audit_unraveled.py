"""Qualify existing author Unraveled CSVs; no split selection, fitting or scoring."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess

import pandas as pd


def digest(path):
    sha=hashlib.sha256();blob=hashlib.sha1()
    blob.update(f'blob {path.stat().st_size}\0'.encode())
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024*1024),b''):
            sha.update(chunk);blob.update(chunk)
    return sha.hexdigest(),blob.hexdigest()


def audit(source_repo:Path,cache_metadata:Path,output:Path):
    if output.exists():raise ValueError('Preserve existing qualification receipt; use a fresh output.')
    source_repo=source_repo.resolve();root=source_repo/'data/network-flows'
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source_repo,text=True).strip()
    tree=subprocess.check_output(['git','ls-tree','-r','-z',commit,'data/network-flows'],cwd=source_repo)
    blobs={}
    for item in tree.split(b'\0'):
        if not item:continue
        meta,name=item.split(b'\t',1);blobs[name.decode()]=meta.decode().split()[2]
    cache=json.loads(cache_metadata.read_text(encoding='utf-8'))
    exposed={str(Path(f['path']).resolve()).casefold() for f in cache['files']}
    counts=Counter();signatures=Counter();joint=Counter();groups=defaultdict(Counter);records=[];schema=None
    for index,path in enumerate(sorted(root.rglob('*.csv')),1):
        columns=pd.read_csv(path,nrows=0).columns.tolist()
        if schema is None:schema=columns
        if columns!=schema:raise ValueError('Source schema differs: '+str(path.relative_to(root)))
        file_count=Counter();signature_count=Counter();file_joint=Counter();n=0;missing_time=0;minimum=None;maximum=None
        for chunk in pd.read_csv(path,usecols=['Stage','Signature','bidirectional_first_seen_ms'],
                                 dtype={'Stage':'string','Signature':'string'},keep_default_na=False,chunksize=200000):
            n+=len(chunk);file_count.update(chunk['Stage'].astype(str));signature_count.update(chunk['Signature'].astype(str))
            for (stage,signature),count in chunk.groupby(['Stage','Signature'],dropna=False).size().items():file_joint[(str(stage),str(signature))]+=int(count)
            times=pd.to_numeric(chunk['bidirectional_first_seen_ms'],errors='coerce');missing_time+=int(times.isna().sum())
            if times.notna().any():
                lo=float(times.min());hi=float(times.max());minimum=lo if minimum is None else min(minimum,lo);maximum=hi if maximum is None else max(maximum,hi)
        sha,working_blob=digest(path);relative=path.relative_to(source_repo).as_posix()
        # Windows checkout may change LF to CRLF. Git's existing text normalization
        # verifies the original tracked content without rewriting either artifact.
        blob=subprocess.check_output(['git','hash-object','--path',relative,str(path)],cwd=source_repo,text=True).strip()
        if blobs.get(relative)!=blob:raise ValueError('Local CSV differs from pinned author Git blob after Git normalization: '+relative)
        group=path.parent.name;counts.update(file_count);signatures.update(signature_count);joint.update(file_joint);groups[group].update(file_count)
        records.append({'source_file':path.relative_to(root).as_posix(),'bytes':path.stat().st_size,'sha256':sha,
                        'git_blob_sha1':blob,'working_tree_blob_sha1':working_blob,
                        'git_text_normalization_changed_bytes':blob!=working_blob,
                        'matches_pinned_author_git_blob_after_git_normalization':True,'rows':n,'stage_counts':dict(file_count),
                        'signature_counts':dict(signature_count),'missing_first_seen':missing_time,
                        'minimum_first_seen_ms':minimum,'maximum_first_seen_ms':maximum,
                        'source_file_in_prior_gml_cache':str(path.resolve()).casefold() in exposed})
        if index%25==0:print(json.dumps({'files_qualified':index,'rows_qualified':sum(counts.values())}),flush=True)
    result={'schema_version':1,'qualified_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
            'source_repository':'https://gitlab.com/asu22/unraveled','source_commit':commit,
            'paper_doi':'10.1016/j.comnet.2023.109688','license':'GPL-3.0; explicitly linked from author data/README.md',
            'files':records,'file_count':len(records),'source_bytes':sum(r['bytes'] for r in records),
            'columns':schema,'rows':sum(counts.values()),'raw_stage_counts':dict(counts),
            'raw_signature_counts':dict(signatures),
            'stage_signature_counts':[{'stage':stage,'signature':sig,'count':n} for (stage,sig),n in sorted(joint.items())],
            'capture_directory_stage_counts':{g:dict(v) for g,v in sorted(groups.items())},
            'capture_directory_count':len(groups),'files_already_represented_in_prior_gml_cache':sum(r['source_file_in_prior_gml_cache'] for r in records),
            'prior_cache_metadata_sha256':digest(cache_metadata)[0],'scientific_fits':0,
            'status':'EXTERNAL_DATASET_REPLICATION_CANDIDATE_NOT_UNTOUCHED_HOLDOUT',
            'scope':'Raw-file counts and pinned-byte provenance only; no feature deduplication, partition qualification or outcome evaluation.'}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','file_count','source_bytes','raw_stage_counts','capture_directory_count','files_already_represented_in_prior_gml_cache')},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source-repo',type=Path,required=True)
    parser.add_argument('--cache-metadata',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();audit(args.source_repo,args.cache_metadata,args.output)
