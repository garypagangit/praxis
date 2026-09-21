"""Verify the pinned CUDA runtime, then launch the unchanged E1 runner."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import runpy
import sys

EXPECTED={'torch':'2.5.1','tabicl':'2.2.0','tabpfn':'9.0.0','numpy':'2.2.6',
          'scipy':'1.15.3','scikit-learn':'1.7.2','pandas':'2.3.3',
          'xgboost':'2.1.4','lightgbm':'4.6.0'}


def qualify():
    if sys.version_info<(3,10):raise ValueError('Python>=3.10 required')
    versions={name:importlib.metadata.version(name) for name in EXPECTED}
    if any(versions[name].split('+')[0]!=version for name,version in EXPECTED.items()):
        raise ValueError('Pinned package version mismatch')
    import torch
    if not torch.cuda.is_available():raise ValueError('CUDA required; no CPU fallback')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(4)
    # Exercise CUDA without fitting any classifier.
    value=torch.ones((8,8),device='cuda')
    assert float((value@value).sum().cpu())==512.0
    torch.cuda.synchronize()
    return {'python':sys.version,'versions':versions,'cuda_runtime':torch.version.cuda,
            'gpu':torch.cuda.get_device_name(0),'threads':torch.get_num_threads(),
            'interop_threads':torch.get_num_interop_threads(),'cuda_tensor_check':'PASS',
            'scientific_model_fits_in_probe':0}


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe',action='store_true');mode.add_argument('--run',action='store_true')
    parser.add_argument('--root',type=Path)
    args,remaining=parser.parse_known_args()
    report=qualify()
    if args.probe:
        from model_backend import ensure_checkpoint
        if args.root is None:raise ValueError('Probe requires bundle root')
        for model in ['tabicl_v2','tabpfn_2_5_synthetic']:
            ensure_checkpoint(model,args.root/'model_cache',allow_download=False)
        report['both_pinned_checkpoints_verified']=True
        print(json.dumps(report,indent=2));return
    sys.argv=['run_e1.py',*remaining]
    runpy.run_path(str(Path(__file__).with_name('run_e1.py')),run_name='__main__')


if __name__=='__main__':main()
