from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_node_features(
    rows: list[dict[str, Any]], event_vocab: list[str]
) -> tuple[list[str], np.ndarray]:
    index = {event: idx for idx, event in enumerate(event_vocab)}
    feats: dict[str, np.ndarray] = defaultdict(
        lambda: np.zeros(len(event_vocab) * 3, dtype=np.float32)
    )
    for row in rows:
        event = str(row.get("datum_type"))
        event_idx = index.get(event)
        if event_idx is None:
            continue
        subject = row.get("subject_uuid")
        obj = row.get("object_uuid")
        obj2 = row.get("object2_uuid")
        if subject:
            feats[str(subject)][event_idx] += 1
        if obj:
            feats[str(obj)][len(event_vocab) + event_idx] += 1
        if obj2:
            feats[str(obj2)][2 * len(event_vocab) + event_idx] += 1
    nodes = sorted(feats)
    mat = (
        np.vstack([np.log1p(feats[node]) for node in nodes])
        if nodes
        else np.zeros((0, len(event_vocab) * 3))
    )
    norm = np.linalg.norm(mat, axis=1, keepdims=True)
    mat = mat / np.clip(norm, 1e-12, None)
    return nodes, mat


def edge_drop(
    rows: list[dict[str, Any]], keep_rate: float, rng: np.random.Generator
) -> list[dict[str, Any]]:
    mask = rng.random(len(rows)) < keep_rate
    return [row for row, keep in zip(rows, mask) if keep]


def compare_views(
    nodes_a: list[str],
    mat_a: np.ndarray,
    nodes_b: list[str],
    mat_b: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    common = sorted(set(nodes_a).intersection(nodes_b))
    pos_a = {node: idx for idx, node in enumerate(nodes_a)}
    pos_b = {node: idx for idx, node in enumerate(nodes_b)}
    if len(common) < 2:
        raise ValueError("Not enough common nodes between augmented views.")
    a = np.vstack([mat_a[pos_a[node]] for node in common])
    b = np.vstack([mat_b[pos_b[node]] for node in common])
    positive = np.sum(a * b, axis=1)
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(len(common))
    negative = np.sum(a * b[shuffled], axis=1)
    return {
        "common_nodes": int(len(common)),
        "positive_cosine_mean": float(np.mean(positive)),
        "negative_cosine_mean": float(np.mean(negative)),
        "positive_minus_negative": float(np.mean(positive) - np.mean(negative)),
        "positive_gt_negative_rate": float(np.mean(positive > negative)),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets SSL Representation Pilot",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## View Agreement",
        "",
        f"- Common nodes: `{summary['view_agreement']['common_nodes']}`",
        f"- Positive cosine mean: `{summary['view_agreement']['positive_cosine_mean']:.4f}`",
        f"- Negative cosine mean: `{summary['view_agreement']['negative_cosine_mean']:.4f}`",
        f"- Positive minus negative: `{summary['view_agreement']['positive_minus_negative']:.4f}`",
        f"- Positive > negative rate: `{summary['view_agreement']['positive_gt_negative_rate']:.4f}`",
        "",
        "## Recommendation",
        "",
        summary["recommendation"],
    ]
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
        default=Path("runs") / "cadets-ssl-representation-pilot-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "contrastive_ssl_provenance_graphs"
        / "CADETS_SSL_REPRESENTATION_PILOT_20260509.md",
    )
    parser.add_argument("--seed", type=int, default=20260509)
    args = parser.parse_args()

    rows = read_jsonl(args.input_dir / "edges.jsonl")
    event_counts = Counter(str(row.get("datum_type")) for row in rows)
    event_vocab = [name for name, _ in event_counts.most_common(32)]
    rng = np.random.default_rng(args.seed)
    view_a = edge_drop(rows, 0.90, rng)
    view_b = edge_drop(rows, 0.90, rng)
    nodes_a, mat_a = build_node_features(view_a, event_vocab)
    nodes_b, mat_b = build_node_features(view_b, event_vocab)
    agreement = compare_views(nodes_a, mat_a, nodes_b, mat_b, args.seed)
    pass_gate = (
        agreement["common_nodes"] >= 1000
        and agreement["positive_minus_negative"] >= 0.20
        and agreement["positive_gt_negative_rate"] >= 0.70
    )
    summary = {
        "decision": (
            "PASS - SSL REPRESENTATION SIGNAL"
            if pass_gate
            else "WEAK - SSL REPRESENTATION SIGNAL"
        ),
        "edge_rows": len(rows),
        "event_vocab": event_vocab,
        "view_agreement": agreement,
        "recommendation": (
            "Proceed to a real GraphCL/BGRL encoder on the Cadets edge sample."
            if pass_gate
            else "Improve augmentations/features before spending GPU on a graph encoder."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
