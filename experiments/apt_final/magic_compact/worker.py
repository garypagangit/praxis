"""Run unchanged registered MAGIC science with explicit exact storage substitution."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json,os
from pathlib import Path
from ..magic_reproduction import worker as original_worker
from ..magic_reproduction import qualification as original_qualification
from .provenance import HERE,ORIGINAL,digest,verify
from .scoring import ExactFullReferenceKNN as ExactMultiplicityKNN


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['data-dir','source-dir','output','registration']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--deadline-epoch',type=float,required=True)
    p.add_argument('--datasets',choices=['theia','cadets','theia,cadets'],required=True)
    a=p.parse_args(argv)
    record,prior=verify(a.registration,a.data_dir,a.source_dir)
    receipt_path=a.output/'COMPACT_RUNTIME_RECEIPT.json'
    if receipt_path.exists():raise ValueError('Refusing existing compact run')
    if a.output.exists() and any(p.name not in original_worker.BOOTSTRAP_FILES or not p.is_file() for p in a.output.iterdir()):
        raise ValueError('Refusing existing scientific output before substitution')
    old_worker=original_worker.ExactFullReferenceKNN
    old_qualification=original_qualification.ExactFullReferenceKNN
    original_worker.ExactFullReferenceKNN=ExactMultiplicityKNN
    original_qualification.ExactFullReferenceKNN=ExactMultiplicityKNN
    rc=1
    try:
        rc=original_worker.main(['--config',str(ORIGINAL/'config.json'),
            '--registration',str(ORIGINAL/'REGISTRATION.json'),
            '--data-dir',str(a.data_dir),'--source-dir',str(a.source_dir),'--output',str(a.output),
            '--deadline-epoch',str(a.deadline_epoch),'--datasets',a.datasets])
    finally:
        original_worker.ExactFullReferenceKNN=old_worker
        original_qualification.ExactFullReferenceKNN=old_qualification
        receipt={'status':'COMPACT_RUNTIME_RECORDED','completed_utc':datetime.now(timezone.utc).isoformat(),
            'compact_registration_sha256':digest(a.registration),
            'original_registration_sha256':record['original_registration_sha256'],
            'source_commit':record['source_commit'],'original_source_commit':prior['source_commit'],
            'source_original_unchanged':True,'source_mode':'exact_multiplicity_runtime',
            'substitutions':{'experiments.apt_final.magic_reproduction.worker.ExactFullReferenceKNN':
                'experiments.apt_final.magic_compact.scoring.ExactFullReferenceKNN',
                'experiments.apt_final.magic_reproduction.qualification.ExactFullReferenceKNN':
                'experiments.apt_final.magic_compact.scoring.ExactFullReferenceKNN'},
            'results_sha256':digest(a.output/'RESULTS.json') if (a.output/'RESULTS.json').exists() else None,
            'bundle_sha256':os.environ.get('APT_FROZEN_BUNDLE_SHA256'),
            'selected_datasets':a.datasets.split(','),'exit_code':rc,'novelty_claimed':False,
            'checkpoint_reuse':False}
        if a.output.is_dir():
            with receipt_path.open('x',encoding='utf-8',newline='\n') as handle:
                handle.write(json.dumps(receipt,indent=2)+'\n')
    return rc


if __name__=='__main__':raise SystemExit(main())
