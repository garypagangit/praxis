#!/usr/bin/env python3
"""Minimal guard tests. Run: python scripts/test_pipeline.py"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aivh import synth, features          # noqa: E402
from aivh.gate import ConformalGate, clopper_pearson_upper  # noqa: E402


def test_feature_determinism():
    s = synth.generate(n_agent=5, n_human=5, n_bot=0, seed=1)
    f1 = features.extract(s[0]); f2 = features.extract(s[0])
    assert f1 == f2, "feature extraction must be deterministic"
    assert all(np.isfinite(v) for v in f1.values()), "no NaN/inf features"
    print("ok  feature_determinism")


def test_timing_free_drops_T():
    names = features.feature_names(exclude_families=("T",))
    assert not any(n.startswith("T_") for n in names)
    assert any(n.startswith("C_") for n in names)
    print("ok  timing_free_ablation_drops_T_only")


def test_gate_coverage_guarantee():
    """On exchangeable data the gate's prediction-set coverage must be ≥ 1-alpha.
    Build a well-calibrated 2-class problem and check empirically."""
    rng = np.random.default_rng(0)
    n, alpha = 4000, 0.1
    # two gaussians, overlapping → non-trivial
    y = rng.integers(0, 2, n)
    score = rng.normal(loc=y * 1.2, scale=1.0)
    p1 = 1 / (1 + np.exp(-score))
    proba = np.column_stack([1 - p1, p1])
    classes = [0, 1]
    half = n // 2
    g = ConformalGate(alpha=alpha).calibrate(proba[:half], y[:half], classes)
    sets = g.prediction_sets(proba[half:])
    yt = y[half:]
    cov = np.mean([yt[i] in sets[i] for i in range(len(yt))])
    assert cov >= 1 - alpha - 0.03, f"set coverage {cov:.3f} < target {1-alpha}"
    print(f"ok  gate_coverage_guarantee (empirical set coverage={cov:.3f} ≥ {1-alpha})")


def test_clopper_pearson():
    assert clopper_pearson_upper(0, 100) < 0.05
    assert clopper_pearson_upper(50, 100) > 0.5
    assert clopper_pearson_upper(0, 0) == 1.0
    print("ok  clopper_pearson_upper")


def test_zenodo_turn_parser():
    """Parser must survive malformed turns without crashing."""
    from aivh.ingest import _parse_zenodo_turns
    raw = [
        [["sysprompt", "2026-01-01T00:00:00Z"], ["banner", 12.0]],
        [["out", 900.0], ["shell", 40.0], ["whoami", "whoami"]],
        "garbage turn",
        [["out", 850.0], ["shell", 30.0], ["ls -la", "ls -la"]],
    ]
    cmds = _parse_zenodo_turns(raw)
    assert [c.text for c in cmds] == ["whoami", "ls -la"]
    assert cmds[0].gap_ms is None        # first command has no gap
    assert cmds[1].gap_ms is not None
    print("ok  zenodo_turn_parser_robust")


if __name__ == "__main__":
    test_feature_determinism()
    test_timing_free_drops_T()
    test_gate_coverage_guarantee()
    test_clopper_pearson()
    test_zenodo_turn_parser()
    print("\nall tests passed")
