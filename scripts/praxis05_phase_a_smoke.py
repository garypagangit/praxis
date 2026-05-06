from __future__ import annotations

import argparse
from pathlib import Path

from praxis.praxis05.config import load_config
from praxis.praxis05.diagnostics import phase_a_diagnostics
from praxis.praxis05.sae_train import train_sae_from_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local Praxis 05 Phase A smoke pipeline.")
    parser.add_argument("--config", default="configs/praxis05-phase-a-smoke.json")
    parser.add_argument("--output-root", default="runs/praxis05-phase-a-smoke")
    args = parser.parse_args()

    import torch

    from praxis.praxis05.activation_cache import save_activation_cache, validate_activation_cache

    config = load_config(args.config)
    root = Path(args.output_root)
    cache_dir = root / "activations"
    generator = torch.Generator().manual_seed(13)
    basis = torch.randn(4, 8, generator=generator)
    codes = torch.randn(512, 4, generator=generator)
    activations = codes @ basis + 0.05 * torch.randn(512, 8, generator=generator)
    save_activation_cache(cache_dir, activations)
    validate_activation_cache(cache_dir)

    for seed in config["seeds"]:
        train_sae_from_cache(config, cache_dir, root / f"sae_seed_{seed}", int(seed))

    diagnostics = phase_a_diagnostics(root, config, root / "diagnostics.json")
    print(diagnostics["status"])


if __name__ == "__main__":
    main()
