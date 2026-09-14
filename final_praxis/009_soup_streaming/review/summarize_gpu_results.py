"""Descriptive aggregation of the frozen tiny-model artifact; no model execution."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics


def summarize(path):
    raw = Path(path).read_bytes()
    data = json.loads(raw)
    arms = ('disk', 'staged_sync', 'staged_prefetch')
    blocks = {}
    for row in data['timing']:
        values = [s['wall_seconds'] for s in row['samples'] if not s['warmup']]
        assert len(values) == 3
        blocks.setdefault(row['block'], {})[row['arm']] = statistics.median(values) * 1000
    assert set(blocks) == {0, 1, 2}
    assert all(set(b) == set(arms) for b in blocks.values())
    means = {arm: statistics.mean(b[arm] for b in blocks.values()) for arm in arms}
    measured = [s for row in data['timing'] for s in row['samples'] if not s['warmup']]
    physical = [int(s['process_after']['io']['read_bytes']) -
                int(s['process_before']['io']['read_bytes']) for s in measured]
    staging = [r['staging'] for r in data['comparisons'] if r.get('staging')]
    return {
        'source_report_sha256': hashlib.sha256(raw).hexdigest(),
        'scope': 'Descriptive tiny random-model warm-cache instrumentation; not independent efficacy replicates',
        'parameters': data['model']['parameters'],
        'positive_assigned': data['assigned_positive'],
        'positive_completed': data['completed_positive'],
        'positive_passed': data['passed_positive'],
        'negative_assigned': data['assigned_negative'],
        'negative_completed': data['completed_negative'],
        'negative_passed': data['passed_negative'],
        'negative_kind': 'Corruption of an already recorded gradient; not a model-generated defect',
        'timing_blocks_per_arm': 3,
        'warmup_steps_per_block': 2,
        'measured_steps_per_block': 3,
        'block_median_step_ms': blocks,
        'mean_of_block_median_step_ms': means,
        'prefetch_time_increase_percent_vs_disk': (means['staged_prefetch'] / means['disk'] - 1) * 100,
        'prefetch_time_increase_percent_vs_staged_sync': (means['staged_prefetch'] / means['staged_sync'] - 1) * 100,
        'all_measured_process_physical_read_deltas_zero': all(x == 0 for x in physical),
        'measured_process_physical_read_deltas_bytes': physical,
        'owned_staging_peak_slots': max(s['peak_slots'] for s in staging),
        'owned_staging_peak_bytes_by_quantization': {
            q: max(r['staging']['peak_staging_bytes'] for r in data['comparisons']
                   if r['quant'] == q and r.get('staging')) for q in ('none', 'nf4')},
        'qualification_pass': data['qualification_pass'],
        'instrumentation_complete': data['instrumentation_complete'],
        'pretrained_quality_reproduced': False,
        'novel_speedup_established': False,
        'disposition': 'GO for a separately specified bounded pilot only; not efficacy or paper-readiness approval',
        'limitations': [
            'One A10G host and one 152,128-parameter random model; no laptop or 8B checkpoint run.',
            'The NF4 reference uses the matched dequantization path; native fused-kernel equivalence is not established.',
            'Two short optimizer steps and four layers do not cover all models, layer sizes or long training.',
            'Large embedding/head streaming is not qualified.',
            'Warm tiny timing shows extra overhead; it cannot estimate a cold or memory-constrained workload benefit.',
            'Research-use dataset terms are available; exact original paper split preparation remains unavailable.',
            'Separate artifact checker implementation shares authorship with the worker; source review by the coordinator is distinct.'
        ]
    }


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    Path(a.output).write_text(json.dumps(summarize(a.input), indent=2, allow_nan=False) + '\n', encoding='utf-8')
