from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def edge_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    for col in ["subject_uuid", "object_uuid", "object2_uuid"]:
        if col not in frame:
            frame[col] = None
    return frame


def graph_stats(frame: pd.DataFrame) -> dict[str, Any]:
    subjects = frame["subject_uuid"].dropna().astype(str)
    objects = frame["object_uuid"].dropna().astype(str)
    object2 = frame["object2_uuid"].dropna().astype(str)
    nodes = pd.concat([subjects, objects, object2], ignore_index=True)
    timestamps = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    event_counts = Counter(frame["datum_type"].fillna("None").astype(str))
    source_counts = Counter(frame["source_file"].fillna("unknown").astype(str))
    return {
        "edge_count": int(len(frame)),
        "node_count": int(nodes.nunique()),
        "subject_count": int(subjects.nunique()),
        "object_count": int(objects.nunique()),
        "object2_count": int(object2.nunique()),
        "missing_subject_edges": int(frame["subject_uuid"].isna().sum()),
        "missing_object_edges": int(frame["object_uuid"].isna().sum()),
        "timestamp_missing": int(timestamps.isna().sum()),
        "timestamp_min": int(timestamps.min()) if timestamps.notna().any() else None,
        "timestamp_max": int(timestamps.max()) if timestamps.notna().any() else None,
        "timestamp_monotonic_by_record_order": bool(
            timestamps.dropna().is_monotonic_increasing
        ),
        "event_type_counts_top20": dict(event_counts.most_common(20)),
        "source_file_counts": dict(source_counts.most_common()),
    }


def drop_edges(
    frame: pd.DataFrame, drop_rate: float, rng: np.random.Generator
) -> pd.DataFrame:
    keep = rng.random(len(frame)) >= drop_rate
    return frame.loc[keep].reset_index(drop=True)


def mask_nodes(
    frame: pd.DataFrame, mask_rate: float, rng: np.random.Generator
) -> pd.DataFrame:
    out = frame.copy()
    nodes = pd.concat(
        [
            out["subject_uuid"].dropna().astype(str),
            out["object_uuid"].dropna().astype(str),
            out["object2_uuid"].dropna().astype(str),
        ],
        ignore_index=True,
    ).unique()
    mask_count = int(round(mask_rate * len(nodes)))
    if mask_count == 0:
        return out
    masked = set(rng.choice(nodes, size=mask_count, replace=False).tolist())
    for col in ["subject_uuid", "object_uuid", "object2_uuid"]:
        out[col] = out[col].map(
            lambda value: "[MASKED_NODE]" if str(value) in masked else value
        )
    return out


def temporal_subgraph(
    frame: pd.DataFrame, quantile_start: float, quantile_stop: float
) -> pd.DataFrame:
    timestamps = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    lo = timestamps.quantile(quantile_start)
    hi = timestamps.quantile(quantile_stop)
    return frame.loc[(timestamps >= lo) & (timestamps <= hi)].reset_index(drop=True)


def compare_augmented(
    base: dict[str, Any], augmented: dict[str, Any]
) -> dict[str, Any]:
    return {
        "edge_retention": augmented["edge_count"] / max(base["edge_count"], 1),
        "node_retention": augmented["node_count"] / max(base["node_count"], 1),
        "timestamp_monotonic": augmented["timestamp_monotonic_by_record_order"],
        "has_event_diversity": len(augmented["event_type_counts_top20"]) >= 5,
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets Graph Augmentation Gate",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Base Graph Sample",
        "",
        f"- Edges: `{summary['base_stats']['edge_count']}`",
        f"- Nodes: `{summary['base_stats']['node_count']}`",
        f"- Timestamp monotonic by record order: `{summary['base_stats']['timestamp_monotonic_by_record_order']}`",
        f"- Missing subject edges: `{summary['base_stats']['missing_subject_edges']}`",
        f"- Missing object edges: `{summary['base_stats']['missing_object_edges']}`",
        "",
        "## Augmentation Checks",
        "",
        "| Augmentation | Edge retention | Node retention | Event diversity | Timestamp monotonic |",
        "|---|---:|---:|---|---|",
    ]
    for name, row in summary["augmentation_checks"].items():
        lines.append(
            f"| `{name}` | `{row['edge_retention']:.4f}` | `{row['node_retention']:.4f}` | `{row['has_event_diversity']}` | `{row['timestamp_monotonic']}` |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            summary["recommendation"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir", type=Path, default=Path("tmp") / "cadets_edge_sample"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "cadets-graph-augmentation-gate-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "contrastive_ssl_provenance_graphs"
        / "CADETS_GRAPH_AUGMENTATION_GATE_20260509.md",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    rows = read_jsonl(args.input_dir / "edges.jsonl", args.limit)
    frame = edge_frame(rows)
    rng = np.random.default_rng(args.seed)
    base = graph_stats(frame)
    augmentations = {
        "edge_drop_10pct": graph_stats(drop_edges(frame, 0.10, rng)),
        "edge_drop_30pct": graph_stats(drop_edges(frame, 0.30, rng)),
        "node_mask_10pct": graph_stats(mask_nodes(frame, 0.10, rng)),
        "temporal_middle_50pct": graph_stats(temporal_subgraph(frame, 0.25, 0.75)),
    }
    checks = {
        name: compare_augmented(base, stats) for name, stats in augmentations.items()
    }
    pass_gate = (
        base["edge_count"] >= 50000
        and base["node_count"] >= 100
        and base["timestamp_missing"] == 0
        and all(row["edge_retention"] > 0.40 for row in checks.values())
        and all(row["has_event_diversity"] for row in checks.values())
    )
    summary = {
        "decision": (
            "PASS - SSL AUGMENTATION SCAFFOLD READY"
            if pass_gate
            else "BLOCKED - AUGMENTATION INPUT ISSUE"
        ),
        "input_dir": str(args.input_dir),
        "base_stats": base,
        "augmentation_stats": augmentations,
        "augmentation_checks": checks,
        "recommendation": (
            "Proceed to a small GraphCL/BGRL-style representation pilot on the Cadets edge sample. Keep it unsupervised until a label/window manifest is added."
            if pass_gate
            else "Do not train yet; inspect missing timestamps, node identifiers, or event diversity before building an SSL objective."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(
        json.dumps(
            {"decision": summary["decision"], "base": base, "checks": checks}, indent=2
        )
    )


if __name__ == "__main__":
    main()
