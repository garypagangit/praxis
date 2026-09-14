"""CPU artifact reconciliation; separate implementation, same author as worker.

Does not execute models or import the worker/common comparison implementation.
The coordinator's separately pinned bundle manifest is the trusted source input.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(results, manifest_path):
    import torch
    from safetensors.torch import load_file
    root = Path(results).resolve()
    report = json.loads((root / 'GPU_QUALIFICATION.json').read_text())
    manifest = json.loads(Path(manifest_path).read_text())
    checks = []

    def require(name, passed, detail=None):
        checks.append({'check': name, 'passed': bool(passed), 'detail': detail})

    require('frozen_protocol', report['provenance']['protocol_sha256'] == manifest['protocol_sha256'])
    require('frozen_source_manifest', report['provenance']['source_manifest_sha256'] == manifest['files']['SOURCE_MANIFEST.json'])
    require('frozen_worker_files', report['provenance']['harness_files'] ==
            {n: h for n, h in manifest['files'].items() if n.endswith('.py')})
    require('source_commit', report['provenance']['source_pin'] == manifest['source_pin'])
    expected = {(q, s, a) for q in ('none', 'nf4') for s in (12, 64)
                for a in ('ram', 'disk', 'staged_sync', 'staged_prefetch')}
    rows = report['comparisons']
    assigned = [(r['quant'], r['seq'], r['arm']) for r in rows]
    require('unique_complete_positive_universe', len(assigned) == 16 and set(assigned) == expected)
    actual_passes = 0
    for row in rows:
        identity = (row['quant'], row['seq'], row['arm'])
        name = str(identity)
        if 'artifact' not in row:
            require(name + '.artifact_exists', False, 'assignment incomplete')
            continue
        path = (root / row['artifact']).resolve()
        require(name + '.path_contained', path.is_relative_to(root))
        if not path.is_relative_to(root) or not path.is_file():
            continue
        require(name + '.bytes', digest(path) == row['artifact_sha256'])
        refpath = root / f"reference_{row['quant']}_{row['seq']}.safetensors"
        if not refpath.is_file():
            require(name + '.reference_exists', False)
            continue
        got, ref = load_file(path), load_file(refpath)
        exact = len(got) == 52 and set(got) == set(ref)
        if exact:
            exact = all(got[k].shape == ref[k].shape and got[k].dtype == ref[k].dtype
                        and bool(torch.isfinite(got[k]).all()) and bool(torch.isfinite(ref[k]).all())
                        and torch.equal(got[k], ref[k]) for k in got)
        gradients = [v for k, v in got.items() if '/grad/' in k]
        nonvacuous = len(gradients) == 32 and all(float(v.abs().sum()) > 0 for v in gradients)
        require(name + '.all_tensors_exact_finite', exact)
        require(name + '.all_gradients_nonzero', nonvacuous)
        require(name + '.reported_verdict_matches', row['passed'] is exact)
        if row['arm'].startswith('staged_') and 'staging' in row:
            stage = row['staging']
            valid = (type(stage['peak_slots']) is int and stage['peak_slots'] <= 2
                     and type(stage['peak_staging_bytes']) is int
                     and 0 < stage['peak_staging_bytes'] <= stage['byte_bound'])
            require(name + '.owned_staging_bound', valid)
        actual_passes += exact and nonvacuous
    neg = report['negative_controls']
    neg_ids = [(r['quant'], r['seq']) for r in neg]
    require('negative_control_universe', len(neg_ids) == 4 and set(neg_ids) ==
            {(q, s) for q in ('none', 'nf4') for s in (12, 64)})
    require('negative_controls_report_rejection', all(r['passed'] is True for r in neg) and len(neg) == 4)
    require('counter_reconciliation', report.get('assigned_positive') == 16
            and report.get('completed_positive') == 16 and report.get('passed_positive') == actual_passes
            and report.get('assigned_negative') == 4 and report.get('completed_negative') == 4
            and report.get('passed_negative') == 4)
    timing = report.get('timing', [])
    tids = [(r['block'], r['arm']) for r in timing]
    require('timing_universe', len(tids) == 9 and set(tids) ==
            {(b, a) for b in range(3) for a in ('disk', 'staged_sync', 'staged_prefetch')})
    for row in timing:
        samples = row.get('samples', [])
        require('timing_samples_' + str((row['block'], row['arm'])), row['status'] == 'complete'
                and len(samples) == 5 and [s['step'] for s in samples] == list(range(5))
                and [s['warmup'] for s in samples] == [True, True, False, False, False]
                and all(type(s['wall_seconds']) in (int, float) and math.isfinite(s['wall_seconds'])
                        and s['wall_seconds'] > 0 for s in samples))
    require('completed_status', report.get('status') == 'complete' and report.get('instrumentation_complete') is True
            and report.get('qualification_pass') is True and report.get('timing_assigned') == 9
            and report.get('timing_completed') == 9 and not report.get('infrastructure_errors'))
    return {'scope': 'Numerical artifact reconciliation only; same reviewer authored worker; no new model runs',
            'report_sha256': digest(root / 'GPU_QUALIFICATION.json'),
            'trusted_bundle_manifest_sha256': digest(manifest_path),
            'reviewer_source_sha256': digest(__file__), 'checks': checks,
            'checks_total': len(checks), 'checks_failed': sum(not x['passed'] for x in checks),
            'artifact_reconciliation_pass': all(x['passed'] for x in checks),
            'paper_quality_reproduced': False, 'novel_speedup_established': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--results', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = audit(args.results, args.manifest)
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: result[k] for k in ['checks_total', 'checks_failed', 'artifact_reconciliation_pass']}))
    raise SystemExit(0 if result['artifact_reconciliation_pass'] else 1)
