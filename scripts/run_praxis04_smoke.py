from __future__ import annotations

import argparse
import json
from pathlib import Path

from praxis.praxis04.smoke import run_smoke


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic Praxis 04 smoke experiment.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if args.seed is not None:
        config["seed"] = int(args.seed)
    output_dir = Path(args.output_dir) if args.output_dir else Path("runs") / f"{config['name']}_seed{config['seed']}"
    result = run_smoke(config, output_dir)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
