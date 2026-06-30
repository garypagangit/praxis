#!/usr/bin/env python3
"""PX-023 PIDSMaker larger-hidden-state pivot gate."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
PIDSMaker = ROOT / "external" / "PIDSMaker"
OUT_DIR = ROOT / "runs" / "px023-pidsmaker-pivot-gate-20260630"
REPORT = ROOT / "reports" / "praxis05_phase_a" / "PX023_PIDSMaker_PIVOT_GATE_20260630.md"
PHASE_A_DIAGNOSTICS = ROOT / "runs" / "praxis05-phase-a-full-magic-aws-20260510" / "diagnostics.json"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def candidate_matrix() -> list[dict[str, Any]]:
    rows = []
    for system in ["magic", "orthrus", "nodlink", "rcaid", "kairos"]:
        cfg = read_yaml(PIDSMaker / "config" / f"{system}.yml")
        training = cfg["training"]
        encoder = training["encoder"]
        node_hid_dim = int(training["node_hid_dim"])
        node_out_dim = int(training["node_out_dim"])
        used_methods = str(encoder["used_methods"])
        if system == "magic":
            decision = "failed_predecessor"
            reason = "Original full Phase A already failed feature-death and stability gates on 64-d MAGIC CADETS activations."
        elif system == "nodlink":
            decision = "preferred_direct_pivot"
            reason = "Direct encoder output is 256-d, matching the larger-hidden-state pivot without an output bottleneck."
        elif system == "orthrus":
            decision = "hook_only_secondary"
            reason = "Configured direct output is 64-d; 128-d signal exists only inside graph-attention/TGN internals."
        elif system == "rcaid":
            decision = "reject_output_bottleneck"
            reason = "Configured encoder output is 3-d for node-type prediction, not a useful SAE activation target."
        else:
            decision = "secondary_tgn_candidate"
            reason = "Direct output is 100-d and depends on TGN queue-style machinery; less clean than NodLink."
        rows.append(
            {
                "system": system,
                "node_hid_dim": node_hid_dim,
                "node_out_dim": node_out_dim,
                "encoder_methods": used_methods,
                "featurization_dim": int(cfg.get("featurization", {}).get("emb_dim", 0)),
                "decoder_methods": str(training["decoder"]["used_methods"]),
                "direct_output_ge_128": node_out_dim >= 128,
                "decision": decision,
                "reason": reason,
            }
        )
    return rows


def write_candidate_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "system",
        "node_hid_dim",
        "node_out_dim",
        "encoder_methods",
        "featurization_dim",
        "decoder_methods",
        "direct_output_ge_128",
        "decision",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def run_nodlink_smoke() -> dict[str, Any]:
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(PIDSMaker))

    import torch
    from pidsmaker.encoders.sum_aggregation import SumAggregation
    from praxis.praxis05.activation_cache import save_activation_cache, validate_activation_cache
    from praxis.praxis05.sae_train import train_sae_from_cache

    torch.manual_seed(20260630)
    cache_dir = OUT_DIR / "nodlink_synthetic_activation_cache"
    sae_root = OUT_DIR / "nodlink_tiny_sae_smoke"
    node_count = 512
    feature_dim = 256
    hidden_dim = 256
    out_dim = 256

    model = SumAggregation(in_dim=feature_dim, hid_dim=hidden_dim, out_dim=out_dim)
    model.eval()
    x = torch.randn(node_count, feature_dim)
    src = torch.arange(0, node_count - 1, dtype=torch.long)
    dst = torch.arange(1, node_count, dtype=torch.long)
    edge_index = torch.stack([torch.cat([src, dst]), torch.cat([dst, src])], dim=0)
    with torch.no_grad():
        activations = model(x, edge_index)["h"].float()

    metadata = [
        {"system": "nodlink", "source": "synthetic-smoke", "node_index": int(index)}
        for index in range(node_count)
    ]
    manifest = save_activation_cache(cache_dir, activations, metadata=metadata)
    cache_validation = validate_activation_cache(cache_dir)

    smoke_config = {
        "name": "px023-nodlink-256d-tiny-sae-smoke",
        "backend": "torch_topk_smoke",
        "sae_type": "topk",
        "k": 16,
        "n_features": 512,
        "batch_size": 64,
        "learning_rate": 0.003,
        "steps": 40,
        "max_train_vectors": 512,
        "research_backend": False,
    }
    metrics = []
    for seed in [13, 42]:
        metrics.append(train_sae_from_cache(smoke_config, cache_dir, sae_root / f"sae_seed_{seed}", seed))

    return {
        "system": "nodlink",
        "smoke_type": "synthetic_encoder_export_plus_tiny_topk_sae",
        "claim_boundary": "Synthetic smoke only; not evidence that PIDSMaker real detector activations are interpretable.",
        "encoder": "pidsmaker.encoders.sum_aggregation.SumAggregation",
        "activation_shape": list(activations.shape),
        "activation_cache": str(cache_dir.relative_to(ROOT)),
        "sae_smoke_root": str(sae_root.relative_to(ROOT)),
        "manifest": manifest,
        "cache_validation": cache_validation,
        "tiny_sae_metrics": metrics,
        "mean_tiny_sae_mse_ratio": sum(float(item["mse_ratio"]) for item in metrics) / len(metrics),
        "mean_tiny_sae_feature_death_rate": sum(float(item["feature_death_rate"]) for item in metrics) / len(metrics),
    }


def fmt(value: Any, digits: int = 4) -> str:
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def write_report(analysis: dict[str, Any], csv_path: Path, json_path: Path) -> None:
    phase_a = analysis["magic_phase_a"]
    checks = phase_a["checks"]
    smoke = analysis["nodlink_smoke"]
    rows = analysis["candidate_matrix"]
    lines = [
        "# PX-023 PIDSMaker Larger-Hidden-State Pivot Gate",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        "Status: **PIVOT SCAFFOLD PASS - NO POSITIVE SAE RESULT YET**",
        "",
        "## Claim Boundary",
        "",
        "MAGIC/CADETS Phase A remains a failed SAE interpretability result. This gate only tests whether the one allowed larger-hidden-state PIDSMaker pivot has a mechanically credible activation-export path before spending GPU time on a real detector run.",
        "",
        "The NodLink smoke below uses synthetic graph features and an untrained encoder. It proves interface compatibility only; it is not evidence that real PIDSMaker activations are interpretable.",
        "",
        "## Prior MAGIC Phase A Result",
        "",
        "| Check | Value | Threshold | Pass? |",
        "|---|---:|---:|---|",
    ]
    for name, item in checks.items():
        lines.append(f"| {name} | `{fmt(item['value'], 6)}` | `{fmt(item['threshold'], 4)}` | {'yes' if item['pass'] else 'no'} |")

    lines.extend(
        [
            "",
            "## PIDSMaker Candidate Matrix",
            "",
            "| System | Encoder methods | Node hidden | Node output | Decision |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['system']} | `{row['encoder_methods']}` | `{row['node_hid_dim']}` | `{row['node_out_dim']}` | {row['decision']} |"
        )

    lines.extend(
        [
            "",
            "NodLink is the only clean direct pivot in the checked configs: it exposes a 256-dimensional encoder output without a small classifier bottleneck. Orthrus and Kairos remain secondary hook/TGN candidates; R-Caid's configured 3-dimensional output is rejected for this SAE use.",
            "",
            "## NodLink Smoke",
            "",
            f"- Activation export: `{smoke['activation_shape'][0]}` rows x `{smoke['activation_shape'][1]}` dimensions.",
            f"- Cache validation: valid=`{smoke['cache_validation']['valid']}`, std=`{fmt(smoke['cache_validation']['std'])}`, nonzero fraction=`{fmt(smoke['cache_validation']['nonzero_fraction'])}`.",
            f"- Tiny non-research TopK SAE smoke: mean MSE ratio `{fmt(smoke['mean_tiny_sae_mse_ratio'])}`, mean feature-death rate `{fmt(smoke['mean_tiny_sae_feature_death_rate'])}` across two seeds.",
            "",
            "## Decision",
            "",
            "Do not reopen MAGIC or proceed to Phase B. Keep PX-023 as a single active pivot gate only if the next step is a real NodLink activation export followed by the frozen Phase A SAE diagnostics. If that real NodLink export fails feature death or stability, close PX-023 as a negative result for provenance-graph detector hidden-state SAEs.",
            "",
            "## Artifacts",
            "",
            f"- Raw JSON: `{json_path.relative_to(ROOT).as_posix()}`",
            f"- Candidate matrix CSV: `{csv_path.relative_to(ROOT).as_posix()}`",
            f"- Synthetic activation cache and tiny SAE smoke: `{OUT_DIR.relative_to(ROOT).as_posix()}/`",
            "- Prior MAGIC evidence: `reports/praxis05_phase_a/FULL_GPU_PHASE_A_20260510.md` and `runs/praxis05-phase-a-full-magic-aws-20260510/diagnostics.json`",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = candidate_matrix()
    csv_path = OUT_DIR / "candidate_matrix.csv"
    write_candidate_csv(csv_path, rows)
    smoke = run_nodlink_smoke()
    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PIVOT SCAFFOLD PASS - NO POSITIVE SAE RESULT YET",
        "magic_phase_a": read_json(PHASE_A_DIAGNOSTICS),
        "candidate_matrix": rows,
        "nodlink_smoke": smoke,
        "next_real_gate": "Run real NodLink activation export, then frozen Phase A SAE diagnostics. Do not relax MAGIC gates.",
    }
    json_path = OUT_DIR / "px023_pidsmaker_pivot_gate.json"
    json_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_report(analysis, csv_path, json_path)
    print(json.dumps({"status": analysis["status"], "nodlink_cache": smoke["cache_validation"]}, indent=2))


if __name__ == "__main__":
    main()
