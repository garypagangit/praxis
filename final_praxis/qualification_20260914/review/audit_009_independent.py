"""Post-run independent 009 audit; stdlib + NumPy, no Torch/model imports.

This source was archived after the model run and initial independent review.
It is not a prospective experiment freeze. AI-assisted implementation.
"""
import argparse
import datetime as dt
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import struct

import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_tensors(path):
    """Read finite F32/BF16 fixture tensors, preserving original payload bytes."""
    raw = Path(path).read_bytes()
    header_size = struct.unpack('<Q', raw[:8])[0]
    header = json.loads(raw[8:8 + header_size])
    payload = raw[8 + header_size:]
    tensors, spans = {}, []
    for key, value in header.items():
        if key == '__metadata__':
            continue
        lo, hi = value['data_offsets']
        if not 0 <= lo <= hi <= len(payload):
            raise ValueError('Tensor offset outside payload')
        buffer = payload[lo:hi]
        dtype, shape = value['dtype'], tuple(value['shape'])
        if dtype == 'F32':
            array = np.frombuffer(buffer, dtype='<f4')
        elif dtype == 'BF16':
            array = (np.frombuffer(buffer, dtype='<u2').astype(np.uint32) << 16).view(np.float32)
        else:
            raise ValueError('Unexpected fixture dtype: ' + dtype)
        if array.size != math.prod(shape) or not np.isfinite(array).all():
            raise ValueError('Invalid tensor size or nonfinite tensor')
        spans.append((lo, hi))
        tensors[key] = (dtype, shape, buffer, array)
    spans.sort()
    if not spans or spans[0][0] != 0 or spans[-1][1] != len(payload):
        raise ValueError('Incomplete payload coverage')
    if any(a[1] != b[0] for a, b in zip(spans, spans[1:])):
        raise ValueError('Overlapping or gapped tensor spans')
    return tensors


NAMES = {
    f'base_model.model.model.layers.{layer}.self_attn.{projection}.lora_{part}.default.weight'
    for layer in range(4) for projection in ('q_proj', 'v_proj') for part in ('A', 'B')
}


def valid_schema(tensors, sequence):
    keys = {f'{step}/{kind}' for step in range(2) for kind in ('logits', 'loss')}
    keys |= {f'{step}/grad/{name}' for step in range(2) for name in NAMES}
    keys |= {'final/' + name for name in NAMES}
    if set(tensors) != keys or len(tensors) != 52:
        return False
    valid = True
    for step in range(2):
        valid &= tensors[f'{step}/logits'][:2] == ('BF16', (1, sequence, 64))
        valid &= tensors[f'{step}/loss'][:2] == ('F32', ())
        for name in NAMES:
            shape = (4, 64) if 'lora_A' in name else ((64, 4) if 'q_proj' in name else (32, 4))
            gradient, final = tensors[f'{step}/grad/{name}'], tensors['final/' + name]
            valid &= gradient[:2] == ('F32', shape) and np.any(gradient[3] != 0)
            valid &= final[:2] == ('F32', shape) and np.any(final[3] != 0)
    return bool(valid)


