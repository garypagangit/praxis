"""Read-only local audit of Final Praxis 006 containment artifacts; stdlib only.
The caller downloads receipts. This program performs no networking or inference.
"""
import argparse
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

THRESHOLDS = (0.5, 1.0, 1.5, 2.0)
POLICIES = ('none', 'permanent', 'conditional', 'random')
CORRUPTIONS = ('clean', 'negate', 'permute')


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def close(a, b, tol=1e-10):
    return isinstance(a, (int, float)) and math.isfinite(a) and abs(a - b) <= tol


def choose_threshold(candidates, clean_baseline):
    admitted = [x for x in candidates if x['clean_correct'] >= clean_baseline]
    if not admitted:
        raise ValueError('No threshold preserves calibration clean accuracy')
    return max(admitted, key=lambda x: (x['corrupt_correct'], x['clean_correct'],
                                       -x['interventions'], x['threshold']))


def transitions(reference, target):
    counts = {'CC': 0, 'CW': 0, 'WC': 0, 'WW': 0}
    changes = 0
    delta = []
    for a, b in zip(reference, target):
        counts[('C' if a['correct'] else 'W') + ('C' if b['correct'] else 'W')] += 1
        changes += a['prediction'] != b['prediction']
        delta.append(int(b['correct']) - int(a['correct']))
    rng = random.Random(20260912)
    n = len(delta)
    boot = sorted(sum(delta[rng.randrange(n)] for _ in range(n))/n for _ in range(2000))
    return dict(counts, prediction_changes=changes, n=n, net_correct=counts['WC']-counts['CW'],
                accuracy_difference=sum(delta)/n,
                paired_question_bootstrap_95pct=[boot[49], boot[1950]], bootstrap_replicates=2000)


def aggregate(rows):
    total = sum(r['eligible'] for r in rows)
    interventions = sum(r['interventions'] for r in rows)
    return {'n': len(rows), 'correct': sum(r['correct'] for r in rows),
            'accuracy': sum(r['correct'] for r in rows)/len(rows),
            'eligible': total, 'interventions': interventions,
            'observed_intervention_rate': interventions/total if total else 0.0,
            'effective_routes': [sum(s['monitor']['effective_counts'][e] for r in rows for s in r['scores']) for e in range(4)],
            'nominal_reported_routes': [sum(s['routing_selection_counts'][e] for r in rows for s in r['scores']) for e in range(4)]}


def likelihood_delta(rows_a, rows_b):
    deltas = [abs(a['log_likelihood']-b['log_likelihood'])
              for ra, rb in zip(rows_a, rows_b) for a, b in zip(ra['scores'], rb['scores'])]
    return {'max_abs': max(deltas), 'candidate_pairs_changed_gt_1e_6': sum(d > 1e-6 for d in deltas)}


class Audit:
    def __init__(self):
        self.errors = []
        self.warnings = []
    def check(self, condition, message):
        if not condition:
            self.errors.append(message)
    def equal(self, actual, expected, message):
        self.check(actual == expected, message + ': expected ' + repr(expected) + ', got ' + repr(actual))


