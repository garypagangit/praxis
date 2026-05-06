from __future__ import annotations

import argparse
from pathlib import Path

from praxis.praxis05.config import load_config
from praxis.praxis05.sae_train import train_sae_from_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Praxis 05 Phase A SAEs for configured seeds.")
    parser.add_argument("--config", default="configs/praxis05-sae-topk-k32-x16.json")
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--output-root", default="runs/praxis05-phase-a")
    parser.add_argument("--seeds", nargs="*", type=int)
    args = parser.parse_args()

    config = load_config(args.config)
    seeds = args.seeds or [int(seed) for seed in config.get("seeds", [13, 42, 137, 271, 1729])]
    for seed in seeds:
        output_dir = Path(args.output_root) / f"sae_seed_{seed}"
        print(f"Training Praxis 05 SAE seed {seed} -> {output_dir}")
        train_sae_from_cache(config, args.cache_dir, output_dir, seed)


if __name__ == "__main__":
    main()

