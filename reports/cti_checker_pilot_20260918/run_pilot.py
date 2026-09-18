"""Source-grouped retrospective evidence-selection pilot; see PROTOCOL.md."""
from __future__ import annotations
import argparse
import collections
import copy
import hashlib
import importlib.metadata
import json
import math
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import sparse
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parent
SEED = 20260918
MODELS = ('llama', 'qwen')
ARMS = ('relevance', 'relevance_options', 'source_classifier', 'question_utility', 'evidence_utility')
COMPARATORS = ARMS[:-1]
TOKEN = re.compile(r'[a-z0-9]+(?:[._-][a-z0-9]+)*')
IDENT = re.compile(r'\b(?:CVE-\d{4}-\d+|[TSGM]\d{4}(?:\.\d{3})?)\b', re.I)
KINDS = ('procedure', 'mitigation', 'detection', 'tactic', 'technique', 'subtechnique')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf-8')


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def tokens(text):
    return set(TOKEN.findall(text.lower())) - ENGLISH_STOP_WORDS


def norm(text):
    return ' '.join(TOKEN.findall(text.lower()))


def question_text(row):
    # Deliberately allowlists only displayed text, never row metadata.
    return row['question'] + '\n' + '\n'.join(f'{k}. {row["options"][k]}' for k in sorted(row['options']))


def features(row, logits):
    """No source, stratum, labels, responses, or inherited support fields."""
    q = tokens(row['question'])
    docs = [x['text'] for x in row['evidence']]
    ds = [tokens(d) for d in docs]
    opts = [row['options'][k] for k in sorted(row['options'])]
    os = [tokens(o) for o in opts]
    qcov = np.array([len(q & d) / max(1, len(q)) for d in ds])
    ocov = np.array([[len(o & d)/max(1, len(o)) for d in ds] for o in os])
    obest = np.sort(ocov.max(axis=1))[::-1]
    joint = np.sort((ocov * qcov[None, :]).max(axis=1))[::-1]
    phrase = np.array([any(' '+norm(o)+' ' in ' '+norm(d)+' ' for d in docs) for o in opts])
    retrieval = np.array([float(x.get('score', 0)) for x in row['evidence']])
    lengths = np.array([len(TOKEN.findall(d.lower())) for d in docs], dtype=float)
    log = np.array(logits, dtype=float)
    qi = set(x.lower() for x in IDENT.findall(row['question']))
    di = set(x.lower() for d in docs for x in IDENT.findall(d))
    union = set().union(*ds)
    f = {
        'question_words_log': math.log1p(len(q)),
        'option_words_log': math.log1p(sum(len(o) for o in os)),
        'fact_count': len(docs),
        'fact_words_total_log': math.log1p(lengths.sum()),
        'fact_words_mean_log': math.log1p(lengths.mean()),
        'fact_words_max_log': math.log1p(lengths.max()),
        'query_coverage_union': len(q & union)/max(1, len(q)),
        'query_coverage_max': qcov.max(),
        'query_coverage_mean': qcov.mean(),
        'query_coverage_std': qcov.std(),
        'option_coverage_best': obest[0],
        'option_coverage_second': obest[1],
        'option_coverage_margin': obest[0]-obest[1],
        'option_coverage_mean': obest.mean(),
        'options_over_half': (obest >= .5).sum(),
        'options_over_80pct': (obest >= .8).sum(),
        'option_phrase_count': phrase.sum(),
        'one_option_phrase': phrase.sum() == 1,
        'joint_support_best': joint[0],
        'joint_support_second': joint[1],
        'joint_support_margin': joint[0]-joint[1],
        'retrieval_max': retrieval.max(),
        'retrieval_mean': retrieval.mean(),
        'retrieval_std': retrieval.std(),
        'relevance_max': log.max(),
        'relevance_mean': log.mean(),
        'relevance_std': log.std(),
        'relevance_min': log.min(),
        'relevance_top_gap': np.sort(log)[-1]-np.sort(log)[-2],
        'query_identifier_count': len(qi),
        'query_identifier_coverage': len(qi & di)/max(1, len(qi)),
        'other_evidence_identifier_count_log': math.log1p(len(di-qi)),
    }
    for kind in KINDS:
        f['kind_'+kind] = sum(x['kind'] == kind for x in row['evidence'])/len(docs)
    return f


