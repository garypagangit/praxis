"""Score a complete frozen external CTI run; never tune policy thresholds."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np

from frozen_inference import strict_parse
from inference_worker import MODELS

ROOT = Path(__file__).resolve().parent
MODEL_NAMES = ['llama', 'qwen']
COMPARATORS = ['relevance', 'relevance_options', 'source_classifier', 'question_utility']
CANDIDATE = 'evidence_utility'


def read(path):
    return [json.loads(x) for x in Path(path).read_text(encoding='utf-8-sig').splitlines() if x.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def interval(values):
    return [float(x) for x in np.percentile(values, [2.5, 97.5])]


def bootstrap_weights(source):
    """Question resampling within fixed observed source counts; NOT source clusters."""
    rng = np.random.default_rng(20260918)
    weights = np.zeros((5000, len(source)), dtype=np.float32)
    for group in sorted(set(source)):
        idx = np.flatnonzero(source == group)
        weights[:, idx] = rng.multinomial(len(idx), np.full(len(idx), 1/len(idx)), size=5000)
    return weights / len(source)


def check_frozen(root):
    freeze = json.loads((root/'SCIENTIFIC_FREEZE.json').read_text())
    required = {'analyze_external.py', 'PROTOCOL.md', 'sealed_labels.jsonl', 'policy_predictions.jsonl',
                'generator_inputs.jsonl', 'qualification_inputs.jsonl', 'inference_worker.py', 'frozen_inference.py'}
    require(required <= set(freeze['files']), 'Essential scientific files omitted from freeze')
    for name, digest in freeze['files'].items():
        require(sha(root/name) == digest, 'Scientific frozen file changed: '+name)
    require('analyze_external.py' in freeze['files'], 'Analysis was not frozen')
    return freeze


def matched_selection(scores, ids, count):
    scores = np.asarray(scores, dtype=float)
    require(scores.shape == (len(ids),) and np.isfinite(scores).all(), 'Invalid matching scores')
    require(len(set(ids)) == len(ids) and 0 <= count <= len(ids), 'Invalid matching inventory/count')
    ranked = sorted(range(len(ids)), key=lambda k: (-scores[k], ids[k]))
    take = np.zeros(len(ids), dtype=bool)
    take[ranked[:count]] = True
    return take


def summarize_policy(base, evidence, use, weights):
    pick = np.where(use[:, None], evidence, base)
    delta = pick.astype(float)-base
    draws = weights @ delta * 100
    by_model = {}
    for j, model in enumerate(MODEL_NAMES):
        benefits = ~base[:, j] & evidence[:, j]
        harms = base[:, j] & ~evidence[:, j]
        by_model[model] = {'correct': int(pick[:, j].sum()), 'accuracy_pct': float(pick[:, j].mean()*100),
            'delta_vs_vanilla_pp': float(delta[:, j].mean()*100), 'delta_ci95_pp': interval(draws[:, j]),
            'recovered_answers': int((use & benefits).sum()), 'induced_errors': int((use & harms).sum()),
            'prevented_errors': int((~use & harms).sum()), 'lost_improvements': int((~use & benefits).sum())}
    return {'evidence_use_n': int(use.sum()), 'evidence_use_pct': float(use.mean()*100),
            'models': by_model, 'mean_delta_vs_vanilla_pp': float(delta.mean()*100),
            'mean_delta_ci95_pp': interval(draws.mean(axis=1))}


def evaluate(root, output):
    freeze = check_frozen(root)
    labels = read(root/'sealed_labels.jsonl')
    policies = read(root/'policy_predictions.jsonl')
    ids = [r['id'] for r in labels]
    require(len(ids) == 1247 and len(set(ids)) == 1247, 'Label inventory mismatch')
    require(all(r['answer'] in 'ABCD' and len(r['answer']) == 1 for r in labels), 'Invalid reference answer')
    policy_map = {r['id']: r for r in policies}
    require(len(policy_map) == len(policies) == 1247 and set(policy_map) == set(ids), 'Policy inventory mismatch')
    runtime = json.loads((output/'runtime.json').read_text())
    require(runtime['status'] == 'COMPLETE', 'Generator run is incomplete')
    require(runtime['inputs_sha256'] == sha(root/'generator_inputs.jsonl'), 'Different generator inputs')
    require(runtime['qualification_sha256'] == sha(root/'qualification_inputs.jsonl'), 'Different qualification inputs')
    require(runtime['worker_sha256'] == sha(root/'inference_worker.py'), 'Different worker')
    require(runtime['frozen_inference_sha256'] == sha(root/'frozen_inference.py'), 'Different inference helper')
    require(runtime['predictions_sha256'] == sha(output/'predictions.jsonl'), 'Prediction digest mismatch')
    require(runtime['qualification_outputs_sha256'] == sha(output/'qualification.jsonl'), 'Qualification digest mismatch')
    require(runtime['decoding'] == {'batch_size': 2, 'dtype': 'float16', 'do_sample': False,
            'max_input_tokens': 4096, 'max_new_tokens': 8}, 'Decoding settings mismatch')
    specs = {key: (model, revision) for key, model, revision in MODELS}
    expected_prompt_hashes = {}
    for phase, filename in [('qualification', 'qualification_inputs.jsonl'), ('test', 'generator_inputs.jsonl')]:
        for row in read(root/filename):
            for field, condition in [('vanilla_prompt', 'vanilla'), ('evidence_prompt', 'relationship_evidence')]:
                expected_prompt_hashes[(phase, row['id'], condition)] = hashlib.sha256(row[field].encode()).hexdigest()

    def verify_receipt(r):
        require((r['model_id'], r['revision']) == specs[r['model']], 'Model revision mismatch')
        require(0 < r['input_tokens'] <= 4096, 'Input length mismatch')
        require(len(r['prompt_sha256']) == 64 and all(c in '0123456789abcdef' for c in r['prompt_sha256']), 'Missing rendered prompt digest')
        require(r['input_prompt_sha256'] == expected_prompt_hashes[(r['phase'], r['id'], r['condition'])], 'Wrong prompt assigned to output')
    qids = {r['id'] for r in read(root/'qualification_inputs.jsonl')}
    require(len(qids) == 8, 'Qualification input inventory mismatch')
    qualification = read(output/'qualification.jsonl')
    expected_q = {(i, m, c) for i in qids for m in MODEL_NAMES for c in ('vanilla', 'relationship_evidence')}
    actual_q = [(r['id'], r['model'], r['condition']) for r in qualification]
    require(len(actual_q) == len(set(actual_q)) == 32 and set(actual_q) == expected_q, 'Incomplete qualification outputs')
    for r in qualification:
        verify_receipt(r)
        answer = strict_parse(r['raw_output'])
        require(r['phase'] == 'qualification' and r['valid'] is True and answer == r['parsed_answer']
                and len(answer) == 1 and answer in 'ABCD', 'Qualification validity mismatch')
    raw = read(output/'predictions.jsonl')
    expected = {(i, m, c) for i in ids for m in MODEL_NAMES for c in ('vanilla', 'relationship_evidence')}
    keys = [(r['id'], r['model'], r['condition']) for r in raw]
    require(len(keys) == len(set(keys)) == 4988 and set(keys) == expected, 'Fresh prediction inventory mismatch')
    prediction = {}
    invalid = Counter()
    for r in raw:
        verify_receipt(r)
        answer = strict_parse(r['raw_output'])
        valid = len(answer) == 1 and answer in 'ABCD'
        require((r['model_id'], r['revision']) == specs[r['model']], 'Model revision mismatch')
        require(r['phase'] == 'test' and r['parsed_answer'] == answer and r['valid'] is valid, 'Parser mismatch')
        require(0 < r['input_tokens'] <= 4096, 'Input length mismatch')
        require(len(r['prompt_sha256']) == 64, 'Missing rendered prompt digest')
        invalid[r['model']+'/'+r['condition']] += int(not valid)
        prediction[(r['id'], r['model'], r['condition'])] = answer
    for model in MODEL_NAMES:
        require(runtime['qualification'][model]['records'] == 16 and runtime['qualification'][model]['valid'] == 16
                and runtime['qualification'][model]['invalid'] == 0, 'Qualification summary mismatch')
        invalid_n = invalid[model+'/vanilla']+invalid[model+'/relationship_evidence']
        require(runtime['test'][model]['records'] == 2494 and runtime['test'][model]['invalid'] == invalid_n
                and runtime['test'][model]['valid'] == 2494-invalid_n, 'Test summary mismatch')
    gold = [r['answer'] for r in labels]
    vanilla = np.array([[prediction[(i, m, 'vanilla')] == a for m in MODEL_NAMES] for i, a in zip(ids, gold)])
    evidence = np.array([[prediction[(i, m, 'relationship_evidence')] == a for m in MODEL_NAMES] for i, a in zip(ids, gold)])
    names = ['always_vanilla', 'always_evidence', *COMPARATORS, CANDIDATE]
    decisions = {}
    for name in names:
        decision = [policy_map[i]['use_evidence'][name] for i in ids]
        require(all(type(x) is bool for x in decision), 'Policy decisions must be boolean')
        decisions[name] = np.array(decision)
    require(not decisions['always_vanilla'].any() and decisions['always_evidence'].all(), 'Reference policy mismatch')
    candidate_count = int(decisions[CANDIDATE].sum())
    for name in COMPARATORS:
        scores = np.array([policy_map[i]['scores'][name] for i in ids])
        decisions[name+'_matched'] = matched_selection(scores, ids, candidate_count)
    chosen = {k: np.where(v[:, None], evidence, vanilla) for k, v in decisions.items()}
    source = np.array([r['source'] for r in labels])
    cohort = np.array([r['cohort'] for r in labels])
    require(sum(cohort == 'attack_source') == 287 and sum(cohort == 'other_source') == 960, 'Cohort mismatch')
    subsets = {'all': np.ones(len(ids), dtype=bool), 'attack_source': cohort == 'attack_source',
               'other_source': cohort == 'other_source', 'previously_absent_broad_families': ~np.isin(source, ['attck', 'cwe'])}
    require(int(subsets['previously_absent_broad_families'].sum()) == 809, 'New-family inventory mismatch')
    subsets.update({'source:'+s: source == s for s in sorted(set(source))})
    metrics = {}
    all_weights = None
    for subset, include in subsets.items():
        n = int(include.sum())
        weights = bootstrap_weights(source[include])
        if subset == 'all':
            all_weights = weights
        base = vanilla[include]
        ev = evidence[include]
        arms = {}
        for name, values in chosen.items():
            use = decisions[name][include]
            arms[name] = summarize_policy(base, ev, use, weights)
        metrics[subset] = {'n': n, 'arms': arms}
    comparisons = {}
    for name in COMPARATORS:
        diff = chosen[CANDIDATE].astype(float)-chosen[name+'_matched']
        draws = all_weights @ diff * 100
        point = diff.mean(axis=0)*100
        ci = interval(draws.mean(axis=1))
        comparisons[name] = {'candidate_minus_comparator_pp': dict(zip(MODEL_NAMES, map(float, point))),
            'model_ci95_pp': {m: interval(draws[:, j]) for j, m in enumerate(MODEL_NAMES)},
            'mean_difference_pp': float(point.mean()), 'mean_ci95_pp': ci,
            'pass': bool(np.all(point >= 1-1e-10) and ci[0] > 0), 'matched_evidence_count': candidate_count}
    gates = {}
    for model in MODEL_NAMES:
        all_delta = metrics['all']['arms'][CANDIDATE]['models'][model]['delta_vs_vanilla_pp']
        attack_gain = metrics['attack_source']['arms'][CANDIDATE]['models'][model]['delta_vs_vanilla_pp']
        always_gain = metrics['attack_source']['arms']['always_evidence']['models'][model]['delta_vs_vanilla_pp']
        other = metrics['other_source']['arms'][CANDIDATE]['models'][model]
        gates[model] = {'overall_gain_at_least_3pp': all_delta >= 3-1e-10,
            'positive_attack_gain_retains_half_positive_always_gain': always_gain > 0 and attack_gain > 0 and attack_gain >= .5*always_gain-1e-10,
            'other_net_loss_no_worse_2pp': other['delta_vs_vanilla_pp'] >= -2-1e-10,
            'other_ci_lower_above_minus5pp': other['delta_ci95_pp'][0] > -5}
    useful = all(all(checks.values()) for checks in gates.values())
    added = all(r['pass'] for r in comparisons.values())
    status = ('EXTERNAL_USEFUL_SIGNAL_AND_ADDED_VALUE' if added else 'EXTERNAL_USEFUL_SIGNAL_ADDED_VALUE_UNPROVEN') if useful else 'EXTERNAL_TRANSPORT_CRITERIA_NOT_MET'
    result = {'status': status, 'completed_utc': datetime.now(timezone.utc).isoformat(), 'n': len(ids),
        'fresh_outputs': len(raw), 'qualification_outputs': len(qualification), 'invalid_outputs': dict(invalid),
        'metrics': metrics, 'matched_comparisons': comparisons, 'useful_signal_gates': gates,
        'useful_signal': useful, 'added_value': added,
        'bootstrap': {'replicates': 5000, 'seed': 20260918, 'method': 'paired questions within fixed coarse-source counts; NOT source clusters'},
        'files_sha256': {name: sha(output/name) for name in ('runtime.json', 'predictions.jsonl', 'qualification.jsonl')},
        'scientific_freeze_sha256': sha(root/'SCIENTIFIC_FREEZE.json'),
        'human_review_complete': False, 'claim_boundary': 'Released-label benchmark agreement; no algorithmic novelty or independent source-document generalization established.'}
    (root/'RESULTS.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    records = []
    for j, row in enumerate(labels):
        records.append({'id': row['id'], 'source': row['source'], 'cohort': row['cohort'], 'released_answer': row['answer'],
            'outcomes': {m: {'vanilla': bool(vanilla[j, k]), 'evidence': bool(evidence[j, k])} for k, m in enumerate(MODEL_NAMES)},
            'use_evidence': {name: bool(d[j]) for name, d in decisions.items()}})
    (root/'scored_records.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records), encoding='utf-8')
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--outputs', type=Path, required=True)
    args = p.parse_args()
    result = evaluate(ROOT, args.outputs)
    print(json.dumps({k: result[k] for k in ('status', 'n', 'fresh_outputs', 'useful_signal', 'added_value')}))


if __name__ == '__main__':
    main()
