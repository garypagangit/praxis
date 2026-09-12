"""Independent, standard-library audit for the frozen MiCRo logic qualification.

No model calls, training, or network access. Scores preserve pinned harness quirks;
truncated responses remain in primary exact-match scoring as preregistered.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import re
from datetime import datetime, timezone

CONDITIONS = ('intact', 'logic_ablation', 'social_ablation')
TECHNICAL_CHECKS = ('pinned_bundle', 'exact_checkpoint_load', 'finite', 'repeat_equal',
    'ablation_reset_equal', 'cache_top_token_equal', 'cache_max_abs_within_tolerance',
    'ablation_routes_zero', 'eager_sdpa_top_token_equal', 'eager_sdpa_max_abs_within_tolerance')
STRICT_PATTERN = r'The answer is (\-?[0-9\.\,]+).'
FLEXIBLE_PATTERN = r'(-?[$0-9.,]{2,})|(-?[0-9]+)'
IGNORE_PATTERNS = (',', r'\$', r'(?s).*#### ', r'\.$')
INVALID = '[invalid]'
FROZEN_PROTOCOL = {'study_id': 'fp006-logic-qualification-v1', 'test_n': 256, 'pilot_n': 16, 'conditions': ['intact', 'logic_ablation', 'social_ablation'], 'prompt_template': "Q: {question}\nA: Let's think step by step.", 'chat_template': False, 'add_special_tokens': True, 'bos_token_id': 128000, 'eos_token_ids': [128001, 128009], 'pad_token_id': 128004, 'stop_strings': ['Q:', '</s>', '<|im_end|>'], 'max_new_tokens': 1024, 'do_sample': False, 'seed': 20260912, 'batch_size': 1, 'dtype': 'bfloat16', 'attention': 'sdpa', 'cache_max_abs_tolerance': 0.25, 'numerical_prompts': ['A simple arithmetic question: 2 + 2 =', 'There are three boxes with five apples each. The total number of apples is'], 'bootstrap_replicates': 10000, 'bootstrap_seed': 20260912, 'primary_metric': 'harness_flexible_extract_exact_match', 'gates': {'intact_accuracy_min': 0.25, 'intact_truncation_max': 0.1, 'intact_numeric_extraction_min': 0.9, 'logic_loss_min': 0.1, 'logic_loss_bootstrap_lower_strictly_above': 0.0}, 'inference_seconds_limit': 24000, 'supervisor_seconds_limit': 27000, 'host_hours_limit': 8, 'total_usd_cap': 75, 'paper_score_reproduction_claimed': False, 'novel_method_tested': False}
HARNESS_COMMIT = 'ad8737ae7fad24cf64e50fc7fc31397bff586b9e'
HARNESS_TASK_SHA256 = 'c506c7f5c19da2817db443f7e6d943421dfc9237510a70991d2667cf8efce1e0'


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def text_sha(value):
    return sha_bytes(value.encode('utf-8'))


def raw_prompt(question):
    return "Q: " + question + "\nA: Let's think step by step."


def extract_prediction(response, mode='flexible'):
    """Match pinned RegexFilter, including first strict and last flexible match."""
    if mode not in ('strict', 'flexible'):
        raise ValueError('Unknown extraction mode')
    if not isinstance(response, str):
        response = ''
    matches = re.findall(STRICT_PATTERN if mode == 'strict' else FLEXIBLE_PATTERN, response)
    if not matches:
        return INVALID
    match = matches[0 if mode == 'strict' else -1]
    if isinstance(match, tuple):
        nonempty = [m for m in match if m]
        match = nonempty[0] if nonempty else INVALID
    return match.strip()


def normalize_exact(value):
    """Exact pinned metric: regex removal then lowercase; no Decimal or strip."""
    if not isinstance(value, str):
        raise TypeError('Exact-match input must be a string')
    for pattern in IGNORE_PATTERNS:
        value = re.sub(pattern, '', value)
    return value.lower()


def score_response(response, answer):
    result = {}
    reference = normalize_exact(answer)
    for mode in ('strict', 'flexible'):
        extracted = extract_prediction(response, mode)
        result[mode + '_prediction'] = extracted
        result[mode + '_extracted'] = extracted != INVALID
        result[mode + '_contains_digit'] = extracted != INVALID and bool(re.search(r'\d', extracted))
        result[mode + '_correct'] = int(normalize_exact(extracted) == reference)
    return result


def interpolated_percentile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    low, high = math.floor(position), math.ceil(position)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (position - low)


def paired_statistics(intact, comparison, replicates=10000, seed=20260912):
    """Positive effect means intact performs better; paired IDs are never dropped."""
    if set(intact) != set(comparison) or not intact:
        raise ValueError('Paired estimates require identical nonempty ID sets')
    ids = sorted(intact)
    if any(v not in (0, 1) for v in list(intact.values()) + list(comparison.values())):
        raise ValueError('Correctness must be binary')
    if not isinstance(replicates, int) or replicates < 2:
        raise ValueError('At least two bootstrap replicates required')
    diffs = [intact[i] - comparison[i] for i in ids]
    rng = random.Random(seed)
    draws = sorted(sum(rng.choices(diffs, k=len(diffs))) / len(diffs) for _ in range(replicates))
    harmful = sum(intact[i] == 1 and comparison[i] == 0 for i in ids)
    recoveries = sum(intact[i] == 0 and comparison[i] == 1 for i in ids)
    return {'n': len(ids), 'intact_correct': sum(intact.values()),
        'comparison_correct': sum(comparison.values()), 'correct_to_wrong': harmful,
        'wrong_to_correct': recoveries, 'discordant': harmful + recoveries,
        'difference': sum(diffs) / len(diffs),
        'ci95': [interpolated_percentile(draws, .025), interpolated_percentile(draws, .975)],
        'quantile_method': 'linear interpolation at (replicates - 1) * probability',
        'bootstrap_replicates': replicates, 'seed': seed,
        'interval_scope': 'paired questions, not training seeds or model families'}


def qualification_gate(n, intact_correct, logic_correct, intact_truncated,
                       intact_extracted, ci_lower, complete, technical):
    if n <= 0:
        return {'passed': False, 'components': {'nonempty_cohort': False}}
    components = {
        'complete_frozen_cohort': complete is True,
        'all_technical_checks': technical is True,
        'intact_accuracy_at_least_25pct': intact_correct * 4 >= n,
        'intact_truncation_at_most_10pct': intact_truncated * 10 <= n,
        'intact_extraction_at_least_90pct': intact_extracted * 10 >= n * 9,
        'logic_loss_at_least_10pp': (intact_correct - logic_correct) * 10 >= n,
        'paired_ci_lower_positive': isinstance(ci_lower, (int, float)) and math.isfinite(ci_lower) and ci_lower > 0,
    }
    return {'passed': all(components.values()), 'components': components,
        'integer_thresholds': {'minimum_intact_correct': math.ceil(n * .25),
          'maximum_intact_truncated': n // 10,
          'minimum_intact_extracted': math.ceil(n * .9),
          'minimum_net_logic_loss': math.ceil(n * .1)}}


def _unique_json(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=_unique_json)


def audit_records(data, protocol, cells, protocol_sha256, technical, data_sha256=None):
    """Validate and summarize cells without modifying any original artifact."""
    errors = []
    expected = {}
    if not isinstance(data, dict):
        errors.append('data:top_level_must_be_object'); data = {}
    if not isinstance(protocol, dict):
        errors.append('protocol:top_level_must_be_object'); protocol = {}
    require = lambda condition, message: errors.append(message) if not condition else None
    for name, expected_value in FROZEN_PROTOCOL.items():
        require(protocol.get(name) == expected_value, 'protocol:' + name + '_mismatch')
    require(isinstance(data_sha256, str) and len(data_sha256) == 64 and data_sha256 == protocol.get('data_sha256'), 'data:frozen_raw_file_sha256')
    for split, count in (('pilot', 16), ('test', 256)):
        cohort = data.get(split, [])
        require(isinstance(cohort, list) and len(cohort) == count, 'data:' + split + '_cohort_size')
        if not isinstance(cohort, list):
            cohort = []
        seen = set()
        for row in cohort:
            try:
                key = (split, row['id'])
                if key in expected:
                    raise ValueError('duplicate_id')
                if not all(isinstance(row[k], str) for k in ('id', 'question', 'answer', 'gold', 'question_sha256')):
                    raise ValueError('field_types')
                if text_sha(row['question']) != row['question_sha256']:
                    raise ValueError('question_hash')
                if normalize_exact(row['answer']) != normalize_exact(row['gold']):
                    raise ValueError('gold_does_not_match_original_answer')
                normalized_question = ' '.join(row['question'].casefold().split())
                if normalized_question in seen:
                    raise ValueError('duplicate_question')
                seen.add(normalized_question)
                expected[key] = row
            except (KeyError, ValueError, TypeError) as exc:
                errors.append('data:' + split + ':' + str(exc))
    pilot_questions = {' '.join(r['question'].casefold().split()) for (s, _), r in expected.items() if s == 'pilot'}
    test_questions = {' '.join(r['question'].casefold().split()) for (s, _), r in expected.items() if s == 'test'}
    require(not (pilot_questions & test_questions), 'data:pilot_test_question_overlap')
    indexed = {}
    for index, cell in enumerate(cells):
        try:
            split, identifier, condition = cell['split'], cell['id'], cell['condition']
            key = (split, identifier, condition)
            if key in indexed:
                raise ValueError('duplicate_cell')
            if (split, identifier) not in expected or condition not in CONDITIONS:
                raise ValueError('unexpected_cohort_or_condition')
            row = expected[(split, identifier)]
            if cell['question_sha256'] != row['question_sha256']:
                raise ValueError('question_hash')
            if cell['prompt_sha256'] != text_sha(raw_prompt(row['question'])):
                raise ValueError('prompt_hash')
            if cell['protocol_sha256'] != protocol_sha256:
                raise ValueError('protocol_hash')
            if cell['gold'] != row['gold']:
                raise ValueError('gold_identity')
            if not isinstance(cell['response'], str):
                raise ValueError('response_type')
            if cell['response_sha256'] != text_sha(cell['response']):
                raise ValueError('response_hash')
            tokens = cell['generated_token_ids']
            if not isinstance(tokens, list) or not all(type(x) is int and x >= 0 for x in tokens):
                raise ValueError('token_ids')
            if type(cell['tokens']) is not int or cell['tokens'] != len(tokens) or not 0 < len(tokens) <= 1024:
                raise ValueError('token_count')
            if type(cell['seconds']) not in (int, float) or not math.isfinite(cell['seconds']) or cell['seconds'] < 0:
                raise ValueError('seconds')
            if cell['stop_reason'] not in ('eos', 'stop_string', 'token_cap'):
                raise ValueError('stop_reason')
            if cell['stop_reason'] == 'eos' and tokens[-1] not in (128001, 128009):
                raise ValueError('eos_identity')
            if cell['stop_reason'] == 'token_cap' and len(tokens) != 1024:
                raise ValueError('cap_length')
            if any(t in (128001, 128009) for t in tokens[:-1]):
                raise ValueError('tokens_after_eos')
            routes = cell['routes']
            if not isinstance(routes, list) or len(routes) != 4 or not all(type(x) is int and x >= 0 for x in routes):
                raise ValueError('route_counts')
            if type(cell['prompt_tokens']) is not int or cell['prompt_tokens'] <= 0:
                raise ValueError('prompt_token_count')
            if sum(routes) != 16 * (cell['prompt_tokens'] + cell['tokens'] - 1):
                raise ValueError('route_accounting')
            for phase in ('prefill_routes', 'decode_routes'):
                counts = cell[phase]
                if not isinstance(counts, list) or len(counts) != 4 or not all(type(x) is int and x >= 0 for x in counts):
                    raise ValueError(phase + '_format')
            if any(a + b != total for a, b, total in zip(cell['prefill_routes'], cell['decode_routes'], routes)):
                raise ValueError('route_phase_sum')
            if sum(cell['prefill_routes']) != 16 * cell['prompt_tokens'] or sum(cell['decode_routes']) != 16 * (cell['tokens'] - 1):
                raise ValueError('route_phase_accounting')
            if condition == 'logic_ablation' and routes[0] != 0:
                raise ValueError('logic_ablation_still_routes_logic')
            if condition == 'social_ablation' and routes[1] != 0:
                raise ValueError('social_ablation_still_routes_social')
            indexed[key] = {**cell, **score_response(cell['response'], row['answer'])}
        except (KeyError, ValueError, TypeError) as exc:
            errors.append('cell:' + str(index) + ':' + str(exc))
    expected_keys = {(split, identifier, condition) for split, identifier in expected for condition in CONDITIONS}
    missing = sorted(expected_keys - set(indexed))
    checks = technical.get('checks', {}) if isinstance(technical, dict) else {}
    if not isinstance(checks, dict):
        checks = {}
    technical_status = {name: checks.get(name) is True for name in TECHNICAL_CHECKS}
    all_technical = all(technical_status.values()) and not errors
    complete = not missing and not errors and len(indexed) == 816
    report = {'status': 'COMPLETE' if complete else 'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY',
        'protocol_sha256': protocol_sha256, 'data_sha256': data_sha256, 'expected_cells': 816, 'recorded_cells': len(cells),
        'validated_unique_cells': len(indexed), 'missing_cell_count': len(missing),
        'missing_cells': [{'split': s, 'id': i, 'condition': c} for s, i, c in missing],
        'integrity_errors': errors, 'technical_checks': technical_status,
        'all_technical_checks': all_technical, 'splits': {},
        'scoring': {'harness_commit': HARNESS_COMMIT, 'task_sha256': HARNESS_TASK_SHA256,
            'primary': 'flexible exact match including truncated outputs',
            'extraction_gate': 'pinned flexible RegexFilter result contains a digit and differs from [invalid]',
            'normalization': 'regex removal then lowercasing; no arithmetic/numeric coercion',
            'uncertainty_scope': 'paired question bootstrap; no training-seed uncertainty'}}
    for split in ('pilot', 'test'):
        cohort_ids = sorted(i for s, i in expected if s == split)
        arm_results = {}
        for condition in CONDITIONS:
            rr = [indexed[(split, i, condition)] for i in cohort_ids if (split, i, condition) in indexed]
            n = len(rr)
            arm_results[condition] = {'n': n, 'planned_n': len(cohort_ids),
                'strict_correct': sum(r['strict_correct'] for r in rr),
                'flexible_correct': sum(r['flexible_correct'] for r in rr),
                'strict_extracted': sum(r['strict_extracted'] for r in rr),
                'flexible_extracted': sum(r['flexible_extracted'] for r in rr),
                'flexible_contains_digit': sum(r['flexible_contains_digit'] for r in rr),
                'truncated': sum(r['stop_reason'] == 'token_cap' for r in rr),
                'empty': sum(not r['response'].strip() for r in rr),
                'correct_and_truncated': sum(r['flexible_correct'] and r['stop_reason'] == 'token_cap' for r in rr),
                'nontruncated_n': sum(r['stop_reason'] != 'token_cap' for r in rr),
                'nontruncated_flexible_correct': sum(r['flexible_correct'] and r['stop_reason'] != 'token_cap' for r in rr),
                'nontruncated_flexible_accuracy': (sum(r['flexible_correct'] and r['stop_reason'] != 'token_cap' for r in rr) / sum(r['stop_reason'] != 'token_cap' for r in rr)) if any(r['stop_reason'] != 'token_cap' for r in rr) else None,
                'stop_reasons': dict(Counter(r['stop_reason'] for r in rr)),
                'tokens': sum(r['tokens'] for r in rr), 'sum_request_seconds': sum(r['seconds'] for r in rr),
                'routes': [sum(r['routes'][j] for r in rr) for j in range(4)],
                'flexible_accuracy': sum(r['flexible_correct'] for r in rr) / n if n else None}
        common = [i for i in cohort_ids if all((split, i, c) in indexed for c in CONDITIONS)]
        paired = {}
        if common:
            for mode in ('strict', 'flexible'):
                reference = {i: indexed[(split, i, 'intact')][mode + '_correct'] for i in common}
                for condition in ('logic_ablation', 'social_ablation'):
                    comparison = {i: indexed[(split, i, condition)][mode + '_correct'] for i in common}
                    paired[mode + '/intact_minus_' + condition] = paired_statistics(reference, comparison)
                social = {i: indexed[(split, i, 'social_ablation')][mode + '_correct'] for i in common}
                logic = {i: indexed[(split, i, 'logic_ablation')][mode + '_correct'] for i in common}
                paired[mode + '/social_minus_logic'] = paired_statistics(social, logic)
        sensitivity = {}
        for condition in ('logic_ablation', 'social_ablation'):
            eligible = [i for i in common if indexed[(split, i, 'intact')]['stop_reason'] != 'token_cap' and indexed[(split, i, condition)]['stop_reason'] != 'token_cap']
            estimate = paired_statistics({i:indexed[(split,i,'intact')]['flexible_correct'] for i in eligible}, {i:indexed[(split,i,condition)]['flexible_correct'] for i in eligible}) if eligible else None
            sensitivity['intact_minus_' + condition] = {'n':len(eligible), 'excluded_truncated_pairs':len(common)-len(eligible), 'estimate':estimate, 'descriptive_only':True, 'selection_warning':'Conditions determine inclusion; this is not the full-cohort primary estimand and never enters gates.'}
        report['splits'][split] = {'arms': arm_results, 'complete_paired_questions': len(common),
            'paired': paired, 'jointly_nontruncated_sensitivity':sensitivity, 'descriptive_only': split == 'pilot' or not complete}
    test = report['splits']['test']; intact = test['arms']['intact']; logic = test['arms']['logic_ablation']
    effect = test['paired'].get('flexible/intact_minus_logic_ablation', {})
    report['qualification'] = qualification_gate(256, intact['flexible_correct'], logic['flexible_correct'],
        intact['truncated'], intact['flexible_contains_digit'], effect.get('ci95', [None])[0], complete, all_technical)
    report['qualification']['decision'] = 'PASS_USEFUL_LOGIC_PREREQUISITE_ONLY' if report['qualification']['passed'] else 'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'
    report['limitations'] = ['No novelty, containment, or fault-transfer efficacy claim.',
        'Flexible extraction may reward the last number in unfinished reasoning; truncation remains separate.',
        'Independent audit checks IDs, hashes, metadata and arithmetic; it does not re-decode token IDs or inspect weight tensors.',
        'Question uncertainty is not uncertainty across model families, seeds or measurement protocols.',
        'Incomplete/invalid cohorts and pilot results cannot pass qualification.']
    return report


def render_report(result):
    lines = ['# MiCRo logic qualification: independent audit', '',
        '**Status:** ' + result['status'] + '. **Decision:** ' + result['qualification']['decision'] + '.', '',
        'Primary scoring is frozen flexible exact match, including truncated outputs. Pilot results are descriptive only.', '',
        '| Test arm | Completed | Flexible correct | Strict correct | Numeric extracted | Truncated |',
        '|---|---:|---:|---:|---:|---:|']
    for condition, row in result['splits']['test']['arms'].items():
        lines.append(f"| {condition} | {row['n']}/{row['planned_n']} | {row['flexible_correct']} | {row['strict_correct']} | {row['flexible_contains_digit']} | {row['truncated']} |")
    lines += ['', 'Paired effects are intact minus ablated accuracy; positive values indicate lost ability after ablation.', '']
    for name, value in result['splits']['test']['paired'].items():
        if not name.startswith('flexible/'):
            continue
        lo, hi = value['ci95']
        lines.append(f"- {name}: {100*value['difference']:.2f} percentage points [95% paired bootstrap {100*lo:.2f}, {100*hi:.2f}], n={value['n']}; correct-to-wrong={value['correct_to_wrong']}, wrong-to-correct={value['wrong_to_correct']}.")
    lines += ['', 'Jointly nontruncated sensitivity (descriptive; outcome-dependent subset; never changes gates):', '']
    for name, row in result['splits']['test']['jointly_nontruncated_sensitivity'].items():
        estimate = row['estimate']
        text = 'no eligible paired responses' if estimate is None else f"{100*estimate['difference']:.2f} percentage points; n={row['n']}"
        lines.append('- ' + name + ': ' + text + '.')
    lines += ['', 'Gate components:', '']
    lines += ['- ' + name + ': ' + ('PASS' if value else 'FAIL') for name, value in result['qualification']['components'].items()]
    lines += ['', f"Integrity errors: {len(result['integrity_errors'])}; missing cells: {result['missing_cell_count']}.", '',
        'All required technical checks must pass. Social ablation is diagnostic, not an additional gate. A pass establishes a useful-specialist prerequisite only.', '',
        'Limitations:', ''] + ['- ' + s for s in result['limitations']]
    return '\n'.join(lines) + '\n'


def read_cells(run_dir):
    records, receipts, errors = [], [], []
    paths = sorted((run_dir / 'cells').glob('*.json'))
    if (run_dir / 'cells.jsonl').exists():
        paths.append(run_dir / 'cells.jsonl')
    for path in paths:
        raw = path.read_bytes(); receipts.append({'file': str(path.relative_to(run_dir)), 'sha256': sha_bytes(raw), 'bytes': len(raw)})
        try:
            if path.suffix == '.jsonl':
                for number, line in enumerate(raw.decode('utf-8-sig').splitlines(), 1):
                    if line.strip():
                        try: records.append(json.loads(line, object_pairs_hook=_unique_json))
                        except (ValueError, TypeError) as exc: errors.append(path.name + ':' + str(number) + ':' + str(exc))
            else:
                records.append(json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_unique_json))
        except (ValueError, TypeError) as exc:
            errors.append(path.name + ':' + str(exc))
    return records, receipts, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--technical', type=Path, required=True)
    parser.add_argument('--report-dir', type=Path)
    args = parser.parse_args()
    cells, receipts, parse_errors = read_cells(args.run_dir)
    technical = load_json(args.technical) if args.technical.exists() else {}
    result = audit_records(load_json(args.data), load_json(args.protocol), cells, sha_bytes(args.protocol.read_bytes()), technical, sha_bytes(args.data.read_bytes()))
    if parse_errors:
        result['integrity_errors'].extend(parse_errors)
        result['status'] = 'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY'
        result['qualification']['passed'] = False
        result['qualification']['components']['complete_frozen_cohort'] = False
        result['qualification']['decision'] = 'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'
        result['all_technical_checks'] = False
        result['qualification']['components']['all_technical_checks'] = False
        for split in result['splits'].values():
            split['descriptive_only'] = True
    result['input_receipts'] = receipts + [{'file': str(p), 'sha256': sha_bytes(p.read_bytes()), 'bytes': p.stat().st_size} for p in (args.data, args.protocol, args.technical) if p.exists()]
    result['audit_utc'] = datetime.now(timezone.utc).isoformat()
    destination = args.report_dir or args.run_dir
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    (destination / 'RESULTS.md').write_text(render_report(result), encoding='utf-8')
    print(json.dumps({'status': result['status'], 'validated_cells': result['validated_unique_cells'],
        'qualification': result['qualification']['decision'], 'integrity_errors': len(result['integrity_errors'])}))
    if result['status'] != 'COMPLETE' or not result['all_technical_checks']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