def load_data():
    data = rows(ROOT/'data.jsonl')
    assert len(data) == 2500 and len({r['id'] for r in data}) == 2500
    eligible = np.array([r['eligible'] for r in data], dtype=bool)
    assert eligible.sum() == 1578
    groups = np.array([r['source_group'] for r in data])
    base = np.array([[r['outcomes'][m]['vanilla'] for m in MODELS] for r in data], dtype=float)
    evidence = np.array([[r['outcomes'][m]['evidence'] for m in MODELS] for r in data], dtype=float)
    assert np.array_equal(base.sum(axis=0), [1618, 1571])
    assert np.array_equal(evidence.sum(axis=0), [1767, 1629])
    return data, eligible, groups, base, evidence


def freeze():
    data, eligible, groups, _, _ = load_data()
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    fold = np.full(len(data), -1)
    for i, (_, test) in enumerate(splitter.split(np.zeros(len(data)), eligible, groups)):
        fold[test] = i
    splits = []
    for i in range(5):
        a, b, c = fold != i, fold == (i+1)%5, fold == i
        a &= ~b
        ga, gb, gc = (set(groups[x]) for x in (a, b, c))
        assert not ga & gb and not ga & gc and not gb & gc
        splits.append({'test_fold': i, 'validation_fold': (i+1)%5,
            'train_n': int(a.sum()), 'validation_n': int(b.sum()), 'test_n': int(c.sum()),
            'test_eligible': int(eligible[c].sum()), 'test_mismatch': int((~eligible[c]).sum()),
            'train_groups': len(ga), 'validation_groups': len(gb), 'test_groups': len(gc)})
    splitrows = [{'id': r['id'], 'fold': int(f), 'source_group': r['source_group']} for r, f in zip(data, fold)]
    dump(ROOT/'SPLITS.json', splitrows)
    names = ['PROTOCOL.md', 'run_pilot.py', 'prepare_data.py', 'score_relevance.py',
             'score_relevance_options.py', 'prepare_relevance_options.py',
             'data.jsonl', 'data_relevance_options.jsonl', 'SPLITS.json']
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'seed': SEED,
                'status': 'FROZEN_BEFORE_SELECTOR_FITTING', 'retrospective': True,
                'sha256': {n: sha(ROOT/n) for n in names}, 'fold_summary': splits}
    dump(ROOT/'FREEZE.json', manifest)
    print(json.dumps(manifest, indent=2))


def threshold(scores, delta, eligible):
    choices = np.unique(np.r_[np.inf, np.quantile(scores, np.linspace(0, 1, 101)), -np.inf])
    best = None
    for t in choices:
        use = scores >= t
        coverage = use.mean()
        d = delta * use[:, None]
        if .15 <= coverage <= .85 and np.all(d[~eligible].mean(axis=0) >= -.02-1e-12):
            key = (float(d.mean()), -float(coverage), float(t))
            if best is None or key > best[0]:
                best = (key, t, coverage, d[~eligible].mean(axis=0))
    if best is None:
        return np.inf, {'feasible': False, 'threshold': None, 'fallback': 'never_evidence'}
    _, t, coverage, mismatch = best
    return t, {'feasible': True, 'threshold': float(t), 'evidence_use': float(coverage),
               'mean_utility': best[0][0], 'mismatch_deltas': mismatch.tolist()}


def top_k(scores, ids, k):
    order = np.lexsort((np.asarray(ids), -np.asarray(scores)))
    mask = np.zeros(len(scores), dtype=bool)
    mask[order[:k]] = True
    return mask


def vectorizers():
    return (TfidfVectorizer(ngram_range=(1, 2), max_features=20000, min_df=2,
                           sublinear_tf=True, dtype=np.float64),
            TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=30000,
                            min_df=2, sublinear_tf=True, dtype=np.float64))


def verified_scores(input_name, output_name, metadata_name, data):
    scored = rows(ROOT/output_name)
    meta = json.loads((ROOT/metadata_name).read_text(encoding='utf-8'))
    digest = sha(ROOT/input_name)
    assert meta['status'] == 'COMPLETE'
    assert meta['input_sha256'] == digest
    assert meta['output_sha256'] == sha(ROOT/output_name)
    assert len(scored) == len(data)
    assert {r['id'] for r in scored} == {r['id'] for r in data}
    assert len({r['id'] for r in scored}) == len(data)
    assert all(r['input_sha256'] == digest and r['spec_sha256'] == meta['spec_sha256'] for r in scored)
    assert all(r['model_revision'] == '233902d25c440f23af6f7d6e94d2946bac0bee0a' for r in scored)
    source = {r['id']: r for r in data}
    for r in scored:
        assert len(r['logits']) == r['evidence_count'] == len(source[r['id']]['evidence'])
        assert np.isfinite(r['logits']).all()
    return {r['id']: r for r in scored}


