"""Synthetic checks; no scientific dataset or learned base model is fitted."""
import numpy as np
import pytest

from . import run


def test_f1_threshold_matches_tied_brute_frontier():
    scores = np.array([.1, .1, .4, .4, .8, .8, .9])
    truth = np.array([0, 1, 1, 1, 0, 1, 1], dtype=bool)
    options = [-1., *np.unique(scores)]
    def key(t):
        flags = scores > t
        tp, fp, fn = (truth & flags).sum(), (~truth & flags).sum(), (truth & ~flags).sum()
        return (2 * tp / (2 * tp + fp + fn), t)
    expected = max(options, key=key)
    assert run.threshold_f1(truth, scores) == expected
    # Neither member of an equal-score group can receive a different decision.
    assert np.all((scores > expected)[scores == .4] == (.4 > expected))


def test_f1_threshold_prefers_larger_threshold_on_equal_f1():
    # All labels negative: every frontier F1 is zero; select the maximum score.
    assert run.threshold_f1(np.zeros(4, dtype=bool), np.array([0., .2, .2, .8])) == .8


@pytest.mark.parametrize('scores,budget', [([0.] * 10, .2), ([0., .2, .2, .2, .8], .4), ([.1, .5, .9], 0.)])
def test_budget_threshold_strict_ties_and_zero_budget(scores, budget):
    scores = np.asarray(scores)
    t = run.threshold_budget(scores, budget)
    assert np.sum(scores > t) <= np.floor(budget * len(scores))
    assert t in scores
    if not budget:
        assert not (scores > t).any()


def test_supports_are_repeatable_fit_only_disjoint_and_match_counts():
    # Fit pool has enough rows; calibration and test have indistinguishable labels.
    yfit = np.concatenate([np.full(40 if k != 3 else 1040, k) for k in range(6)])
    y = np.r_[yfit, np.arange(6), np.arange(6)]
    split = np.r_[np.zeros(len(yfit), dtype=int), np.ones(6, dtype=int), np.full(6, 2)]
    data = {'y': y, 'split': split, 'group_sha256': np.array([f'{i:064x}' for i in range(len(y))])}
    a, b = run.supports(data, 20260922), run.supports(data, 20260922)
    np.testing.assert_array_equal(a, b)
    assert len(np.unique(a)) == 1184
    assert np.all(split[a] == 0)
    np.testing.assert_array_equal(np.bincount(y[a]), [32, 32, 32, 1024, 32, 32])
    assert not set(a).intersection(np.flatnonzero(split != 0))


def test_crossfit_never_trains_on_held_row_or_evaluation(monkeypatch):
    y = np.tile(np.arange(6), 6)
    X = np.column_stack([np.arange(36), y])
    folds = np.repeat(np.arange(3), 12)
    seen = []
    class Spy:
        def fit(self, features, labels):
            self.ids = set(features[:, 0].astype(int)); seen.append(self.ids)
            assert self.ids.issubset(set(range(36)))
            self.full = len(self.ids) == 36
            return self
        def predict_proba(self, features):
            ids = set(features[:, 0].astype(int))
            assert not ids.intersection(self.ids), 'in-sample base prediction used'
            p = np.full((len(features), 6), .05)
            p[np.arange(len(features)), features[:, 1].astype(int)] = .75
            return p
    monkeypatch.setattr(run, 'make_model', lambda *args: Spy())
    out, _, metadata = run.crossfit('xgboost', X, y, folds, 7,
        np.array([[100, 0], [101, 1]]), np.array([[200, 2], [201, 3]]))
    assert len(seen) == 4
    for fold in range(3):
        assert seen[fold] == set(np.flatnonzero(folds != fold))
    assert seen[3] == set(range(36))
    assert np.isfinite(out['oof']).all()
    np.testing.assert_array_equal(out['oof'].argmax(axis=1), y)
    assert sum(x['validation_rows'] for x in metadata) == 36


def test_engineering_is_row_local_label_free_with_missingness():
    names = ['Total Length of Fwd Packet', 'Total Length of Bwd Packet',
             'Total Fwd Packet', 'Total Bwd packets', 'Flow Duration',
             'Flow IAT Std', 'Flow IAT Mean', 'Fwd IAT Std', 'Fwd IAT Mean',
             'Bwd IAT Std', 'Bwd IAT Mean', 'Packet Length Std',
             'Packet Length Mean', 'Active Std', 'Active Mean']
    X = np.zeros((3, len(names)))
    X[0, :4] = [90, 9, 9, 3]
    X[1, 0] = np.nan
    X[2] = -1
    out = run.engineered(X, names)
    assert out.shape == (3, len(names) + 18)
    np.testing.assert_allclose(out[[2, 0, 1]], run.engineered(X[[2, 0, 1]], names), equal_nan=True)
    np.testing.assert_allclose(out[0], run.engineered(X[:1], names)[0])
    assert np.isclose(out[0, len(names) + 3], .9)
    assert np.isnan(out[1, len(names)])
    assert np.isfinite(out[2]).all()
    np.testing.assert_array_equal(out[:, :len(names)], X)


