"""Synthetic-only foundation runtime qualification; no cybersecurity scores."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

import numpy as np

from .model_backend import create_foundation_classifier


def run(cache, output, device, models):
    if output.exists():
        raise ValueError('Use a fresh smoke receipt')
    os.environ['TABPFN_DISABLE_TELEMETRY'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['DO_NOT_TRACK'] = '1'
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    rng = np.random.default_rng(20260921)
    X = rng.normal(size=(192, 73)).astype(np.float32)
    y = np.tile(np.arange(6), 32)
    test = rng.normal(size=(1024, 73)).astype(np.float32)
    report = {'created_utc': datetime.now(timezone.utc).isoformat(), 'synthetic_only': True,
              'scientific_performance_evaluated': False, 'models': []}
    output.parent.mkdir(parents=True, exist_ok=True)
    for name in models:
        item = {'model': name}
        print(json.dumps({'event': 'smoke_start', 'model': name}), flush=True)
        try:
            model, receipt = create_foundation_classifier(name, cache, seed=20260921,
                device=device, n_estimators=4, allow_download=False)
            start = time.perf_counter()
            model.fit(X, y)
            if device == 'cuda':
                torch.cuda.synchronize()
            item['fit_seconds'] = time.perf_counter() - start
            start = time.perf_counter()
            pred = np.asarray(model.predict_proba(test))
            if device == 'cuda':
                torch.cuda.synchronize()
            item['predict_1024_seconds'] = time.perf_counter() - start
            assert pred.shape == (1024, 6) and np.isfinite(pred).all()
            assert (pred >= 0).all() and np.allclose(pred.sum(1), 1, atol=1e-5)
            item.update(status='PASS', probability_shape=list(pred.shape), backend=receipt)
            del model
        except Exception as error:
            item.update(status='FAIL', error_type=type(error).__name__, error=str(error))
        report['models'].append(item)
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in item.items() if k != 'backend'}), flush=True)
    if any(i['status'] != 'PASS' for i in report['models']):
        raise SystemExit(1)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--device', choices=['cpu', 'cuda'], required=True)
    p.add_argument('--models', default='tabicl_v2,tabpfn_2_5_synthetic')
    a = p.parse_args()
    run(a.cache, a.output, a.device, a.models.split(','))
