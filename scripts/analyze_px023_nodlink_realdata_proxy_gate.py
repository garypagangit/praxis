#!/usr/bin/env python3
"""PX-023 NodLink real-data proxy gate.

This is not a full PIDSMaker/Postgres detector run. It uses the full E5 Cadets
window-feature table as the available real data source, trains the NodLink
SumAggregation reconstruction objective over a chronological window graph, then
exports 256-d activations for the existing Praxis 05 Phase A SAE diagnostics.
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from torch import nn


ROOT = Path(__file__).resolve().parents[1]
PIDSMaker = ROOT / "external" / "PIDSMaker"
WINDOW_FEATURES = ROOT / "runs" / "full-e5cadets-window-factory-20260511" / "window_features.csv"
OUT_DIR = ROOT / "runs" / "px023-nodlink-realdata-proxy-20260630"
REPORT = ROOT / "reports" / "praxis05_phase_a" / "PX023_NODLINK_REALDATA_PROXY_GATE_20260630.md"


def load_window_features(path: Path) -> tuple[torch.Tensor, list[dict[str, Any]], list[str], dict[str, Any]]:
    feature_cols: list[str] | None = None
    values: list[list[float]] = []
    metadata: list[dict[str, Any]] = []
    label_counts: dict[str, int] = {}

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if feature_cols is None:
                feature_cols = select_feature_columns(list(row.keys()))
            values.append([float(row[col]) if row[col] != "" else 0.0 for col in feature_cols])
            label = row.get("primary_label", "")
            label_counts[label] = label_counts.get(label, 0) + 1
            metadata.append(
                {
                    "source": "full-e5cadets-window-factory-20260511",
                    "window_id": int(row["window_id"]),
                    "primary_label": label,
                    "rows": int(float(row["rows"])),
                    "span_seconds": float(row["span_seconds"]),
                    "malicious_node_events": int(float(row.get("malicious_node_events", "0") or 0)),
                    "malicious_node_count": int(float(row.get("malicious_node_count", "0") or 0)),
                }
            )

    if feature_cols is None:
        raise ValueError(f"No rows found in {path}")
    x = torch.tensor(values, dtype=torch.float32)
    mean = x.mean(dim=0, keepdim=True)
    std = x.std(dim=0, keepdim=True).clamp_min(1e-6)
    x = (x - mean) / std
    summary = {
        "rows": int(x.shape[0]),
        "feature_dim": int(x.shape[1]),
        "feature_columns": feature_cols,
        "label_counts": label_counts,
        "excluded_label_leakage_columns": [
            "window_id",
            "start_ns",
            "end_ns",
            "primary_label",
            "labels",
            "label_overlap_ns",
            "malicious_node_events",
            "malicious_node_count",
            "node_labels",
        ],
    }
    return x, metadata, feature_cols, summary


def select_feature_columns(columns: list[str]) -> list[str]:
    base = [
        "rows",
        "span_seconds",
        "source_files",
        "distinct_subjects",
        "distinct_objects",
        "distinct_execs",
        "distinct_event_types",
    ]
    prefix_cols = [col for col in columns if col.startswith("event__") or col.startswith("exec__")]
    selected = [col for col in base if col in columns] + prefix_cols
    if not selected:
        raise ValueError("No usable feature columns found")
    return selected


def chronological_edge_index(node_count: int) -> torch.Tensor:
    edges: list[tuple[int, int]] = [(idx, idx) for idx in range(node_count)]
    for idx in range(node_count - 1):
        edges.append((idx, idx + 1))
        edges.append((idx + 1, idx))
    return torch.tensor(edges, dtype=torch.long).t().contiguous()


class NodLinkProxy(nn.Module):
    def __init__(self, in_dim: int, hidden_dim: int = 256, out_dim: int = 256):
        super().__init__()
        sys.path.insert(0, str(PIDSMaker))
        from pidsmaker.encoders.sum_aggregation import SumAggregation

        self.encoder = SumAggregation(in_dim=in_dim, hid_dim=hidden_dim, out_dim=out_dim)
        self.decoder = nn.Linear(out_dim, in_dim)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.encoder(x, edge_index)["h"]
        return self.decoder(h), h


def train_nodlink_proxy(x: torch.Tensor, edge_index: torch.Tensor, seed: int = 13) -> dict[str, Any]:
    torch.manual_seed(seed)
    started = time.time()
    model = NodLinkProxy(in_dim=int(x.shape[1]))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003, weight_decay=1e-5)
    epochs = 300
    losses: list[float] = []
    baseline_mse = float(torch.mean((x - x.mean(dim=0, keepdim=True)) ** 2).item())
    best_loss = math.inf
    best_state: dict[str, torch.Tensor] | None = None

    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        recon, _ = model(x, edge_index)
        loss = torch.mean((recon - x) ** 2)
        loss.backward()
        optimizer.step()
        loss_value = float(loss.detach().cpu().item())
        losses.append(loss_value)
        if loss_value < best_loss:
            best_loss = loss_value
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    with torch.no_grad():
        recon, activations = model(x, edge_index)
        reconstruction_mse = float(torch.mean((recon - x) ** 2).item())
        activation_std = float(activations.std().item())
        activation_nonzero = float((activations.abs() > 1e-8).float().mean().item())

    model_dir = OUT_DIR / "nodlink_proxy_model"
    model_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), model_dir / "weights.pt")
    torch.save({"seed": seed, "epochs": epochs, "losses": losses}, model_dir / "training_trace.pt")

    return {
        "seed": seed,
        "epochs": epochs,
        "learning_rate": 0.003,
        "weight_decay": 1e-5,
        "baseline_mse": baseline_mse,
        "reconstruction_mse": reconstruction_mse,
        "mse_ratio": reconstruction_mse / max(baseline_mse, 1e-12),
        "activation_shape": [int(activations.shape[0]), int(activations.shape[1])],
        "activation_std": activation_std,
        "activation_nonzero_fraction": activation_nonzero,
        "elapsed_seconds": time.time() - started,
        "activations": activations.detach().cpu().float(),
    }


def run_sae_diagnostics(cache_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    sys.path.insert(0, str(ROOT / "src"))
    from praxis.praxis05.diagnostics import phase_a_diagnostics
    from praxis.praxis05.sae_train import train_sae_from_cache

    phase_root = OUT_DIR / "saelens_phase_a_pilot"
    config = {
        "name": "px023-nodlink-realdata-saelens-pilot",
        "backend": "saelens",
        "saelens_version": "6.43.0",
        "sae_type": "topk",
        "k": 32,
        "n_features": 1024,
        "batch_size": 1024,
        "learning_rate": 0.0003,
        "steps": 1000,
        "max_train_vectors": 20000,
        "device": "cpu",
        "research_backend": True,
        "pilot_only": True,
        "seeds": [13, 42, 137, 271, 1729],
        "diagnostics": {
            "mse_ratio_pass_max": 0.25,
            "death_rate_pass_max": 0.5,
            "seed_stability_top_k": 100,
            "seed_stability_cosine_threshold": 0.8,
            "seed_stability_pass_min": 0.3,
        },
    }
    metrics = []
    for seed in config["seeds"]:
        metrics.append(train_sae_from_cache(config, cache_dir, phase_root / f"sae_seed_{seed}", seed))
    diagnostics = phase_a_diagnostics(phase_root, config, phase_root / "diagnostics.json")
    (phase_root / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return diagnostics, metrics


def write_report(analysis: dict[str, Any]) -> None:
    diagnostics = analysis["sae_diagnostics"]
    checks = diagnostics["checks"]
    status = analysis["status"]
    lines = [
        "# PX-023 NodLink Real-Data Proxy Gate",
        "",
        f"Generated: {analysis['generated_utc']}",
        "",
        f"Status: **{status}**",
        "",
        "## Claim Boundary",
        "",
        "This gate uses real full E5 Cadets window features and PIDSMaker's NodLink `SumAggregation` encoder, but it is not a full PIDSMaker detector run. The full PIDSMaker path still requires a Postgres graph database/runtime that is not present on the AWS data-loader.",
        "",
        "The result can close or constrain the one allowed PX-023 pivot, but it must not be described as a full NodLink/PIDSMaker detection result.",
        "",
        "## Runtime Readiness",
        "",
        "- AWS data-loader has the raw E5 Cadets mirror: `49` gzipped Cadets files under `/mnt/praxis/datasets/darpa-tc/e5/cadets`.",
        "- AWS data-loader is missing Docker and native Postgres/psql for a full PIDSMaker database-backed run.",
        "- Local repo venv has Torch, PyG, and SAELens, so the real-data proxy was run locally without restarting the GPU instance.",
        "",
        "## Real-Data Proxy Input",
        "",
        f"- Source table: `{analysis['input']['source']}`.",
        f"- Rows: `{analysis['input']['rows']}` windows.",
        f"- Feature dimensions: `{analysis['input']['feature_dim']}` non-label aggregate features.",
        f"- Class support: `{analysis['input']['label_counts']}`.",
        "- Label-derived columns were excluded from the reconstruction input.",
        "",
        "## NodLink-Style Activation Export",
        "",
        f"- Encoder: `pidsmaker.encoders.sum_aggregation.SumAggregation`.",
        f"- Graph: chronological bidirectional window graph with self loops, `{analysis['graph']['edge_count']}` edges.",
        f"- Reconstruction MSE ratio: `{analysis['nodlink_proxy']['mse_ratio']:.6f}`.",
        f"- Activation shape: `{analysis['nodlink_proxy']['activation_shape'][0]}` x `{analysis['nodlink_proxy']['activation_shape'][1]}`.",
        f"- Activation std: `{analysis['nodlink_proxy']['activation_std']:.6f}`.",
        f"- Nonzero activation fraction: `{analysis['nodlink_proxy']['activation_nonzero_fraction']:.6f}`.",
        "",
        "## SAE Phase A Pilot Diagnostics",
        "",
        "SAELens TopK pilot config: `1024` features, `k=32`, `1000` CPU steps, five seeds. Thresholds are the same Phase A kill-switch thresholds, but the run is a pilot, not the frozen `4096` feature / `20000` step GPU sweep.",
        "",
        "| Check | Value | Threshold | Pass? |",
        "|---|---:|---:|---|",
    ]
    for name, item in checks.items():
        lines.append(
            f"| {name} | `{float(item['value']):.6f}` | `{float(item['threshold']):.4f}` | {'yes' if item['pass'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            analysis["decision"],
            "",
            "## Artifacts",
            "",
            f"- Raw analysis JSON: `{(OUT_DIR / 'px023_nodlink_realdata_proxy_gate.json').relative_to(ROOT).as_posix()}`",
            f"- Activation cache: `{(OUT_DIR / 'nodlink_realdata_activation_cache').relative_to(ROOT).as_posix()}/`",
            f"- NodLink proxy model: `{(OUT_DIR / 'nodlink_proxy_model').relative_to(ROOT).as_posix()}/`",
            f"- SAELens pilot diagnostics: `{(OUT_DIR / 'saelens_phase_a_pilot' / 'diagnostics.json').relative_to(ROOT).as_posix()}`",
            "",
        ]
    )
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(ROOT / "src"))
    from praxis.praxis05.activation_cache import save_activation_cache, validate_activation_cache
    from praxis.praxis05.config import write_json

    x, metadata, feature_cols, input_summary = load_window_features(WINDOW_FEATURES)
    edge_index = chronological_edge_index(int(x.shape[0]))
    nodlink = train_nodlink_proxy(x, edge_index, seed=13)
    activations = nodlink.pop("activations")
    cache_dir = OUT_DIR / "nodlink_realdata_activation_cache"
    manifest = save_activation_cache(cache_dir, activations, metadata=metadata)
    cache_validation = validate_activation_cache(cache_dir)
    diagnostics, sae_metrics = run_sae_diagnostics(cache_dir)

    if diagnostics["status"] == "PASS":
        status = "REAL-DATA PROXY PASS - FULL PIDSMaker STILL BLOCKED"
        decision = (
            "Keep PX-023 constrained: the real-data proxy clears the pilot SAE diagnostics, "
            "but a full PIDSMaker/Postgres NodLink detector run is still required before any positive SAE claim."
        )
    else:
        status = "REAL-DATA PROXY FAIL - CLOSE PIVOT"
        failed = [name for name, item in diagnostics["checks"].items() if not item["pass"]]
        decision = (
            "Close PX-023 as negative for this cycle. The available real-data NodLink-style pivot fails "
            f"the Phase A pilot diagnostics on {', '.join(failed)}, while the full PIDSMaker runtime remains "
            "database-blocked. Do not reopen MAGIC or spend on Phase B."
        )

    analysis = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "claim_boundary": "Real Cadets window data and NodLink-style encoder; not a full PIDSMaker/Postgres detector run.",
        "input": {
            "source": str(WINDOW_FEATURES.relative_to(ROOT)),
            **input_summary,
        },
        "graph": {
            "construction": "chronological_bidirectional_with_self_loops",
            "edge_count": int(edge_index.shape[1]),
        },
        "nodlink_proxy": nodlink,
        "activation_cache_manifest": manifest,
        "activation_cache_validation": cache_validation,
        "sae_metrics": sae_metrics,
        "sae_diagnostics": diagnostics,
        "decision": decision,
    }
    write_json(OUT_DIR / "px023_nodlink_realdata_proxy_gate.json", analysis)
    write_report(analysis)
    print(json.dumps({"status": status, "diagnostics": diagnostics["checks"]}, indent=2))


if __name__ == "__main__":
    main()
