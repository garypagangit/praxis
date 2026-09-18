"""Post-freeze independent point-metric reconstruction; never selects or fits a policy.

This audit was authored after the scientific freeze, while generation was running.
It must be run only after the complete result is released for audit. It deliberately
does not import analyze_external.py or read scored_records.jsonl. Bootstrap draws
are not repeated: reported interval endpoints are used only to check gate logic.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import heapq
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
MODELS = ('llama', 'qwen')
CONDITIONS = ('vanilla', 'relationship_evidence')
COMPARATORS = ('relevance', 'relevance_options', 'source_classifier', 'question_utility')
CANDIDATE = 'evidence_utility'
MODEL_SPECS = {
    'llama': ('meta-llama/Llama-3.1-8B-Instruct', '0e9e39f249a16976918f6564b8830bc894c89659'),
    'qwen': ('Qwen/Qwen2.5-7B-Instruct', 'a09a35458c702b33eeacc393d103063234e8bc28'),
}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def reparse(text):
    """Independently implement the frozen first-line answer acceptance contract."""
    text = re.sub(r'^assistant\s*[:\n]*', '', text.strip(), flags=re.IGNORECASE).strip()
    first = next((line.strip() for line in text.splitlines() if line.strip()), '')
    if not first:
        return ''
    initial = re.match(r'^(?:answer\s*[:\-]?\s*)?([a-d])(?=[\).:\s]|$)', first, re.IGNORECASE)
    if initial:
        return initial[1].upper()
    fallback = re.search(r'\b[A-D]\b', first[:20].upper())
    return fallback[0] if fallback else ''


def same(expected, actual, location, counts):
    counts['compared_values'] += 1
    if isinstance(expected, bool):
        require(type(actual) is bool and actual == expected, f'{location}: boolean differs')
    elif isinstance(expected, int):
        require(type(actual) is int and actual == expected, f'{location}: count differs ({actual} vs {expected})')
    elif isinstance(expected, float):
        require(isinstance(actual, (float, int)) and math.isfinite(actual)
                and math.isclose(expected, actual, rel_tol=0, abs_tol=1e-9),
                f'{location}: point estimate differs ({actual} vs {expected})')
    else:
        require(expected == actual, f'{location}: value differs')


def finite_interval(value, location):
    require(isinstance(value, list) and len(value) == 2
            and all(isinstance(v, (float, int)) and math.isfinite(v) for v in value)
            and value[0] <= value[1], f'{location}: malformed interval')
    return value


def validate_raw(records, phase, ids, prompt_map, runtime):
    expected = {(identifier, model, condition) for identifier in ids
                for model in MODELS for condition in CONDITIONS}
    indexed = {}
    invalid = Counter({model + '/' + condition: 0 for model in MODELS for condition in CONDITIONS})
    for row in records:
        key = (row['id'], row['model'], row['condition'])
        require(key in expected and key not in indexed, f'{phase}: unexpected or duplicate output {key}')
        require(row['phase'] == phase, f'{phase}: phase differs')
        require((row['model_id'], row['revision']) == MODEL_SPECS[row['model']], f'{key}: model revision differs')
        require(isinstance(row['raw_output'], str), f'{key}: raw output must be text')
        answer = reparse(row['raw_output'])
        valid = answer in {'A', 'B', 'C', 'D'}
        require(row['parsed_answer'] == answer and row['valid'] is valid, f'{key}: parser/validity disagreement')
        require(type(row['input_tokens']) is int and 0 < row['input_tokens'] <= 4096, f'{key}: input length differs')
        require(re.fullmatch('[0-9a-f]{64}', row['prompt_sha256']) is not None, f'{key}: invalid rendered hash')
        require(row['input_prompt_sha256'] == prompt_map[(row['id'], row['condition'])], f'{key}: wrong input prompt')
        if phase == 'qualification':
            require(valid, 'Qualification contains an invalid answer')
        invalid[row['model'] + '/' + row['condition']] += int(not valid)
        indexed[key] = answer
    require(set(indexed) == expected and len(records) == len(expected), f'{phase}: incomplete output inventory')
    for model in MODELS:
        summary = runtime[phase][model]
        bad = sum(invalid[model + '/' + condition] for condition in CONDITIONS)
        require(summary['records'] == 2 * len(ids) and summary['invalid'] == bad
                and summary['valid'] == 2 * len(ids) - bad, f'{phase}/{model}: runtime counts differ')
    return indexed, invalid


def reconstruct(labels, decisions, answers):
    """Count each question directly; do not use analyzer arrays or summary code."""
    n = len(labels)
    use_count = sum(label['id'] in decisions for label in labels)
    output = {'evidence_use_n': use_count, 'evidence_use_pct': 100.0 * use_count / n, 'models': {}}
    net_sum = 0
    for model in MODELS:
        counts = Counter()
        for label in labels:
            identifier = label['id']
            baseline_correct = answers[identifier, model, 'vanilla'] == label['answer']
            evidence_correct = answers[identifier, model, 'relationship_evidence'] == label['answer']
            use = identifier in decisions
            chosen_correct = evidence_correct if use else baseline_correct
            counts['correct'] += chosen_correct
            counts['baseline_correct'] += baseline_correct
            if not baseline_correct and evidence_correct:
                counts['recovered_answers' if use else 'lost_improvements'] += 1
            elif baseline_correct and not evidence_correct:
                counts['induced_errors' if use else 'prevented_errors'] += 1
        net = counts['correct'] - counts['baseline_correct']
        require(net == counts['recovered_answers'] - counts['induced_errors'], 'Net-change accounting identity failed')
        net_sum += net
        output['models'][model] = {
            'correct': counts['correct'], 'accuracy_pct': 100.0 * counts['correct'] / n,
            'delta_vs_vanilla_pp': 100.0 * net / n,
            **{name: counts[name] for name in ('recovered_answers', 'induced_errors', 'prevented_errors', 'lost_improvements')},
        }
    output['mean_delta_vs_vanilla_pp'] = 100.0 * net_sum / (n * len(MODELS))
    return output


def audit(root, outputs, results_path):
    counts = Counter()
    freeze = read_json(root / 'SCIENTIFIC_FREEZE.json')
    for name, expected in freeze['files'].items():
        require(digest(root / name) == expected, 'Frozen file changed: ' + name)
    runtime = read_json(outputs / 'runtime.json')
    require(runtime['status'] == 'COMPLETE', 'Do not audit an incomplete generation run')
    for field, name in (('inputs_sha256', 'generator_inputs.jsonl'),
                        ('qualification_sha256', 'qualification_inputs.jsonl'),
                        ('worker_sha256', 'inference_worker.py'),
                        ('frozen_inference_sha256', 'frozen_inference.py')):
        require(runtime[field] == digest(root / name), 'Runtime digest mismatch: ' + name)
    for field, name in (('predictions_sha256', 'predictions.jsonl'),
                        ('qualification_outputs_sha256', 'qualification.jsonl')):
        require(runtime[field] == digest(outputs / name), 'Runtime output digest mismatch: ' + name)
    require(runtime['decoding'] == {'batch_size': 2, 'dtype': 'float16', 'do_sample': False,
            'max_input_tokens': 4096, 'max_new_tokens': 8}, 'Decoding settings changed')

    prompt_maps = {}
    for phase, filename in (('test', 'generator_inputs.jsonl'), ('qualification', 'qualification_inputs.jsonl')):
        items = read_lines(root / filename)
        prompt_map = {}
        identifiers = []
        for item in items:
            identifiers.append(item['id'])
            for field, condition in (('vanilla_prompt', 'vanilla'), ('evidence_prompt', 'relationship_evidence')):
                prompt_map[item['id'], condition] = hashlib.sha256(item[field].encode()).hexdigest()
        require(len(identifiers) == len(set(identifiers)) == (1247 if phase == 'test' else 8), 'Input inventory differs')
        prompt_maps[phase] = (set(identifiers), prompt_map)
    require(not prompt_maps['test'][0] & prompt_maps['qualification'][0], 'Qualification overlaps test IDs')

    # Labels and all raw outputs are first accessed here, after the complete-run checks.
    labels = read_lines(root / 'sealed_labels.jsonl')
    ids = [label['id'] for label in labels]
    require(len(ids) == len(set(ids)) == 1247 and set(ids) == prompt_maps['test'][0], 'Reference inventory differs')
    require(all(label['answer'] in {'A', 'B', 'C', 'D'} for label in labels), 'Invalid reference labels')
    qualification = read_lines(outputs / 'qualification.jsonl')
    raw = read_lines(outputs / 'predictions.jsonl')
    require(len(qualification) == 32 and len(raw) == 4988, 'Full 32 + 4988 output inventory is required')
    validate_raw(qualification, 'qualification', *prompt_maps['qualification'], runtime)
    answers, invalid = validate_raw(raw, 'test', *prompt_maps['test'], runtime)
    result = read_json(results_path)
    for name, expected in (('n', 1247), ('fresh_outputs', 4988), ('qualification_outputs', 32)):
        same(expected, result[name], name, counts)
    same(dict(invalid), result['invalid_outputs'], 'invalid_outputs', counts)
    same(digest(root / 'SCIENTIFIC_FREEZE.json'), result['scientific_freeze_sha256'], 'scientific freeze digest', counts)
    for filename, expected in result['files_sha256'].items():
        same(digest(outputs / filename), expected, 'result output digest/' + filename, counts)

    policies = read_lines(root / 'policy_predictions.jsonl')
    require(len(policies) == 1247 and {row['id'] for row in policies} == set(ids), 'Policy inventory differs')
    policy_map = {row['id']: row for row in policies}
    policy_names = ('always_vanilla', 'always_evidence', *COMPARATORS, CANDIDATE)
    decisions = {}
    threshold_details = read_json(root / 'DEPLOYMENT_METADATA.json')['threshold_calibration']
    for name in policy_names:
        require(all(type(row['use_evidence'][name]) is bool for row in policies), 'Nonboolean policy decision')
        decisions[name] = {row['id'] for row in policies if row['use_evidence'][name]}
        if name not in {'always_vanilla', 'always_evidence'}:
            detail = threshold_details[name]
            cutoff = detail['threshold'] if detail['feasible'] else math.inf
            for row in policies:
                require(math.isfinite(row['scores'][name]), 'Non-finite policy score')
                require(row['use_evidence'][name] == (row['scores'][name] >= cutoff), 'Frozen cutoff decision differs')
    require(not decisions['always_vanilla'] and decisions['always_evidence'] == set(ids), 'Reference policy differs')
    k = len(decisions[CANDIDATE])
    for name in COMPARATORS:
        ranked = heapq.nsmallest(k, policy_map, key=lambda identifier: (-policy_map[identifier]['scores'][name], identifier))
        decisions[name + '_matched'] = set(ranked)
        require(len(decisions[name + '_matched']) == k, 'Matched-count inventory differs')

    sources = sorted({label['source'] for label in labels})
    subsets = {
        'all': labels,
        'attack_source': [label for label in labels if label['cohort'] == 'attack_source'],
        'other_source': [label for label in labels if label['cohort'] == 'other_source'],
        'previously_absent_broad_families': [label for label in labels if label['source'] not in {'attck', 'cwe'}],
        **{'source:' + source: [label for label in labels if label['source'] == source] for source in sources},
    }
    require(len(subsets['attack_source']) == 287 and len(subsets['other_source']) == 960
            and len(subsets['previously_absent_broad_families']) == 809, 'Cohort counts differ')
    require(set(result['metrics']) == set(subsets), 'Reported cohort inventory differs')
    recomputed = {}
    for cohort, rows in subsets.items():
        reported = result['metrics'][cohort]
        same(len(rows), reported['n'], cohort + '/n', counts)
        require(set(reported['arms']) == set(decisions), cohort + ': policy inventory differs')
        recomputed[cohort] = {'n': len(rows), 'arms': {}}
        for policy, use in decisions.items():
            observed = reconstruct(rows, use, answers)
            recomputed[cohort]['arms'][policy] = observed
            stated = reported['arms'][policy]
            for field in ('evidence_use_n', 'evidence_use_pct', 'mean_delta_vs_vanilla_pp'):
                same(observed[field], stated[field], cohort + '/' + policy + '/' + field, counts)
            finite_interval(stated['mean_delta_ci95_pp'], cohort + '/' + policy + '/mean interval')
            require(set(stated['models']) == set(MODELS), 'Reported model inventory differs')
            for model, metrics in observed['models'].items():
                for field, value in metrics.items():
                    same(value, stated['models'][model][field], cohort + '/' + policy + '/' + model + '/' + field, counts)
                finite_interval(stated['models'][model]['delta_ci95_pp'], cohort + '/' + policy + '/' + model + '/interval')

    require(set(result['matched_comparisons']) == set(COMPARATORS), 'Comparison inventory differs')
    comparison_checks = {}
    overall = recomputed['all']['arms']
    for comparator in COMPARATORS:
        reported = result['matched_comparisons'][comparator]
        differences = {model: 100.0 * (overall[CANDIDATE]['models'][model]['correct']
            - overall[comparator + '_matched']['models'][model]['correct']) / len(labels) for model in MODELS}
        for model, value in differences.items():
            same(value, reported['candidate_minus_comparator_pp'][model], comparator + '/' + model + '/difference', counts)
            finite_interval(reported['model_ci95_pp'][model], comparator + '/' + model + '/difference interval')
        mean = sum(differences.values()) / len(MODELS)
        same(mean, reported['mean_difference_pp'], comparator + '/mean difference', counts)
        same(k, reported['matched_evidence_count'], comparator + '/matched count', counts)
        interval = finite_interval(reported['mean_ci95_pp'], comparator + '/mean difference interval')
        point_gate = all(value >= 1 - 1e-10 for value in differences.values())
        combined_gate = point_gate and interval[0] > 0
        same(combined_gate, reported['pass'], comparator + '/gate', counts)
        comparison_checks[comparator] = {'both_models_gain_at_least_1pp': point_gate,
            'reported_mean_ci_lower_positive': interval[0] > 0, 'combined_pass': combined_gate}

    reconstructed_gates = {}
    require(set(result['useful_signal_gates']) == set(MODELS), 'Useful-gate model inventory differs')
    for model in MODELS:
        overall_gain = overall[CANDIDATE]['models'][model]['delta_vs_vanilla_pp']
        attack = recomputed['attack_source']['arms']
        gain = attack[CANDIDATE]['models'][model]['delta_vs_vanilla_pp']
        always_gain = attack['always_evidence']['models'][model]['delta_vs_vanilla_pp']
        other_gain = recomputed['other_source']['arms'][CANDIDATE]['models'][model]['delta_vs_vanilla_pp']
        reported_ci = result['metrics']['other_source']['arms'][CANDIDATE]['models'][model]['delta_ci95_pp']
        checks = {
            'overall_gain_at_least_3pp': overall_gain >= 3 - 1e-10,
            'positive_attack_gain_retains_half_positive_always_gain': always_gain > 0 and gain > 0 and 2 * gain >= always_gain - 2e-10,
            'other_net_loss_no_worse_2pp': other_gain >= -2 - 1e-10,
            'other_ci_lower_above_minus5pp': reported_ci[0] > -5,
        }
        for name, value in checks.items():
            same(value, result['useful_signal_gates'][model][name], model + '/' + name, counts)
        reconstructed_gates[model] = checks
    useful = all(all(checks.values()) for checks in reconstructed_gates.values())
    added = all(check['combined_pass'] for check in comparison_checks.values())
    status = 'EXTERNAL_TRANSPORT_CRITERIA_NOT_MET'
    if useful:
        status = 'EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE' if added else 'EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN'
    same(useful, result['useful_signal'], 'useful_signal', counts)
    same(added, result['added_value'], 'added_value', counts)
    same(status, result['status'], 'classification', counts)

    return {'status': 'PASS', 'completed_utc': datetime.now(timezone.utc).isoformat(),
        'audit_role': 'Post-freeze independent reconstruction; no model or policy selection',
        'implementation': 'Python standard-library per-question counters; independent parsing and heap ranking; no analyzer imports',
        'bootstrap_scope': 'Not independently recomputed. Interval structure and gates using reported bounds checked only.',
        'comparisons_checked': counts['compared_values'], 'questions': 1247,
        'qualification_outputs': 32, 'fresh_outputs': 4988, 'cohorts': len(subsets),
        'policies_per_cohort': len(decisions), 'models': list(MODELS),
        'all_frozen_hashes_verified': True, 'all_frozen_thresholds_verified': True,
        'inventory_parser_validity_and_runtime_counts_verified': True,
        'all_point_metrics_match': True, 'matched_counts_and_difference_gates_match': True,
        'matched_evidence_count': k, 'invalid_outputs': dict(invalid),
        'reconstructed_classification': status, 'reconstructed_useful_signal_gates': reconstructed_gates,
        'comparison_checks': comparison_checks, 'recomputed_point_metrics': recomputed,
        'matched_policy_ids': {name + '_matched': sorted(decisions[name + '_matched']) for name in COMPARATORS},
        'provenance_sha256': {'audit_script': digest(Path(__file__)), 'RESULTS.json': digest(results_path),
            'scientific_freeze': digest(root / 'SCIENTIFIC_FREEZE.json'),
            'sealed_labels': digest(root / 'sealed_labels.jsonl'),
            'policies': digest(root / 'policy_predictions.jsonl'),
            **{name: digest(outputs / name) for name in ('runtime.json', 'predictions.jsonl', 'qualification.jsonl')}}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--outputs', type=Path, required=True)
    parser.add_argument('--results', type=Path, default=ROOT / 'RESULTS.json')
    parser.add_argument('--report', type=Path, default=ROOT / 'INDEPENDENT_RESULTS_AUDIT.json')
    args = parser.parse_args()
    if args.report.exists():
        raise FileExistsError('Refusing to overwrite an independent audit receipt: ' + str(args.report))
    report = audit(ROOT, args.outputs, args.results)
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: report[key] for key in ('status', 'questions', 'fresh_outputs',
        'comparisons_checked', 'all_point_metrics_match', 'reconstructed_classification')}, indent=2))


if __name__ == '__main__':
    main()
