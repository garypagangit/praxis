from __future__ import annotations

import torch

from praxis.praxis05.activation_cache import load_activation_tensor, save_activation_cache, validate_activation_cache
from praxis.praxis05.diagnostics import phase_a_diagnostics
from praxis.praxis05.sae_train import train_sae_from_cache


def test_activation_cache_roundtrip(tmp_path):
    activations = torch.arange(24, dtype=torch.float32).reshape(6, 4)
    manifest = save_activation_cache(tmp_path, activations)
    assert manifest["shards"][0]["rows"] == 6
    loaded = load_activation_tensor(tmp_path)
    assert torch.equal(loaded, activations)
    summary = validate_activation_cache(tmp_path)
    assert summary["valid"] is True


def test_phase_a_smoke_deterministic(tmp_path):
    generator = torch.Generator().manual_seed(13)
    basis = torch.randn(4, 8, generator=generator)
    codes = torch.randn(256, 4, generator=generator)
    activations = codes @ basis + 0.05 * torch.randn(256, 8, generator=generator)
    cache_dir = tmp_path / "cache"
    save_activation_cache(cache_dir, activations)

    config = {
        "backend": "torch_topk_smoke",
        "k": 4,
        "n_features": 32,
        "batch_size": 64,
        "learning_rate": 0.005,
        "steps": 10,
        "max_train_vectors": 256,
        "diagnostics": {
            "mse_ratio_pass_max": 2.0,
            "death_rate_pass_max": 1.0,
            "seed_stability_top_k": 10,
            "seed_stability_cosine_threshold": 0.1,
            "seed_stability_pass_min": 0.0,
        },
    }
    first = train_sae_from_cache(config, cache_dir, tmp_path / "run_a" / "sae_seed_13", seed=13)
    second = train_sae_from_cache(config, cache_dir, tmp_path / "run_b" / "sae_seed_13", seed=13)
    assert first["mse_ratio"] == second["mse_ratio"]
    assert first["feature_death_rate"] == second["feature_death_rate"]


def test_phase_a_diagnostics_kill_switch_payload(tmp_path):
    generator = torch.Generator().manual_seed(42)
    cache_dir = tmp_path / "cache"
    save_activation_cache(cache_dir, torch.randn(128, 8, generator=generator))
    config = {
        "backend": "torch_topk_smoke",
        "k": 4,
        "n_features": 16,
        "batch_size": 32,
        "learning_rate": 0.001,
        "steps": 4,
        "max_train_vectors": 128,
        "diagnostics": {
            "mse_ratio_pass_max": 10.0,
            "death_rate_pass_max": 1.0,
            "seed_stability_top_k": 5,
            "seed_stability_cosine_threshold": 0.1,
            "seed_stability_pass_min": 0.0,
        },
    }
    root = tmp_path / "phase_a"
    for seed in [13, 42]:
        train_sae_from_cache(config, cache_dir, root / f"sae_seed_{seed}", seed=seed)
    payload = phase_a_diagnostics(root, config, root / "diagnostics.json")
    assert payload["phase"] == "A"
    assert payload["status"] == "PASS"
    assert "seed_stability" in payload["checks"]

