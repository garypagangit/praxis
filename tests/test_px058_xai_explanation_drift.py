import numpy as np

from scripts.run_px058_xai_explanation_drift import (
    jaccard,
    feature_mean_drift,
    mean_pairwise_jaccard,
    rank_spearman,
    safe_spearman,
    top_k_set,
)


def test_top_k_uses_absolute_importance():
    assert top_k_set(np.array([-9.0, 2.0, 1.0]), ["a", "b", "c"], 2) == {"a", "b"}


def test_jaccard_and_pairwise_stability():
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3
    assert mean_pairwise_jaccard([{"a", "b"}, {"a", "b"}]) == 1.0


def test_rank_spearman_is_sign_invariant():
    assert rank_spearman(np.array([3.0, -2.0, 1.0]), np.array([-3.0, 2.0, -1.0])) == 1.0


def test_safe_spearman_requires_replication():
    assert safe_spearman([0.0, 1.0], [0.0, 1.0]) == 0.0
    assert safe_spearman([0.0, 0.5, 1.0], [0.1, 0.2, 0.9]) > 0.9


def test_feature_mean_drift_is_zero_for_identical_data():
    values = np.array([[0.0, 1.0], [2.0, 3.0]])
    assert feature_mean_drift(values, values.copy()) == 0.0