def fit():
    start = time.perf_counter()
    frozen = json.loads((ROOT/'FREEZE.json').read_text())
    for name, h in frozen['sha256'].items():
        assert sha(ROOT/name) == h, f'Freeze changed: {name}'
    data, eligible, groups, base, ev = load_data()
    delta = ev-base
    target = delta.mean(axis=1)
    foldrows = json.loads((ROOT/'SPLITS.json').read_text())
    assert [r['id'] for r in foldrows] == [r['id'] for r in data]
    folds = np.array([r['fold'] for r in foldrows])
    scoremap = verified_scores('data.jsonl', 'relevance_scores.jsonl', 'relevance_metadata.json', data)
    # Scorer uses per-fact raw logits. No outcome fields enter this join.
    logits = [scoremap[r['id']]['logits'] for r in data]
    option_data = rows(ROOT/'data_relevance_options.jsonl')
    assert [r['id'] for r in option_data] == [r['id'] for r in data]
    for original, projected in zip(data, option_data):
        assert projected['question'] == question_text(original)
        assert projected['evidence'] == original['evidence']
    option_map = verified_scores('data_relevance_options.jsonl', 'relevance_options_scores.jsonl',
                                'relevance_options_metadata.json', option_data)
    option_scores = np.array([max(option_map[r['id']]['logits']) for r in data])
    assert all(len(x) == len(r['evidence']) for r, x in zip(data, logits))
    fdicts = [features(r, s) for r, s in zip(data, logits)]
    names = list(fdicts[0])
    dense = np.array([[f[n] for n in names] for f in fdicts], dtype=float)
    assert np.isfinite(dense).all()
    text = [question_text(r) for r in data]
    # A concrete leakage regression check: mutate every forbidden metadata field.
    altered = copy.deepcopy(data[0])
    altered.update(source_group='TRAP', eligible=not data[0]['eligible'],
                   expected_output='TRAP', option_support_scores={'A': 999999},
                   source_url='TRAP', technique_id='TRAP', source_pointer_relationship_evidence='TRAP')
    altered['outcomes'] = {'TRAP': 999999}
    assert question_text(altered) == text[0]
    assert features(altered, logits[0]) == fdicts[0]
    dump(ROOT/'FEATURE_AUDIT.json', {'safe_text_fields': ['question', 'options'],
          'safe_evidence_fields': ['text', 'kind', 'score'], 'numerical_features': names,
          'forbidden_field_mutation_invariance': True, 'data_sha256': sha(ROOT/'data.jsonl')})
    oof = {a: np.full(len(data), np.nan) for a in ARMS}
    decisions = {a: np.zeros(len(data), dtype=bool) for a in ARMS}
    decisions.update({a+'_matched': np.zeros(len(data), dtype=bool) for a in COMPARATORS})
    records = []
    for f in range(5):
        t0 = time.perf_counter()
        test = np.flatnonzero(folds == f)
        val = np.flatnonzero(folds == (f+1)%5)
        train = np.flatnonzero((folds != f) & (folds != (f+1)%5))
        gt, gv, ge = (set(groups[x]) for x in (train, val, test))
        assert not (gt & gv or gt & ge or gv & ge)
        vectors = vectorizers()
        xtr = sparse.hstack([v.fit_transform([text[i] for i in train]) for v in vectors], format='csr')
        xva = sparse.hstack([v.transform([text[i] for i in val]) for v in vectors], format='csr')
        xte = sparse.hstack([v.transform([text[i] for i in test]) for v in vectors], format='csr')
        scale = StandardScaler().fit(dense[train])
        ztr = sparse.hstack([xtr, sparse.csr_matrix(scale.transform(dense[train]))], format='csr')
        zva = sparse.hstack([xva, sparse.csr_matrix(scale.transform(dense[val]))], format='csr')
        zte = sparse.hstack([xte, sparse.csr_matrix(scale.transform(dense[test]))], format='csr')
        tfit = time.perf_counter()
        src = LogisticRegression(C=1, class_weight='balanced', max_iter=2000, random_state=SEED).fit(xtr, eligible[train])
        source_fit_seconds = time.perf_counter()-tfit
        tfit = time.perf_counter()
        qu = Ridge(alpha=10, solver='lsqr').fit(xtr, target[train])
        question_fit_seconds = time.perf_counter()-tfit
        tfit = time.perf_counter()
        eu = Ridge(alpha=10, solver='lsqr').fit(ztr, target[train])
        evidence_fit_seconds = time.perf_counter()-tfit
        valscores = {'relevance': dense[val, names.index('relevance_max')],
                     'relevance_options': option_scores[val],
                     'source_classifier': src.predict_proba(xva)[:, 1],
                     'question_utility': qu.predict(xva), 'evidence_utility': eu.predict(zva)}
        testscores = {'relevance': dense[test, names.index('relevance_max')],
                     'relevance_options': option_scores[test],
                     'source_classifier': src.predict_proba(xte)[:, 1],
                     'question_utility': qu.predict(xte), 'evidence_utility': eu.predict(zte)}
        calibration = {}
        for arm in ARMS:
            t, rec = threshold(valscores[arm], delta[val], eligible[val])
            assert np.isfinite(testscores[arm]).all()
            decisions[arm][test] = testscores[arm] >= t
            oof[arm][test] = testscores[arm]
            calibration[arm] = rec
        k = int(decisions['evidence_utility'][test].sum())
        for arm in COMPARATORS:
            decisions[arm+'_matched'][test] = top_k(testscores[arm], [data[i]['id'] for i in test], k)
            assert decisions[arm+'_matched'][test].sum() == k
        coefficients = {n: float(c) for n, c in zip(names, eu.coef_[-len(names):])}
        records.append({'fold': f, 'train_n': len(train), 'validation_n': len(val), 'test_n': len(test),
                        'calibration': calibration, 'fit_and_score_seconds': time.perf_counter()-t0,
                        'estimator_fit_seconds': {'source_classifier': source_fit_seconds,
                            'question_utility': question_fit_seconds, 'evidence_utility': evidence_fit_seconds},
                        'candidate_standardized_dense_coefficients': coefficients})
        print(f'Finished fold {f}: {len(train)} train / {len(val)} validation / {len(test)} test', flush=True)
    assert all(np.isfinite(s).all() for s in oof.values())
    with (ROOT/'predictions.jsonl').open('w', encoding='utf-8') as out:
        for i, row in enumerate(data):
            record = {'id': row['id'], 'fold': int(folds[i]),
                'scores': {a: float(oof[a][i]) for a in ARMS},
                'use_evidence': {a: bool(v[i]) for a, v in decisions.items()}}
            out.write(json.dumps(record, allow_nan=False)+'\n')
    dump(ROOT/'FIT_RECEIPT.json', {'finished_utc': datetime.now(timezone.utc).isoformat(),
         'elapsed_seconds': time.perf_counter()-start, 'folds': records,
         'freeze_sha256': sha(ROOT/'FREEZE.json'), 'relevance_scores_sha256': sha(ROOT/'relevance_scores.jsonl'),
         'relevance_options_scores_sha256': sha(ROOT/'relevance_options_scores.jsonl'),
         'predictions_sha256': sha(ROOT/'predictions.jsonl'), 'python': sys.version,
         'versions': {p: importlib.metadata.version(p) for p in ('numpy', 'scipy', 'scikit-learn')}})


