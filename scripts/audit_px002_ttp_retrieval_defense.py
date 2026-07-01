#!/usr/bin/env python3
"""Defense audit for PX-002 ATT&CK TTP-set profile retrieval.

The original positive asks whether sampled observed TTPs retrieve the same ATT&CK
group profile. This audit adds harsher settings:

1. standard: reproduce the original profile-retrieval protocol.
2. leave_query_out: remove the observed query techniques from the true group's
   candidate profile before ranking, so exact self-overlap cannot win.
3. noisy_query: replace a fraction of observed techniques with techniques from
   other groups, approximating noisy incident extraction.

The result decides whether PX-002 is defense-ready or only a bounded lookup-style
profile retrieval artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_attack_ttp_graph_embedding_baseline import load_attack_graph, rank_metrics


DEFAULT_ATTACK_JSON = Path("external/datasets/mitre-attack/enterprise-attack/enterprise-attack.json")
DEFAULT_OUT_DIR = Path("runs/px002-ttp-retrieval-defense-audit-20260630")
DEFAULT_REPORT = Path(
    "reports/gnn_attribution_ttp_graph_embeddings/"
    "PX002_TTP_RETRIEVAL_DEFENSE_AUDIT_20260630.md"
)


def evaluate_setting(
    matrix: np.ndarray,
    groups: list[dict[str, str]],
    techniques: list[dict[str, str]],
    setting: str,
    shot: int,
    seeds: list[int],
    min_degree: int,
    noise_rate: float = 0.4,
) -> pd.DataFrame:
    group_degrees = matrix.sum(axis=1).astype(int)
    eligible = np.where(group_degrees >= min_degree)[0]
    full_norms = np.linalg.norm(matrix, axis=1)
    full_norms[full_norms == 0] = 1.0
    frequency_scores = group_degrees.astype(np.float32)

    n_components = min(32, matrix.shape[0] - 1, matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=13)
    group_latent = svd.fit_transform(matrix)

    records: list[dict[str, Any]] = []
    all_techniques = np.arange(matrix.shape[1])
    for seed in seeds:
        rng = np.random.default_rng(seed + shot * 1000)
        for group_idx in eligible:
            technique_indices = np.flatnonzero(matrix[group_idx] > 0)
            if len(technique_indices) < shot:
                continue

            observed = rng.choice(technique_indices, size=shot, replace=False)
            if setting == "noisy_query":
                noise_count = max(1, int(round(noise_rate * shot)))
                replace_positions = rng.choice(np.arange(shot), size=noise_count, replace=False)
                outside = np.setdiff1d(all_techniques, technique_indices, assume_unique=False)
                observed = observed.copy()
                observed[replace_positions] = rng.choice(outside, size=noise_count, replace=False)

            query = np.zeros(matrix.shape[1], dtype=np.float32)
            query[observed] = 1.0
            query_norm = np.linalg.norm(query)

            candidate_matrix = matrix.copy()
            if setting == "leave_query_out":
                candidate_matrix[group_idx, observed] = 0.0
            candidate_norms = np.linalg.norm(candidate_matrix, axis=1)
            candidate_norms[candidate_norms == 0] = 1.0
            candidate_latent = svd.transform(candidate_matrix)

            random_rng = np.random.default_rng(seed + shot * 1000 + int(group_idx) * 7919 + 17)
            method_scores = {
                "random_uniform": random_rng.random(matrix.shape[0]),
                "frequency_prior": frequency_scores,
                "overlap_cosine": (candidate_matrix @ query) / (candidate_norms * max(query_norm, 1e-12)),
            }
            query_latent = query @ svd.components_.T
            method_scores["svd32_graph_embedding"] = cosine_similarity(
                query_latent.reshape(1, -1), candidate_latent
            )[0]

            for method, scores in method_scores.items():
                metrics = rank_metrics(np.asarray(scores), int(group_idx))
                records.append(
                    {
                        "setting": setting,
                        "method": method,
                        "shot": shot,
                        "seed": seed,
                        "group": groups[group_idx]["name"],
                        "group_external_id": groups[group_idx]["external_id"],
                        "group_degree": int(group_degrees[group_idx]),
                        **metrics,
                    }
                )
    return pd.DataFrame.from_records(records)


def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.groupby(["setting", "method", "shot"], as_index=False)
        .agg(
            top1=("top1", "mean"),
            top5=("top5", "mean"),
            top10=("top10", "mean"),
            mrr=("mrr", "mean"),
            median_rank=("rank", "median"),
            queries=("rank", "size"),
        )
        .sort_values(["setting", "shot", "method"])
    )


def table(frame: pd.DataFrame) -> list[str]:
    cols = ["setting", "method", "shot", "top1", "top5", "top10", "mrr", "median_rank", "queries"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in frame[cols].to_dict("records"):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["setting"]),
                    str(row["method"]),
                    str(row["shot"]),
                    f"{row['top1']:.3f}",
                    f"{row['top5']:.3f}",
                    f"{row['top10']:.3f}",
                    f"{row['mrr']:.3f}",
                    f"{row['median_rank']:.1f}",
                    str(int(row["queries"])),
                ]
            )
            + " |"
        )
    return lines


def decide(summary: pd.DataFrame) -> dict[str, Any]:
    def get(setting: str, method: str) -> float:
        rows = summary[(summary["setting"] == setting) & (summary["method"] == method)]
        if rows.empty:
            return float("nan")
        return float(rows.iloc[0]["top5"])

    standard_overlap = get("standard", "overlap_cosine")
    leave_overlap = get("leave_query_out", "overlap_cosine")
    noisy_overlap = get("noisy_query", "overlap_cosine")
    leave_svd = get("leave_query_out", "svd32_graph_embedding")
    noisy_svd = get("noisy_query", "svd32_graph_embedding")

    defense_ready = leave_overlap >= 0.70 and noisy_overlap >= 0.70 and leave_svd >= 0.60 and noisy_svd >= 0.60
    bounded_positive = standard_overlap >= 0.90
    if defense_ready:
        status = "DEFENSE-READY PROFILE RETRIEVAL POSITIVE"
        recommendation = "Keep PX-002 as a true defense-positive profile retrieval result."
    elif bounded_positive:
        status = "BOUNDED LOOKUP-STYLE POSITIVE ONLY"
        recommendation = (
            "Keep PX-002 only as a bounded profile-lookup artifact. Do not use it as a major "
            "Praxis defense pillar because anti-tautology/noisy-query stress is too weak."
        )
    else:
        status = "NOT A TRUE POSITIVE"
        recommendation = "Demote PX-002 from positives."
    return {
        "status": status,
        "defense_ready": defense_ready,
        "bounded_positive": bounded_positive,
        "standard_overlap_top5": standard_overlap,
        "leave_query_out_overlap_top5": leave_overlap,
        "noisy_query_overlap_top5": noisy_overlap,
        "leave_query_out_svd_top5": leave_svd,
        "noisy_query_svd_top5": noisy_svd,
        "recommendation": recommendation,
    }


def write_report(report: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# PX-002 TTP Retrieval Defense Audit",
        "",
        f"Generated: {payload['generated_utc']}",
        "",
        f"Status: **{payload['decision']['status']}**",
        "",
        "## Purpose",
        "",
        "This audit tests whether the ATT&CK group-profile retrieval positive survives harsher defense conditions. The original positive samples observed TTPs from the target group's profile and ranks candidate profiles. That is useful as profile lookup, but it can overstate defense readiness because exact self-overlap is available.",
        "",
        "## Stress Settings",
        "",
        "- `standard`: original five-shot profile retrieval.",
        "- `leave_query_out`: remove the observed query techniques from the true group's candidate profile before scoring.",
        "- `noisy_query`: replace 40% of observed techniques with techniques not in the target profile.",
        "",
        "## Results",
        "",
        *table(pd.DataFrame(payload["summary"])),
        "",
        "## Decision",
        "",
        payload["decision"]["recommendation"],
        "",
        "## Artifacts",
        "",
        f"- Raw records: `{(Path(payload['out_dir']) / 'records.csv').as_posix()}`",
        f"- Summary: `{(Path(payload['out_dir']) / 'summary.csv').as_posix()}`",
        f"- JSON payload: `{(Path(payload['out_dir']) / 'payload.json').as_posix()}`",
        "",
    ]
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attack-json", type=Path, default=DEFAULT_ATTACK_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--shot", type=int, default=5)
    parser.add_argument("--min-degree", type=int, default=10)
    args = parser.parse_args()

    groups, techniques, matrix = load_attack_graph(args.attack_json)
    seeds = [13, 42, 271, 1729, 20260510]
    frames = [
        evaluate_setting(matrix, groups, techniques, setting, args.shot, seeds, args.min_degree)
        for setting in ["standard", "leave_query_out", "noisy_query"]
    ]
    records = pd.concat(frames, ignore_index=True)
    summary = summarize(records)
    decision = decide(summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    records.to_csv(args.out_dir / "records.csv", index=False)
    summary.to_csv(args.out_dir / "summary.csv", index=False)
    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "out_dir": str(args.out_dir),
        "report": str(args.report),
        "graph": {
            "groups": len(groups),
            "techniques": len(techniques),
            "edges": int(matrix.sum()),
            "min_degree": args.min_degree,
            "shot": args.shot,
            "seeds": seeds,
        },
        "summary": summary.to_dict("records"),
        "decision": decision,
    }
    (args.out_dir / "payload.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(args.report, payload)
    print(json.dumps({"status": decision["status"], "report": str(args.report)}, indent=2))


if __name__ == "__main__":
    main()
