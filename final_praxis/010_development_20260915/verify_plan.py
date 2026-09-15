"""Offline integrity and accounting checks for this unrun development plan."""
from pathlib import Path
import hashlib
import json
import math
import re


def main():
    root = Path(__file__).resolve().parent
    spec = json.loads((root / 'D0_SPEC.json').read_text())
    checks = {}
    origins = [384 + math.floor(j * 622 / 31) for j in range(32)]
    checks['origins_complete_unique'] = len(set(origins)) == 32
    checks['commissioning_precedes_contexts'] = min(origins) - spec['model']['context_length'] > spec['data']['commissioning_row_indices_inclusive'][1]
    checks['targets_within_allowed_rows'] = max(origins) <= spec['data']['permitted_value_row_indices_inclusive'][1]
    counts = spec['accounting']
    total = len(spec['pipelines']) * spec['data']['origins'] * (counts['clean_evaluations_per_pipeline_origin'] + counts['perturbed_evaluations_per_pipeline_origin'] + counts['extra_clean_repeats_per_pipeline_origin'])
    checks['all_1024_evaluations_accounted'] = total == counts['total_pipeline_evaluations'] == 1024
    checks['paired_reference'] = counts['each_pipeline_uses_its_own_clean_reference']
    checks['no_selected_context_mean'] = spec['gates']['variant_mean_error_inflation_context_denominator'] == 32 and spec['gates']['clean_off_channel_mae_scalar_target_denominator'] == 64 and not spec['gates']['means_conditioned_on_high_spillover_cases']
    checks['no_hai_or_labels'] = not spec['data']['hai_access_allowed'] and not spec['data']['labels_used']
    checks['raw_joint_hypothesis'] = spec['gates']['hypothesis_pipeline'] == 'joint_native3'
    checks['explicit_routing'] = spec['model']['use_variate_attention'] and not spec['model']['joint_univariate_option'] and spec['model']['independent_univariate_option']
    checks['unrun_and_runtime_gate'] = spec['status'] == 'PLAN_ONLY_NOT_RUN_RUNTIME_NOT_FROZEN' and spec['planned_compute']['model_calls_for_this_plan'] == 0 and not spec['planned_compute']['cloud_started_for_this_plan'] and spec['planned_compute']['requires_committed_worker_and_runtime_freeze']
    checks['bounded_compute'] = spec['planned_compute']['maximum_hosts'] == 1 and spec['planned_compute']['maximum_total_host_minutes'] == 30 and spec['planned_compute']['combined_reserve_usd'] == 10
    problems = []
    for name, item in json.loads((root / 'MANIFEST.json').read_text())['files'].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            problems.append(name)
            continue
        data = path.read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            problems.append(name)
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                if '://' in target or target.startswith('#'):
                    continue
                if not (path.parent / target.split('#')[0]).exists():
                    problems.append(name + ': ' + target)
    checks['sealed_bytes_and_local_links'] = not problems
    result = {'status': 'PASS_PLAN_INTEGRITY_ONLY' if all(checks.values()) else 'FAIL',
              'checks': checks, 'problems': problems, 'model_calls': 0, 'dataset_value_reads': 0,
              'scope': 'Plan integrity and specified accounting; no executable runtime, model outcome, novelty or academic approval verification.'}
    print(json.dumps(result, indent=2))
    raise SystemExit(not all(checks.values()))


if __name__ == '__main__':
    main()
