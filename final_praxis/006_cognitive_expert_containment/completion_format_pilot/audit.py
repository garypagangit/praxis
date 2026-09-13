"""Independent, standard-library audit for the fixed completion-format pilot.

No model calls, training, or network access. Scores preserve pinned harness quirks;
truncated responses remain reported but cannot count toward completed-correct gates.
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
import unicodedata
from datetime import datetime, timezone

CONDITIONS = ('raw', 'chat')
TECHNICAL_CHECKS = ('pinned_bundle', 'exact_checkpoint_load', 'finite', 'repeat_equal',
    'ablation_reset_equal', 'cache_top_token_equal', 'cache_max_abs_within_tolerance',
    'ablation_routes_zero', 'eager_sdpa_top_token_equal', 'eager_sdpa_max_abs_within_tolerance')
STRICT_PATTERN = r'The answer is (\-?[0-9\.\,]+).'
FLEXIBLE_PATTERN = r'(-?[$0-9.,]{2,})|(-?[0-9]+)'
IGNORE_PATTERNS = (',', r'\$', r'(?s).*#### ', r'\.$')
INVALID = '[invalid]'
FROZEN_PROTOCOL = {'study_id': 'fp006-completion-format-pilot-v1', 'test_n': 0, 'pilot_n': 32, 'conditions': ['raw', 'chat'], 'prompt_template': "Q: {question}\nA: Let's think step by step.", 'chat_template': {'raw': False, 'chat': True}, 'add_special_tokens': {'raw': True, 'chat': False}, 'bos_token_id': 128000, 'eos_token_ids': [128001, 128009], 'pad_token_id': 128004, 'stop_strings': ['Q:', '</s>', '<|im_end|>'], 'max_new_tokens': 1024, 'do_sample': False, 'seed': 20260913, 'batch_size': 1, 'dtype': 'float32', 'attention': 'sdpa', 'cache_max_abs_tolerance': 0.001, 'numerical_prompts': ['A simple arithmetic question: 2 + 2 =', 'There are three boxes with five apples each. The total number of apples is', '<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nCutting Knowledge Date: December 2023\nToday Date: 13 Sep 2026\n\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nA simple arithmetic question: 2 + 2 =<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n', '<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nCutting Knowledge Date: December 2023\nToday Date: 13 Sep 2026\n\n<|eot_id|><|start_header_id|>user<|end_header_id|>\n\nThere are three boxes with five apples each. The total number of apples is<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n'], 'bootstrap_replicates': 10000, 'bootstrap_seed': 20260913, 'primary_metric': 'chat_nontruncated_harness_flexible_correct_count', 'gates': {'chat_truncated_max_count': 3, 'chat_numeric_extracted_min_count': 29, 'chat_nontruncated_flexible_correct_min_count': 8}, 'inference_seconds_limit': 4800, 'supervisor_seconds_limit': 6300, 'host_hours_limit': 2, 'total_usd_cap': 15, 'paper_score_reproduction_claimed': False, 'novel_method_tested': False, 'predecessor_run': 'fp006-logic-ec92d2561c', 'amendment': 'Prospective single fixed chat-wrapper feasibility pilot after raw-format qualification failed completion; no held-out TEST generation in this study', 'chat_date_string': '13 Sep 2026', 'expected_cells': 64, 'checkpoint_interventions': False, 'automatic_followup': False}
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


def _unique_json(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError('Duplicate JSON key: ' + key)
        obj[key] = value
    return obj


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'), object_pairs_hook=_unique_json)



def input_ids_sha(ids):
    return text_sha(json.dumps(ids, separators=(',', ':')))


def chat_prompt(question, date_string):
    """Pinned user-only Llama3.2 instruction template; no tools/custom system."""
    return ('<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n'
        'Cutting Knowledge Date: December 2023\nToday Date: ' + date_string + '\n\n'
        '<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n' + raw_prompt(question).strip()
        + '<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n')


def qualification_gate(chat, complete, technical):
    components = {
        'complete_frozen_64_cell_cohort': complete is True,
        'all_technical_checks': technical is True,
        'chat_truncated_at_most_3_of_32': chat['truncated'] <= 3,
        'chat_numeric_extracted_at_least_29_of_32': chat['flexible_contains_digit'] >= 29,
        'chat_nontruncated_correct_at_least_8_of_32': chat['nontruncated_flexible_correct'] >= 8,
    }
    passed = all(components.values())
    return {'passed': passed, 'components': components,
        'decision': 'QUALIFIED_FOR_FRESH_TEST_REGISTRATION' if passed else 'DO_NOT_ADVANCE_CURRENT_QUALIFICATION',
        'automatic_followup': False,
        'interpretation': 'A pass permits designing a separately frozen fresh-test qualification; it is not a full-study or investment pass.'}


def audit_records(data, protocol, cells, protocol_sha256, technical, data_sha256=None):
    errors = []
    require = lambda ok, message: errors.append(message) if not ok else None
    if not isinstance(data, dict): errors.append('data:top_level'); data = {}
    if not isinstance(protocol, dict): errors.append('protocol:top_level'); protocol = {}
    require(bool(FROZEN_PROTOCOL), 'protocol:audit_not_frozen')
    for name, expected in FROZEN_PROTOCOL.items():
        require(protocol.get(name) == expected, 'protocol:' + name + '_mismatch')
    require(isinstance(data_sha256, str) and len(data_sha256) == 64 and data_sha256 == protocol.get('data_sha256'), 'data:frozen_raw_file_sha256')
    require(set(data) == {'pilot'}, 'data:pilot_only_no_test')
    cohort = data.get('pilot', [])
    require(isinstance(cohort, list) and len(cohort) == 32, 'data:pilot_n_must_be_32')
    if not isinstance(cohort, list): cohort = []
    expected, questions = {}, set()
    for position, row in enumerate(cohort):
        try:
            if not all(isinstance(row[k], str) for k in ('id','question','answer','gold','question_sha256')):
                raise ValueError('field_types')
            if type(row['source_index']) is not int or not 0 <= row['source_index'] < 7473:
                raise ValueError('training_source_index')
            if row['id'] != f"train-{row['source_index']:04d}": raise ValueError('training_source_id')
            if row['id'] in expected: raise ValueError('duplicate_id')
            normalized = ' '.join(unicodedata.normalize('NFKC',row['question']).casefold().split())
            if normalized in questions: raise ValueError('duplicate_question')
            if text_sha(row['question']) != row['question_sha256']: raise ValueError('question_hash')
            if normalize_exact(row['answer']) != normalize_exact(row['gold']): raise ValueError('gold_reference')
            if set(row['prompts']) != set(CONDITIONS): raise ValueError('prompt_formats')
            for condition in CONDITIONS:
                manifest = row['prompts'][condition]
                prompt = raw_prompt(row['question']) if condition == 'raw' else chat_prompt(row['question'], protocol['chat_date_string'])
                if manifest['text'] != prompt or manifest['prompt_sha256'] != text_sha(prompt):
                    raise ValueError('rendered_' + condition + '_prompt')
                ids = manifest['input_token_ids']
                if not isinstance(ids, list) or not ids or not all(type(t) is int and 0 <= t < 128256 for t in ids):
                    raise ValueError('input_token_ids')
                if ids[0] != 128000 or ids.count(128000) != 1: raise ValueError('exactly_one_bos')
                if manifest['input_token_ids_sha256'] != input_ids_sha(ids): raise ValueError('input_token_ids_hash')
                if type(manifest['prompt_tokens']) is not int or manifest['prompt_tokens'] != len(ids):
                    raise ValueError('prompt_token_count')
            expected[row['id']] = row; questions.add(normalized)
        except (KeyError, TypeError, ValueError) as error:
            errors.append('data:' + str(position) + ':' + str(error))
    indexed = {}
    for position, cell in enumerate(cells):
        try:
            if cell['split'] != 'pilot' or cell['id'] not in expected or cell['condition'] not in CONDITIONS:
                raise ValueError('unexpected_cell_identity')
            key = (cell['id'], cell['condition'])
            if key in indexed: raise ValueError('duplicate_cell')
            row = expected[cell['id']]; manifest = row['prompts'][cell['condition']]
            for name, value in [('question_sha256',row['question_sha256']),('gold',row['gold']),
                ('protocol_sha256',protocol_sha256),('prompt_sha256',manifest['prompt_sha256']),
                ('input_token_ids_sha256',manifest['input_token_ids_sha256']),('prompt_tokens',manifest['prompt_tokens'])]:
                if cell[name] != value: raise ValueError(name + '_identity')
            if not isinstance(cell['response'], str) or cell['response_sha256'] != text_sha(cell['response']):
                raise ValueError('response_hash_or_type')
            ids = cell['generated_token_ids']
            if not isinstance(ids, list) or not ids or not all(type(t) is int and 0 <= t < 128256 for t in ids):
                raise ValueError('generated_token_ids')
            if type(cell['tokens']) is not int or cell['tokens'] != len(ids) or len(ids) > 1024:
                raise ValueError('generated_token_count')
            stop = cell['stop_reason']
            if stop not in ('eos','stop_string','token_cap'): raise ValueError('stop_reason')
            if stop == 'eos' and ids[-1] not in (128001,128009): raise ValueError('eos_identity')
            if stop != 'eos' and ids[-1] in (128001,128009): raise ValueError('eos_mislabeled')
            if stop == 'token_cap' and len(ids) != 1024: raise ValueError('cap_length')
            if any(t in (128001,128009) for t in ids[:-1]): raise ValueError('tokens_after_eos')
            if stop == 'stop_string' and cell.get('stop_string') not in protocol['stop_strings']:
                raise ValueError('unregistered_stop_string')
            if type(cell['seconds']) not in (int,float) or not math.isfinite(cell['seconds']) or cell['seconds'] < 0:
                raise ValueError('seconds')
            for name in ('routes','prefill_routes','decode_routes'):
                values = cell[name]
                if not isinstance(values,list) or len(values) != 4 or not all(type(x) is int and x >= 0 for x in values):
                    raise ValueError(name + '_format')
            if sum(cell['routes']) != 16 * (cell['prompt_tokens'] + cell['tokens'] - 1): raise ValueError('route_accounting')
            if sum(cell['prefill_routes']) != 16 * cell['prompt_tokens'] or sum(cell['decode_routes']) != 16 * (cell['tokens'] - 1):
                raise ValueError('route_phase_accounting')
            if any(a+b != total for a,b,total in zip(cell['prefill_routes'],cell['decode_routes'],cell['routes'])):
                raise ValueError('route_phase_sum')
            indexed[key] = {**cell, **score_response(cell['response'], row['answer'])}
        except (KeyError, TypeError, ValueError) as error:
            errors.append('cell:' + str(position) + ':' + str(error))
    missing = sorted({(identifier,c) for identifier in expected for c in CONDITIONS} - set(indexed))
    complete = not errors and not missing and len(indexed) == 64
    checks = technical.get('checks',{}) if isinstance(technical,dict) else {}
    if not isinstance(checks,dict): checks = {}
    technical_status = {name:checks.get(name) is True for name in TECHNICAL_CHECKS}
    detail_errors = []
    details = technical.get('details',[]) if isinstance(technical,dict) else []
    expected_probes = {(text_sha(text),condition) for text in protocol.get('numerical_prompts',[]) for condition in ('intact','logic_ablation','social_ablation')}
    seen_probes = set()
    if not isinstance(details,list): details = []
    if len(details) != 12: detail_errors.append('expected_12_numerical_probe_details')
    for index,detail in enumerate(details):
        try:
            identity=(detail['prompt_sha256'],detail['condition'])
            if identity not in expected_probes or identity in seen_probes: raise ValueError('unexpected_or_duplicate_probe')
            seen_probes.add(identity)
            for name in ('finite','repeat_equal','ablation_reset_equal','cache_top_token_equal','ablation_routes_zero','eager_sdpa_top_token_equal'):
                if detail.get(name) is not True: raise ValueError(name)
            for name in ('cache_max_abs','eager_sdpa_max_abs'):
                value=detail.get(name)
                if type(value) not in (int,float) or not math.isfinite(value) or not 0 <= value <= 0.001: raise ValueError(name)
        except (KeyError,TypeError,ValueError) as error:
            detail_errors.append('probe:'+str(index)+':'+str(error))
    if seen_probes != expected_probes: detail_errors.append('missing_numerical_probe_identities')
    if not isinstance(technical,dict) or technical.get('tolerance') != 0.001: detail_errors.append('technical_tolerance_identity')
    all_technical = all(technical_status.values()) and not errors and not detail_errors
    arms = {}
    for condition in CONDITIONS:
        rows = [r for (identifier,c),r in indexed.items() if c == condition]
        n = len(rows)
        arms[condition] = {'n':n,'planned_n':32,
            'flexible_correct':sum(r['flexible_correct'] for r in rows),
            'strict_correct':sum(r['strict_correct'] for r in rows),
            'strict_extracted':sum(r['strict_extracted'] for r in rows),
            'flexible_extracted':sum(r['flexible_extracted'] for r in rows),
            'flexible_contains_digit':sum(r['flexible_contains_digit'] for r in rows),
            'nontruncated_flexible_correct':sum(r['flexible_correct'] and r['stop_reason'] != 'token_cap' for r in rows),
            'truncated':sum(r['stop_reason'] == 'token_cap' for r in rows),
            'empty':sum(not r['response'].strip() for r in rows),
            'correct_and_truncated':sum(r['flexible_correct'] and r['stop_reason'] == 'token_cap' for r in rows),
            'stop_reasons':dict(Counter(r['stop_reason'] for r in rows)),
            'tokens':sum(r['tokens'] for r in rows),'sum_request_seconds':sum(r['seconds'] for r in rows),
            'routes':[sum(r['routes'][i] for r in rows) for i in range(4)],
            'flexible_accuracy':sum(r['flexible_correct'] for r in rows)/n if n else None}
    common = sorted(i for i in expected if all((i,c) in indexed for c in CONDITIONS))
    paired = {}
    if common:
        for name,field,invert in [('chat_minus_raw_flexible','flexible_correct',False),
                                  ('chat_minus_raw_completed_correct','completed_correct',False),
                                  ('raw_minus_chat_truncation','truncated',True)]:
            values = {}
            for condition in CONDITIONS:
                values[condition] = {}
                for i in common:
                    row = indexed[(i,condition)]
                    value = (row['flexible_correct'] and row['stop_reason'] != 'token_cap') if field == 'completed_correct' else ((row['stop_reason'] == 'token_cap') if field == 'truncated' else row[field])
                    values[condition][i] = int(value)
            estimate = paired_statistics(values['raw' if invert else 'chat'],values['chat' if invert else 'raw'],replicates=10000,seed=protocol.get('bootstrap_seed',20260913))
            estimate['reference_condition'] = 'raw' if invert else 'chat'
            estimate['comparison_condition'] = 'chat' if invert else 'raw'
            estimate['descriptive_only'] = True
            paired[name] = estimate
    result = {'status':'COMPLETE' if complete else 'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY',
        'protocol_sha256':protocol_sha256,'data_sha256':data_sha256,'expected_cells':64,'recorded_cells':len(cells),
        'validated_unique_cells':len(indexed),'missing_cell_count':len(missing),
        'missing_cells':[{'id':i,'condition':c} for i,c in missing],'integrity_errors':errors,
        'technical_checks':technical_status,'technical_detail_errors':detail_errors,'all_technical_checks':all_technical,
        'arms':arms,'complete_paired_questions':len(common),'paired_diagnostics':paired,
        'qualification':qualification_gate(arms['chat'],complete,all_technical),
        'scoring':{'harness_commit':HARNESS_COMMIT,'task_sha256':HARNESS_TASK_SHA256,
            'primary_gate':'nontruncated flexible-correct chat answers, on all 32 planned chat questions',
            'numeric_extraction':'flexible match containing a digit',
            'normalization':'pinned regex removals then lowercase; no numeric coercion'},
        'limitations':['This is a training-split feasibility pilot, not a held-out efficacy or novelty result.',
            'Raw is diagnostic only; it cannot replace a failed chat candidate.',
            'Pilot gates do not prove a population truncation rate below 10%.',
            'Chat text is independently rendered here; token IDs are hashed and compared to the frozen manifest, not independently decoded by this standard-library audit.',
            'Question-bootstrap intervals do not cover model seeds or families.',
            'No automatic follow-up inference is permitted by this pilot result.']}
    return result


def render_report(result):
    lines = ['# Completion-format pilot: final automated review','',
        '**Status:** '+result['status']+'. **Decision:** '+result['qualification']['decision']+'.','',
        'All 32 TRAIN questions were assigned to both formats. Both use the intact model. Raw is diagnostic; chat alone determines the fixed pilot gate.','',
        '| Format | Validated | Flexible correct | Nontruncated correct | Strict correct | Numeric extracted | Truncated |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for name,row in result['arms'].items():
        lines.append(f"| {name} | {row['n']}/32 | {row['flexible_correct']} | {row['nontruncated_flexible_correct']} | {row['strict_correct']} | {row['flexible_contains_digit']} | {row['truncated']} |")
    lines += ['', 'Registered pilot gates:', '']
    lines += ['- '+name+': '+('PASS' if value else 'FAIL') for name,value in result['qualification']['components'].items()]
    lines += ['', 'Paired diagnostics (never choose the winning format or change the gate):', '']
    for name,row in result['paired_diagnostics'].items():
        lo,hi = row['ci95']
        lines.append(f"- {name}: {100*row['difference']:.2f} percentage points [95% paired bootstrap {100*lo:.2f}, {100*hi:.2f}], n={row['n']}.")
    lines += ['',f"Integrity errors: {len(result['integrity_errors'])}; numerical-detail errors: {len(result['technical_detail_errors'])}; missing cells: {result['missing_cell_count']}.",'',
        'A passing pilot permits a separately preregistered fresh-test qualification. It does not approve a primary Praxis investment or automatically start another study.','',
        'Limitations:','']+['- '+item for item in result['limitations']]
    return '\n'.join(lines)+'\n'


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
        result['qualification']['components']['complete_frozen_64_cell_cohort'] = False
        result['qualification']['decision'] = 'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'
        result['all_technical_checks'] = False
        result['qualification']['components']['all_technical_checks'] = False
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