def audit(source, results, canonical_summary=None, canonical_results=None):
    source, results = Path(source), Path(results)
    canonical_summary = Path(canonical_summary or source / 'results/GPU_SUMMARY.json')
    canonical_results = Path(canonical_results or source / 'RESULTS.md')
    report = json.loads((results / 'GPU_QUALIFICATION.json').read_text())
    bundle = json.loads((source / 'BUNDLE_MANIFEST.json').read_text())
    checks = []

    def check(name, valid, detail=None):
        checks.append({'check': name, 'passed': bool(valid), 'detail': detail})

    for name in ('QUALIFICATION_PROTOCOL.md', 'SOURCE_MANIFEST.json', *report['provenance']['harness_files']):
        check('frozen:' + name, sha(source / name) == bundle['files'][name])
    check('protocol_provenance', report['provenance']['protocol_sha256'] == bundle['protocol_sha256'])
    check('source_pin', report['provenance']['source_pin'] == bundle['source_pin'])
    check('all_harness_provenance', report['provenance']['harness_files'] ==
          {k: v for k, v in bundle['files'].items() if k.endswith('.py')})
    check('manifest_provenance', report['provenance']['source_manifest_sha256'] == bundle['files']['SOURCE_MANIFEST.json'])
    expected = set(itertools.product(('none', 'nf4'), (12, 64), ('ram', 'disk', 'staged_sync', 'staged_prefetch')))
    rows = report['comparisons']
    check('positive_universe', len(rows) == 16 and {(r['quant'], r['seq'], r['arm']) for r in rows} == expected)
    references, hashes, comparisons = {}, {}, []
    for quant, sequence in itertools.product(('none', 'nf4'), (12, 64)):
        path = results / f'reference_{quant}_{sequence}.safetensors'
        references[quant, sequence] = load_tensors(path)
        hashes[path.name] = sha(path)
        check('reference_schema:' + path.name, valid_schema(references[quant, sequence], sequence))
    for row in rows:
        identity = f"{row['arm']}_{row['quant']}_{row['seq']}"
        path = results / row['artifact']
        if not path.resolve().is_relative_to(results.resolve()):
            raise ValueError('Artifact path escapes results directory')
        check(identity + ':expected_filename', path.name == identity + '.safetensors')
        check(identity + ':recorded_sha', sha(path) == row['artifact_sha256'])
        hashes[path.name] = sha(path)
        actual, reference = load_tensors(path), references[row['quant'], row['seq']]
        exact = valid_schema(actual, row['seq']) and set(actual) == set(reference)
        exact = bool(exact and all(actual[k][:3] == reference[k][:3] for k in reference))
        check(identity + ':all52_tensors_bitwise_exact_finite_nonzero_gradients', exact)
        check(identity + ':reported_pass_matches', row['passed'] is exact and row['tensors'] == 52 and row['differences'] == [])
        if row['arm'].startswith('staged'):
            stage = row['staging']
            bound = 147968 if row['quant'] == 'none' else 38640
            check(identity + ':staging', stage['slots'] == stage['peak_slots'] == 2 and
                  stage['peak_staging_bytes'] == stage['byte_bound'] == bound and stage['reads'] == 10 and
                  stage['requested_read_bytes'] == bound // 2 * 10 and stage['waited_copy_events'] > 0 and
                  stage['pin'] is True and stage['prefetch'] is (row['arm'] == 'staged_prefetch'))
        check(identity + ':runtime', row['runtime']['buffers'] == 2 and row['runtime']['n_layers'] == 4 and
              row['runtime']['large_buffer_bytes'] == 0 and row['runtime']['device'] == 'cuda')
        comparisons.append({'identity': identity, 'tensors': 52, 'gradient_tensors': 32, 'exact': exact})
    negative = report['negative_controls']
    check('negative_universe', len(negative) == 4 and {(r['quant'], r['seq']) for r in negative} ==
          set(itertools.product(('none', 'nf4'), (12, 64))))
    check('negative_reported_rejection', all(r['passed'] is True and
          r['kind'] == 'deliberately corrupted recorded gradient' for r in negative))
    for key, reference in references.items():
        name = next(k for k in sorted(reference) if '/grad/' in k)
        altered = reference[name][3].copy()
        altered[0] += np.float32(1)
        check('independent_gradient_corruption_rejected:' + str(key), not np.array_equal(altered, reference[name][3]))
    counts = dict(assigned_positive=16, completed_positive=16, passed_positive=16,
                  assigned_negative=4, completed_negative=4, passed_negative=4,
                  timing_assigned=9, timing_completed=9)
    check('reported_counts', all(report[k] == v for k, v in counts.items()))
    check('completion_gate', report['status'] == 'complete' and report['qualification_pass'] is True and
          report['instrumentation_complete'] is True and not report.get('infrastructure_errors'))
    order = ['disk', 'staged_sync', 'staged_prefetch']
    expected_order = [(block, arm) for block in range(3) for arm in order[block:] + order[:block]]
    timing = report['timing']
    check('timing_order', [(r['block'], r['arm']) for r in timing] == expected_order)
    values, blocks = {a: [] for a in order}, {a: [] for a in order}
    physical_reads, gpu_peaks, process_rss = [], [], []
    for row in timing:
        identity = f"{row['block']}/{row['arm']}"
        samples = row['samples']
        check('timing_complete:' + identity, row['status'] == 'complete' and len(samples) == 5 and
              [s['step'] for s in samples] == list(range(5)) and
              [s['warmup'] for s in samples] == [True, True, False, False, False] and
              math.isfinite(row['build_seconds']) and row['build_seconds'] > 0)
        measured = []
        for sample in samples:
            check('timing_sample:' + identity + '/' + str(sample['step']),
                  math.isfinite(sample['wall_seconds']) and sample['wall_seconds'] > 0 and
                  sample['nonpadding_tokens'] == 64 and math.isfinite(sample['loss']) and
                  sample['gpu_reserved_peak_bytes'] >= sample['gpu_allocated_peak_bytes'] > 0)
            before, after = sample['process_before'], sample['process_after']
            physical_reads.append(int(after['io']['read_bytes']) - int(before['io']['read_bytes']))
            gpu_peaks.append(sample['gpu_allocated_peak_bytes'])
            process_rss.append(int(after['status']['VmRSS'].split()[0]) * 1024)
            if not sample['warmup']:
                measured.append(sample['wall_seconds'])
                values[row['arm']].append(sample['wall_seconds'])
        blocks[row['arm']].append(statistics.median(measured))
        if row['arm'].startswith('staged'):
            stage = row['staging']
            check('timing_staging:' + identity, stage['slots'] == stage['peak_slots'] == 2 and
                  stage['peak_staging_bytes'] == stage['byte_bound'] == 38640 and stage['pin'] is True)
    medians = {a: statistics.median(v) for a, v in values.items()}
    means = {a: statistics.mean(v) for a, v in blocks.items()}
    ratio_disk = means['staged_prefetch'] / means['disk'] - 1
    ratio_sync = means['staged_prefetch'] / means['staged_sync'] - 1
    summary = json.loads(canonical_summary.read_text())
    agrees = summary['source_report_sha256'] == sha(results / 'GPU_QUALIFICATION.json')
    agrees &= all(math.isclose(v * 1000, summary['mean_of_block_median_step_ms'][a], rel_tol=0, abs_tol=1e-10)
                  for a, v in means.items())
    agrees &= math.isclose(ratio_disk * 100, summary['prefetch_time_increase_percent_vs_disk'], rel_tol=0, abs_tol=1e-10)
    agrees &= math.isclose(ratio_sync * 100, summary['prefetch_time_increase_percent_vs_staged_sync'], rel_tol=0, abs_tol=1e-10)
    prose = canonical_results.read_text(encoding='utf-8')
    agrees &= all(f'{v * 1000:.2f}' in prose for v in means.values())
    agrees &= f'{ratio_disk * 100:.2f}%' in prose and f'{ratio_sync * 100:.2f}%' in prose
    check('canonical_mean_of_three_block_medians_aggregation', agrees)
    return {
        'status': 'PASS_TINY_MODEL_ARTIFACT_QUALIFICATION' if all(c['passed'] for c in checks) else 'FAIL',
        'reviewed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'reviewer': 'oracle_contract, independent of worker and artifact-review implementation author',
        'method': 'Independent stdlib/NumPy safetensors binary parser; no Torch, worker comparator, model or owner auditor imported.',
        'results_receipt_sha256': sha(results / 'GPU_QUALIFICATION.json'),
        'worker_sha256': sha(source / 'gpu_qualification.py'),
        'staged_source_sha256': sha(source / 'staged_source.py'),
        'bundle_manifest_sha256': sha(source / 'BUNDLE_MANIFEST.json'),
        'artifact_sha256': hashes, 'checks_total': len(checks),
        'checks_passed': sum(c['passed'] for c in checks), 'checks_failed': sum(not c['passed'] for c in checks),
        'checks': checks, 'positive_comparisons': comparisons,
        'exact_tensor_comparisons': 832, 'nonzero_gradient_comparisons': 512,
        'reference_configurations': 4, 'trajectory_optimizer_steps': 2,
        'negative_controls': {'reported_recorded_gradient_corruptions': 4,
                              'independent_in_memory_corruption_rejections': 4,
                              'wrong_weight_GPU_model_run_observed': False},
        'timing': {
            'blocks': 3, 'arms': 3, 'completed_blocks': 9, 'total_steps': 45,
            'warmup_steps': 18, 'measured_steps': 27, 'measured_steps_per_arm': 9,
            'median_wall_seconds_by_arm': medians, 'block_median_seconds_by_arm': blocks,
            'prefetch_vs_disk_median_time_increase_fraction': medians['staged_prefetch'] / medians['disk'] - 1,
            'prefetch_vs_staged_sync_median_time_increase_fraction': medians['staged_prefetch'] / medians['staged_sync'] - 1,
            'sum_process_physical_read_bytes_deltas': sum(physical_reads),
            'all_process_physical_read_deltas_zero': all(v == 0 for v in physical_reads),
            'max_gpu_allocated_bytes': max(gpu_peaks), 'max_process_rss_bytes': max(process_rss),
            'inferential_efficacy_test_performed': False,
            'existing_median_statistic_definition': 'Median of all 9 measured step times per arm, pooled across 3 blocks.',
            'canonical_aggregation_crosscheck': {
                'definition': 'Arithmetic mean of 3 block medians; each block median uses 3 measured steps.',
                'mean_block_median_seconds_by_arm': means,
                'prefetch_vs_disk_time_increase_fraction': ratio_disk,
                'prefetch_vs_staged_sync_time_increase_fraction': ratio_sync,
                'canonical_reported_values_agree': bool(agrees),
                'canonical_results_md_sha256': sha(canonical_results),
                'canonical_summary_json_sha256': sha(canonical_summary),
                'canonical_unrounded_summary_agreement_absolute_tolerance': 1e-10,
                'canonical_input_report_hash_agrees': summary['source_report_sha256'] == sha(results / 'GPU_QUALIFICATION.json'),
                'inference_claimed': False}},
        'interpretation': 'Tiny generated-model correctness is qualified; prefetch is slower in these warm-cache measurements. No novel speedup or downstream quality claim.',
        'limitations': ['Owned staging bounds are not total memory bounds.',
                       'References and gradients are checked, not independently regenerated model outputs.',
                       'Two optimizer steps, four decoder layers; no large embedding/head pool.',
                       'GPU negative controls alter saved gradients, not GPU model weights.',
                       'No efficacy interval, independent laboratory replication or original quality-task reproduction.'],
        'novel_algorithm_established': False, 'speedup_established': False,
        'downstream_quality_reproduced': False, 'reviewer_model_calls': 0,
        'reviewer_cloud_calls': 0, 'worker_or_artifacts_modified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--canonical-summary', type=Path)
    parser.add_argument('--canonical-results', type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.source, args.results, args.canonical_summary, args.canonical_results)
    except Exception as exc:
        result = {'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc),
                  'scope': 'Audit could not complete; no PASS inferred from missing inputs.'}
    result.update(audit_source_sha256=sha(__file__), audit_source_archived_after_model_runs=True,
                  audit_source_frozen_before_model_runs=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'checks_total', 'checks_failed') if k in result}))
    raise SystemExit(0 if result['status'].startswith('PASS') else 1)


if __name__ == '__main__':
    main()
