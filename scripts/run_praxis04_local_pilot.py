from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from praxis.praxis04.experiment import run_experiment


MODELS = [
    ("praxis04-pilot-baseline-single", "Baseline-Single", ["RF"], ["features"]),
    ("praxis04-pilot-baseline-tse", "Baseline-TSE", ["RF", "MLP", "BiLSTM"], ["features"]),
    ("praxis04-pilot-treatment-stage", "Treatment-Stage", ["RF", "MLP", "BiLSTM"], ["features", "predicted_stage_logits"]),
    ("praxis04-pilot-ablation-nostage", "Ablation-NoStage", ["RF", "MLP", "BiLSTM"], ["features", "random_stage_noise"]),
    ("praxis04-pilot-ablation-oraclestage", "Ablation-OracleStage", ["RF", "MLP", "BiLSTM"], ["features", "ground_truth_stage_onehot"]),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Praxis 04 local pilot sweep.")
    parser.add_argument("--base-config", default="configs/praxis04-local-pilot.json")
    parser.add_argument("--output-root", default="runs")
    args = parser.parse_args()

    base = json.loads(Path(args.base_config).read_text(encoding="utf-8"))
    for name, model, submodels, router_input in MODELS:
        for seed in base["seeds"]:
            config = deepcopy(base)
            config.update(
                {
                    "name": name,
                    "model": model,
                    "submodels": submodels,
                    "router_input": router_input,
                    "seed": int(seed),
                }
            )
            output_dir = Path(args.output_root) / f"{name}_seed{seed}"
            print(f"Running {name} seed {seed}")
            run_experiment(config, output_dir)


if __name__ == "__main__":
    main()