def audit(input_dir, fixture_path):
    a = Audit()
    fixture = read(fixture_path)
    manifest = read(input_dir/'manifest.json')
    manifest_sha = sha(canonical(manifest))
    calibration = read(input_dir/'calibration_frozen.json')
    summary = read(input_dir/'summary.json')
    environment = read(input_dir/'environment.json')
    sanity = read(input_dir/'sanity.json')
    lock = manifest['data_lock']
    a.equal(sha((input_dir/'manifest.json').read_bytes()), manifest_sha, 'Canonical manifest bytes')
    a.equal(sha(fixture_path.read_bytes()), lock['fixture_sha256'], 'Fixture hash')
    a.equal(manifest.get('protocol'), '006-stage2-v1', 'Protocol')
    a.equal(manifest['thresholds'], list(THRESHOLDS), 'Threshold grid')
    a.equal(manifest['calibration_corruptions'], ['clean', 'negate'], 'Calibration perturbations')
    a.equal(manifest['confirmation_corruptions'], list(CORRUPTIONS), 'Confirmation perturbations')
    a.equal(manifest['permutation_shift'], 17, 'Permutation shift')
    ids = {split: [r['id'] for r in fixture[split]] for split in ('calibration', 'confirmation')}
    a.equal(len(ids['calibration']), 16, 'Calibration size')
    a.equal(len(ids['confirmation']), 32, 'Confirmation size')
    a.equal(ids['calibration'], lock['calibration_ids'], 'Locked calibration IDs and order')
    a.equal(ids['confirmation'], lock['confirmation_ids'], 'Locked confirmation IDs and order')
    a.equal(len(set(ids['calibration']+ids['confirmation'])), 48, 'Unique cohort IDs')
    a.check(not set(ids['confirmation']) & set(lock['excluded_previous_test_ids']), 'Exposed test ID overlap')
    normalize = lambda q: ' '.join(q.lower().split())
    questions = [normalize(r['question']) for split in ids for r in fixture[split]]
    a.equal(len(set(questions)), 48, 'Unique normalized questions')
    for doc, name in ((calibration, 'calibration'), (summary, 'summary')):
        a.equal(doc.get('manifest_sha256'), manifest_sha, name+' manifest hash')
    a.equal(environment.get('dtype'), 'float32', 'Reported dtype')
    a.equal(environment.get('threads'), 4, 'Reported threads')
    a.equal(environment.get('model'), manifest['checkpoint_settings'], 'Environment checkpoint settings')
    for key in ('missing_keys', 'unexpected_keys', 'mismatched_keys', 'error_msgs'):
        a.equal(environment.get('loading', {}).get(key), [], 'Strict checkpoint loading '+key)
    a.check(close(sanity.get('sham_abs_delta'), 0.0, 1e-6), 'Clean sham identity failed')
    a.check(close(sanity.get('always_vs_permanent_abs_delta'), 0.0, 1e-4), 'Always/permanent equivalence failed')
    a.warnings.append('Hardware identity, RAM, process device and actual expert FLOPs are not recorded in environment.json; join an independent launch receipt.')
    a.warnings.append('Calibration content is recomputed exclusively from training cells. File content alone cannot prove it was frozen before confirmation; retain deployment and object timestamp receipts.')
    a.warnings.append('Confidence intervals are descriptive paired question bootstrap intervals, with no multiple-comparison correction; synthetic-fault feasibility does not establish a novel method.')
    rows = {(split, r['id']): r for split in ids for r in fixture[split]}
    records = {}
    token_reference = {}
    files = sorted((input_dir/'cells').glob('*.json'))
    for path in files:
        try:
            r = read(path)
            name = path.name
            ident = r['identity']
            expected_ident = [manifest_sha, r['split'], r['id'], r['corruption'], r['policy'], r['threshold'], r['random_rate']]
            a.equal(ident, expected_ident, name+' identity')
            a.equal(path.stem, sha(canonical(ident)), name+' filename digest')
            key = (r['split'], r['id'], r['corruption'], r['policy'], r['threshold'])
            a.check(key not in records, name+' duplicate semantic cell')
            records[key] = r
            row = rows[(r['split'], r['id'])]
            choices = row['choices']
            a.equal(len(r['scores']), len(choices['label']), name+' choice count')
            a.equal(len(choices['label']), 4, name+' expected four choices')
            a.equal(r['gold'], row['answerKey'], name+' gold label')
            ll = [s['log_likelihood'] for s in r['scores']]
            a.check(all(math.isfinite(x) and x <= 1e-5 for x in ll), name+' invalid log likelihood')
            winner = max(range(len(ll)), key=ll.__getitem__)
            predicted = choices['label'][winner]
            a.equal(r['prediction'], predicted, name+' raw likelihood winner')
            a.equal(r['correct'], predicted == row['answerKey'], name+' correctness')
            a.check(type(r['correct']) is bool, name+' correctness must be Boolean')
            eligible = interventions = 0
            for j, score in enumerate(r['scores']):
                tag = name+':choice'+str(j)
                tokens = score['token_ids']
                a.check(len(tokens) > 0 and all(type(t) is int and t >= 0 for t in tokens), tag+' invalid target IDs')
                a.equal(score['continuation_tokens'], len(tokens), tag+' target count')
                a.equal(score['choice_characters'], len(choices['text'][j]), tag+' choice character count')
                token_key = (r['split'], r['id'], j)
                if token_key in token_reference:
                    a.equal(tokens, token_reference[token_key], tag+' cross-panel tokenization')
                else:
                    token_reference[token_key] = tokens
                monitor = score['monitor']
                e, i = monitor['eligible'], monitor['interventions']
                nominal, effective = score['routing_selection_counts'], monitor['effective_counts']
                a.check(len(nominal) == len(effective) == 4, tag+' route vector size')
                a.check(all(type(v) is int and v >= 0 for v in nominal+effective+[e, i]), tag+' nonnegative integer counters')
                a.check(0 <= i <= e <= sum(effective), tag+' intervention count bounds')
                a.equal(sum(nominal), sum(effective), tag+' route total conservation')
                a.check(sum(effective) % 30 == 0 and sum(effective) >= 60, tag+' 30-block full-sequence route count')
                a.equal(effective[1], e-i, tag+' remaining social selections')
                a.check(close(monitor['distance_sum'], max(0, min(2*e, monitor['distance_sum'])), 1e-3), tag+' distance sum range')
                a.equal(monitor['corrupted_selected'], 0 if r['corruption']=='clean' else e, tag+' actuator mask count')
                if r['policy'] in ('none', 'permanent') or (r['policy']=='conditional' and r['threshold']==2.0):
                    a.equal(i, 0, tag+' disabled fallback')
                if r['policy']=='permanent':
                    a.equal((e, nominal[1], effective[1]), (0, 0, 0), tag+' permanent social exclusion')
                eligible += e
                interventions += i
            a.equal(r['eligible'], eligible, name+' summed eligible')
            a.equal(r['interventions'], interventions, name+' summed interventions')
        except (KeyError, TypeError, ValueError, IndexError, OverflowError) as exc:
            a.errors.append(path.name+' malformed record: '+repr(exc))
    counts = Counter(r.get('split') for r in records.values())
    a.equal(len(files), 576, 'Cell file count')
    a.equal(dict(counts), {'calibration': 192, 'confirmation': 384}, 'Split cell counts')
    expected_cal = {( 'calibration', q, c, p, t) for q in ids['calibration'] for c in ('clean', 'negate')
                    for p, t in [('none', 2.0), ('permanent', 2.0)]+[('conditional', t) for t in THRESHOLDS]}
    actual_cal = {k for k in records if k[0]=='calibration'}
    a.equal(actual_cal, expected_cal, 'Exact calibration panel coverage')
    result = {'manifest_sha256': manifest_sha, 'cells': len(files), 'split_counts': dict(counts),
              'unique_question_choice_pairs': len(token_reference), 'environment': environment, 'sanity': sanity}
    if a.errors:
        return dict(result, integrity_status='FAIL', errors=a.errors, warnings=a.warnings)
    def panel(split, corruption, policy, threshold):
        return [records[(split, q, corruption, policy, threshold)] for q in ids[split]]
    candidates = []
    for threshold in THRESHOLDS:
        clean = panel('calibration', 'clean', 'conditional', threshold)
        corrupt = panel('calibration', 'negate', 'conditional', threshold)
        candidates.append({'threshold': threshold, 'clean_correct': sum(r['correct'] for r in clean),
                           'corrupt_correct': sum(r['correct'] for r in corrupt),
                           'interventions': sum(r['interventions'] for r in clean+corrupt),
                           'eligible': sum(r['eligible'] for r in clean+corrupt)})
    clean_baseline = sum(r['correct'] for r in panel('calibration', 'clean', 'none', 2.0))
    selected = choose_threshold(candidates, clean_baseline)
    rate = selected['interventions']/selected['eligible'] if selected['eligible'] else 0
    threshold = selected['threshold']
    expected_freeze = {'manifest_sha256': manifest_sha, 'candidates': candidates, 'selected': selected,
                       'random_rate': rate, 'clean_baseline_correct': clean_baseline, 'selection_uses_confirmation': False}
    a.equal(calibration, expected_freeze, 'Entire train-only calibration freeze')
    a.equal(summary.get('calibration'), expected_freeze, 'Summary calibration freeze')
    expected_conf = {('confirmation', q, c, p, threshold) for q in ids['confirmation'] for c in CORRUPTIONS for p in POLICIES}
    a.equal({k for k in records if k[0]=='confirmation'}, expected_conf, 'Exact confirmation panel coverage')
    for r in records.values():
        a.check(close(r['random_rate'], rate if r['split']=='confirmation' else 0), 'Cell uses frozen random rate: '+str(r['identity']))
    if a.errors:
        return dict(result, integrity_status='FAIL', errors=a.errors, warnings=a.warnings)
    panels = {c+'/'+p: panel('confirmation', c, p, threshold) for c in CORRUPTIONS for p in POLICIES}
    metrics = {name: aggregate(rs) for name, rs in panels.items()}
    original_metrics = {name: {k: v[k] for k in ('correct', 'accuracy', 'interventions', 'eligible')} for name, v in metrics.items()}
    a.equal(summary.get('metrics'), original_metrics, 'All 12 summary metric panels')
    paired = {name: transitions(panels['clean/none'], rs) for name, rs in panels.items()}
    controlled = {c+'/'+p: transitions(panels[c+'/none'], panels[c+'/'+p]) for c in CORRUPTIONS for p in ('permanent', 'conditional', 'random')}
    damage = [i for i, (clean, corrupt) in enumerate(zip(panels['clean/none'], panels['negate/none'])) if clean['correct'] and not corrupt['correct']]
    recovery = sum(panels['negate/conditional'][i]['correct'] for i in damage)
    scientific = {'clean_permanent_harms': paired['clean/permanent']['CW'],
                  'negation_damages_clean_correct': len(damage),
                  'conditional_recovers_negation_damage': recovery,
                  'conditional_clean_losses': paired['clean/conditional']['CW']}
    for key, value in scientific.items():
        a.equal(summary.get(key), value, 'Summary '+key)
    consistency = {}
    for split, corruptions in (('calibration', ('clean', 'negate')), ('confirmation', CORRUPTIONS)):
        t = 2.0 if split=='calibration' else threshold
        base = panel(split, 'clean', 'permanent', t)
        for c in corruptions:
            delta = likelihood_delta(base, panel(split, c, 'permanent', t))
            consistency[split+'/permanent_clean_vs_'+c] = delta
            a.check(delta['max_abs'] <= 1e-6, split+' permanent corruption invariance '+c)
    for c in ('clean', 'negate'):
        delta = likelihood_delta(panel('calibration', c, 'none', 2.0), panel('calibration', c, 'conditional', 2.0))
        consistency['calibration/'+c+'/disabled_vs_none'] = delta
        a.check(delta['max_abs'] <= 1e-6, 'Disabled gate identity '+c)
    for c in CORRUPTIONS:
        consistency['confirmation/clean_none_vs_'+c+'_none'] = likelihood_delta(panels['clean/none'], panels[c+'/none'])
    current_forwards = summary.get('candidate_forwards_this_execution')
    a.check(type(current_forwards) is int and 4 <= current_forwards <= 2308, 'Per-execution forward count bounds')
    a.check(close(summary.get('n'), 32), 'Summary cohort size')
    a.equal(summary.get('novel_method_established'), False, 'No novelty claim')
    a.equal(summary.get('requires_further_confirmation'), True, 'Further confirmation requirement')
    result.update(calibration_recomputed=expected_freeze, confirmation_metrics=metrics,
                  calibration_metrics={c+'/'+p+'/'+str(t): aggregate(panel('calibration', c, p, t))
                      for c in ('clean', 'negate') for p, t in [('none', 2.0), ('permanent', 2.0)]+[('conditional', t) for t in THRESHOLDS]},
                  paired_vs_clean_none=paired, paired_vs_same_corruption_none=controlled,
                  likelihood_consistency=consistency, scientific_counters=scientific,
                  feasibility={'H_M1_at_least_two_damaged': len(damage)>=2,
                      'H_M2_recovery_without_clean_loss': recovery>=1 and scientific['conditional_clean_losses']==0,
                      'conditional_negate_net_vs_permanent': metrics['negate/conditional']['correct']-metrics['negate/permanent']['correct'],
                      'conditional_negate_net_vs_random': metrics['negate/conditional']['correct']-metrics['negate/random']['correct'],
                      'interpretation': 'Feasibility screens only; superiority and naturally occurring error containment are unestablished.'},
                  compute_accounting={'logical_candidate_forwards_in_cells': 2304, 'sanity_forwards_per_execution': 4,
                      'fresh_execution_total': 2308, 'reported_current_execution': current_forwards,
                      'all_expert_blocks_per_candidate_source_contract': 120,
                      'expert_block_forward_calls_for_full_cell_set_source_contract': 276480,
                      'note': '30 blocks times 4 experts; source- and hook-supported accounting, not measured FLOPs. Resumes repeat sanity and may omit cached cells.'})
    return dict(result, integrity_status='PASS' if not a.errors else 'FAIL', errors=a.errors, warnings=a.warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.input_dir, args.fixture)
    except Exception as exc:
        result = {'integrity_status': 'FAIL', 'errors': ['Audit could not complete: '+repr(exc)], 'warnings': []}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out/'audit.json').write_bytes(canonical(result))
    lines = ['# Final Praxis 006 containment audit', '', 'Artifact integrity: **'+result['integrity_status']+'**.', '']
    if result.get('confirmation_metrics'):
        lines += ['| Condition / policy | Correct / 32 | Fallbacks / eligible |', '|---|---:|---:|']
        for name, m in result['confirmation_metrics'].items():
            lines.append('| '+name+' | '+str(m['correct'])+' / 32 | '+str(m['interventions'])+' / '+str(m['eligible'])+' |')
        lines += ['', 'Scientific counters: `'+json.dumps(result['scientific_counters'], sort_keys=True)+'`.', '',
                  'Threshold and random rate were independently reconstructed from all 192 calibration cells. All 384 confirmation cells are included. Paired intervals and all transitions are in audit.json.', '']
    if result['errors']:
        lines += ['Audit failures:', '']+['- '+e for e in result['errors']]+['']
    lines += ['Limits:', '']+['- '+w for w in result['warnings']]
    (args.out/'AUDIT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({'integrity_status': result['integrity_status'], 'errors': len(result['errors']), 'out': str(args.out)}))
    raise SystemExit(0 if result['integrity_status']=='PASS' else 1)

if __name__ == '__main__':
    main()
