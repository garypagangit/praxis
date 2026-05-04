from __future__ import annotations

from praxis.praxis04.smoke import run_smoke


def test_praxis04_smoke_is_deterministic(tmp_path):
    config = {"name": "determinism", "seed": 42, "n_classes": 5, "smoke_n_samples": 300}
    first = run_smoke(config, tmp_path / "first")
    second = run_smoke(config, tmp_path / "second")
    assert first["macro_f1"] == second["macro_f1"]
    assert first["global_router_entropy_mean"] == second["global_router_entropy_mean"]
    assert first["stage_router_entropy_mean"] == second["stage_router_entropy_mean"]

