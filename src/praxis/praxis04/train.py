from __future__ import annotations

import argparse
import json
from pathlib import Path

from praxis.praxis04.experiment import run_experiment
from praxis.praxis04.smoke import run_smoke


def main() -> None:
    parser = argparse.ArgumentParser(description="Praxis 04 experiment entrypoint.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--smoke", action="store_true", help="Run the deterministic synthetic harness.")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    if args.seed is not None:
        config["seed"] = int(args.seed)

    output_dir = Path(args.output_dir) if args.output_dir else Path("runs") / f"{config['name']}_seed{config['seed']}"
    if args.smoke:
        print(json.dumps(run_smoke(config, output_dir), indent=2))
        return

    print(json.dumps(run_experiment(config, output_dir), indent=2))


if __name__ == "__main__":
    main()