def test_ovr_normalization_is_not_raw_score_weighting():
    general = np.array([[.8, .2]])
    independent_experts = np.array([[.8, .8]])
    equal_models = .5 * (general + run.normalize(independent_experts))
    wrong = run.normalize(.5 * (general + independent_experts))
    np.testing.assert_allclose(equal_models, [[.65, .35]])
    assert not np.allclose(equal_models, wrong)
    np.testing.assert_allclose(run.normalize(np.zeros((1, 6))), np.full((1, 6), 1 / 6))


def test_learned_fusion_fits_only_oof_inputs(monkeypatch):
    class SpyLogistic:
        def __init__(self, **kwargs):
            assert kwargs['C'] == 1
        def fit(self, X, y):
            np.testing.assert_allclose(X, run.logits(np.array([[.1], [.2], [.3], [.4]])))
            np.testing.assert_array_equal(y, [0, 1, 0, 1])
            return self
        def predict_proba(self, X):
            assert X.shape == (2, 1)
            return np.tile([.25, .75], (2, 1))
    monkeypatch.setattr(run, 'LogisticRegression', SpyLogistic)
    part = {'oof': np.array([.1, .2, .3, .4]), 'cal': np.array([.8, .9]), 'test': np.array([.6, .7])}
    out, _ = run.learned_fusion([part], np.array([0, 1, 0, 1]), binary=True)
    np.testing.assert_array_equal(out['test'], [.75, .75])


def test_stage_identification_and_any_attack_are_distinct():
    y = np.arange(6)
    scores = np.eye(6) * .9 + .1 / 6
    # Exfiltration is predicted as LateralMovement: an attack alert, wrong stage.
    scores[0] = scores[2]
    m = run.stage_metrics(y, scores)
    assert m['per_stage']['DataExfiltration']['recall'] == 0
    assert m['per_stage']['DataExfiltration']['any_attack_recall'] == 1
    assert m['any_attack_recall'] == 1


def test_independent_auditor_reconstructs_all_metrics_and_tied_frontiers():
    from . import audit
    rng = np.random.default_rng(91)
    ycal, ytest = np.tile(np.arange(6), 12), np.tile(np.arange(6), 10)
    # Discrete scores make threshold ties substantial rather than accidental.
    cal, test = rng.integers(0, 8, len(ycal)) / 8, rng.integers(0, 8, len(ytest)) / 8
    audit.compare(run.exfil_metrics(ycal, ytest, cal, test),
                  audit.exfil_metrics(ycal, ytest, cal, test, run.CLASSES, run.BUDGETS))
    probabilities = rng.dirichlet(np.ones(6), len(ytest))
    audit.compare(run.stage_metrics(ytest, probabilities), audit.stage_metrics(ytest, probabilities, run.CLASSES))
    assert audit.best_f1_threshold(ycal == 0, cal) == run.threshold_f1(ycal == 0, cal)


def test_auditor_rejects_changed_prediction_artifact(tmp_path):
    from . import audit
    packet = tmp_path / 'PREDICTIONS.npz'
    np.savez(packet, score=np.array([.2, .8]))
    bound = {'PREDICTIONS.npz': audit.digest(packet)}
    audit.verify_hashes(tmp_path, bound, ['PREDICTIONS.npz'])
    np.savez(packet, score=np.array([.8, .2]))
    with pytest.raises(audit.AuditError, match='hash mismatch'):
        audit.verify_hashes(tmp_path, bound, ['PREDICTIONS.npz'])


def test_auditor_rejects_rewritten_summary_and_probability_semantics():
    from . import audit
    truth = {'seed': 1, 'metric': {'fp': 10, 'f1': .4}}
    with pytest.raises(audit.AuditError):
        audit.compare({'seed': 1, 'metric': {'fp': 9, 'f1': .4}}, truth)
    with pytest.raises(audit.AuditError):
        audit.compare({'seed': 1, 'metric': {'fp': 10, 'f1': .5}}, truth)
    with pytest.raises(audit.AuditError, match='row sums'):
        audit.probability(np.ones((3, 6)), 3, 6)
    with pytest.raises(audit.AuditError, match='range'):
        audit.probability(np.array([.2, np.nan]), 2)
