from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from praxis.detectors import detector_table, make_detector


def render_report(path: Path, registry: list[dict[str, Any]]) -> None:
    lines = [
        "# Detector Zoo Registry",
        "",
        "Generated: 2026-05-11",
        "",
        "## Decision",
        "",
        "Status: **ARCHITECTURE READY - DETECTOR SUITE REGISTERED**.",
        "",
        "This registry gives watermarking, membership inference, adversarial robustness, provenance drift, and stage-routing experiments a shared detector target set. It is not a model-performance claim by itself.",
        "",
        "## Registered Detectors",
        "",
        "| Detector | Family | Purpose | Probability output | Notes |",
        "|---|---|---|---|---|",
    ]
    for spec in registry:
        lines.append(
            f"| `{spec['name']}` | {spec['family']} | {spec['purpose']} | "
            f"{spec['supports_proba']} | {spec['notes']} |"
        )
    lines.extend(
        [
            "",
            "## Experiments This Opens",
            "",
            "| Experiment | How to use the zoo | Honest gate before claim |",
            "|---|---|---|",
            "| APT detector watermarking | Train source and independent non-owner detectors from the same registry | Utility loss, signature retention, and false-ownership rate must all pass |",
            "| MIA against APT detectors | Use matched target/shadow detector families | Same-distribution MIA must beat temporal-shift confounding |",
            "| Cross-detector adversarial robustness | Attack one family and test transfer to others | Need at least two stable high-quality detector families |",
            "| Concept drift | Compare detector degradation across chronological windows | Needs labels/anomaly windows and longer streams |",
            "| Stage routing on provenance graphs | Use common baselines before graph neural routing | Stage predictor must beat prior day-shift bottleneck |",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("configs/detector_zoo_registry.json"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/DETECTOR_ZOO_REGISTRY_20260511.md"),
    )
    parser.add_argument("--instantiate-check", action="store_true")
    args = parser.parse_args()

    registry = detector_table()
    if args.instantiate_check:
        for spec in registry:
            make_detector(spec["name"], random_state=20260511)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(args.report, registry)
    print(json.dumps({"registry": str(args.out), "report": str(args.report), "detectors": registry}, indent=2))


if __name__ == "__main__":
    main()
