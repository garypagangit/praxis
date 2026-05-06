from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from praxis.praxis05.config import write_json
from praxis.praxis05.feature_analysis.seed_stability import pairwise_top_feature_stability


def phase_a_diagnostics(phase_a_root: str | Path, config: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    root = Path(phase_a_root)
    run_dirs = sorted(path for path in root.glob("sae_seed_*") if (path / "metrics.json").exists())
    if not run_dirs:
        raise ValueError(f"No sae_seed_* metrics found under {root}")

    metrics = [json.loads((path / "metrics.json").read_text(encoding="utf-8")) for path in run_dirs]
    diagnostic_config = config.get("diagnostics", {})
    mse_ratio_max = float(diagnostic_config.get("mse_ratio_pass_max", 0.25))
    death_rate_max = float(diagnostic_config.get("death_rate_pass_max", 0.5))
    stability_min = float(diagnostic_config.get("seed_stability_pass_min", 0.3))
    top_k = int(diagnostic_config.get("seed_stability_top_k", 100))
    cosine_threshold = float(diagnostic_config.get("seed_stability_cosine_threshold", 0.8))

    mean_mse_ratio = sum(float(item["mse_ratio"]) for item in metrics) / len(metrics)
    mean_death_rate = sum(float(item["feature_death_rate"]) for item in metrics) / len(metrics)
    stability = pairwise_top_feature_stability(run_dirs, top_k=top_k, cosine_threshold=cosine_threshold)
    mean_stability = float(stability["mean_pairwise_overlap"])

    checks = {
        "mse_ratio": {"value": mean_mse_ratio, "pass": mean_mse_ratio < mse_ratio_max, "threshold": mse_ratio_max},
        "feature_death_rate": {"value": mean_death_rate, "pass": mean_death_rate < death_rate_max, "threshold": death_rate_max},
        "seed_stability": {"value": mean_stability, "pass": mean_stability > stability_min, "threshold": stability_min},
    }
    passed = all(item["pass"] for item in checks.values())
    payload = {
        "phase": "A",
        "status": "PASS" if passed else "FAIL",
        "kill_switch_enforced": not passed,
        "run_count": len(run_dirs),
        "runs": [str(path) for path in run_dirs],
        "checks": checks,
        "stability": stability,
        "metrics": metrics,
        "next_step": "Ask before implementing Phase B." if passed else "Do not proceed to Phase B. Write the negative-result note or run the single allowed PIDSMaker pivot.",
    }
    write_json(output_path, payload)
    return payload