def analyze():
    data, eligible, groups, base, ev = load_data()
    pred = rows(ROOT/'predictions.jsonl')
    assert [r['id'] for r in pred] == [r['id'] for r in data]
    policies = {'always_vanilla': np.zeros(len(data), bool), 'always_evidence': np.ones(len(data), bool)}
    policies.update({a: np.array([r['use_evidence'][a] for r in pred]) for a in pred[0]['use_evidence']})
    delta = ev-base
    outcomes = {a: base + use[:, None]*delta for a, use in policies.items()}
    unique, index = np.unique(groups, return_inverse=True)
    rng = np.random.default_rng(SEED)
    weights = rng.multinomial(len(unique), np.full(len(unique), 1/len(unique)), size=5000).astype(float)
    agg = sparse.csr_matrix((np.ones(len(data)), (index, np.arange(len(data)))), shape=(len(unique), len(data)))
    def interval(values, mask):
        means = weights @ np.asarray(agg @ (values*mask))
        den = weights @ np.asarray(agg @ mask.astype(float))
        assert (den > 0).all()
        return [float(v) for v in np.quantile(100*means/den, [.025, .975])]
    masks = {'all': np.ones(len(data), bool), 'eligible': eligible, 'mismatch': ~eligible,
             'excluding_prior_500': np.array([not r['previously_exposed'] for r in data])}
    metrics = {}
    for arm, use in policies.items():
        metrics[arm] = {}
        for cohort, mask in masks.items():
            per = {}
            for j, model in enumerate(MODELS):
                d = (outcomes[arm][:, j]-base[:, j])
                helpful, harmful = delta[:, j] > 0, delta[:, j] < 0
                per[model] = {'n': int(mask.sum()), 'correct': int(outcomes[arm][mask, j].sum()),
                     'accuracy_pct': float(100*outcomes[arm][mask, j].mean()),
                     'delta_vs_vanilla_pp': float(100*d[mask].mean()), 'delta_ci95_pp': interval(d, mask),
                     'recovered_wrong_answers': int((mask & use & helpful).sum()),
                     'induced_mistakes': int((mask & use & harmful).sum()),
                     'prevented_mistakes': int((mask & ~use & harmful).sum()),
                     'lost_improvements': int((mask & ~use & helpful).sum())}
            per['evidence_used_n'] = int(use[mask].sum())
            per['evidence_use_pct'] = float(100*use[mask].mean())
            metrics[arm][cohort] = per
    comparisons = {}
    allmask = masks['all']
    for arm in [*COMPARATORS, *(x+'_matched' for x in COMPARATORS)]:
        dif = outcomes['evidence_utility']-outcomes[arm]
        comparisons[arm] = {model: {'difference_pp': float(100*dif[:, j].mean()),
                     'ci95_pp': interval(dif[:, j], allmask)} for j, model in enumerate(MODELS)}
        comparisons[arm]['paired_model_average'] = {'difference_pp': float(100*dif.mean()),
                     'ci95_pp': interval(dif.mean(axis=1), allmask)}
    checks = {}
    for model in MODELS:
        c = metrics['evidence_utility']
        benefit = metrics['always_evidence']['eligible'][model]['delta_vs_vanilla_pp']
        checks[model] = {
            'overall_gain_at_least_3pp': c['all'][model]['delta_vs_vanilla_pp'] >= 3-1e-9,
            'retains_half_eligible_benefit': c['eligible'][model]['delta_vs_vanilla_pp'] >= .5*benefit-1e-9,
            'mismatch_loss_no_worse_than_2pp': c['mismatch'][model]['delta_vs_vanilla_pp'] >= -2-1e-9,
            'mismatch_ci_lower_above_minus5pp': c['mismatch'][model]['delta_ci95_pp'][0] > -5}
    core = all(all(x.values()) for x in checks.values())
    added = {}
    for comparator in COMPARATORS:
        c = comparisons[comparator+'_matched']
        added[comparator] = {**{m+'_gain_at_least_1pp': c[m]['difference_pp'] >= 1-1e-9 for m in MODELS},
                           'paired_average_ci_positive': c['paired_model_average']['ci95_pp'][0] > 0}
    added_pass = all(all(x.values()) for x in added.values())
    status = 'METHOD_SPECIFIC_PILOT_SIGNAL' if core and added_pass else ('USEFUL_SELECTION_SIGNAL_ADDED_VALUE_UNPROVEN' if core else 'PILOT_CRITERIA_NOT_MET')
    dump(ROOT/'RESULTS.json', {'status': status, 'core_signal_pass': core, 'added_value_pass': added_pass,
        'core_checks': checks, 'added_value_checks': added, 'metrics': metrics, 'candidate_vs_comparator': comparisons,
        'bootstrap': {'resamples': 5000, 'seed': SEED, 'source_groups': len(unique),
                      'interpretation': 'Conditional descriptive intervals for fixed cross-fitted predictions; not fresh confirmation.'},
        'novelty_established': False, 'fresh_generator_inference': False})
    print(json.dumps({'status': status, 'core_checks': checks, 'added_value_checks': added}, indent=2))
    for arm in policies:
        a = metrics[arm]['all']
        print(arm, 'evidence_pct', round(a['evidence_use_pct'], 2),
              'accuracy', [round(a[m]['accuracy_pct'], 2) for m in MODELS])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['freeze', 'fit', 'analyze'])
    args = parser.parse_args()
    with threadpool_limits(limits=4):
        {'freeze': freeze, 'fit': fit, 'analyze': analyze}[args.mode]()
