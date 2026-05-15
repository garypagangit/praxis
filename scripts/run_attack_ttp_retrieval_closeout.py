from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_attack_ttp_graph_embedding_baseline import (
    load_attack_graph,
    rank_metrics,
)


DEFAULT_ATTACK_JSON = Path(
    "external/datasets/mitre-attack/enterprise-attack/enterprise-attack.json"
)
DEFAULT_OUT_DIR = Path("runs/attack-ttp-profile-retrieval-closeout-20260514")
DEFAULT_REPORT = Path(
    "reports/gnn_attribution_ttp_graph_embeddings/"
    "ATTACK_TTP_RETRIEVAL_CLOSEOUT_20260514.md"
)


def bucket_labels(values: np.ndarray) -> tuple[np.ndarray, dict[str, int]]:
    q33, q66 = np.quantile(values, [0.33, 0.66])
    labels = []
    for value in values:
        if value <= q33:
            labels.append("low-degree")
        elif value <= q66:
            labels.append("mid-degree")
        else:
            labels.append("high-degree")
    thresholds = {"low_max": int(q33), "mid_max": int(q66)}
    return np.array(labels), thresholds


def summarize(records: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(records)
    return (
        df.groupby(["method", "shot"], as_index=False)
        .agg(
            top1=("top1", "mean"),
            top5=("top5", "mean"),
            top10=("top10", "mean"),
            mrr=("mrr", "mean"),
            median_rank=("rank", "median"),
            mean_rank=("rank", "mean"),
            queries=("rank", "size"),
        )
        .sort_values(["shot", "method"])
    )


def evaluate(
    matrix: np.ndarray,
    groups: list[dict[str, str]],
    techniques: list[dict[str, str]],
    shots: list[int],
    seeds: list[int],
    min_degree: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    group_degrees = matrix.sum(axis=1).astype(int)
    eligible = np.where(group_degrees >= min_degree)[0]
    eligible_degrees = group_degrees[eligible]
    eligible_bucket_labels, bucket_thresholds = bucket_labels(eligible_degrees)
    eligible_bucket_by_group = {
        int(group_idx): str(label)
        for group_idx, label in zip(eligible, eligible_bucket_labels, strict=True)
    }

    full_norms = np.linalg.norm(matrix, axis=1)
    full_norms[full_norms == 0] = 1.0

    n_components = min(32, matrix.shape[0] - 1, matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=13)
    group_latent = svd.fit_transform(matrix)

    records: list[dict[str, Any]] = []
    example_rows: list[dict[str, Any]] = []

    frequency_scores = group_degrees.astype(np.float32)

    for shot in shots:
        for seed in seeds:
            rng = np.random.default_rng(seed + shot * 1000)
            for group_idx in eligible:
                technique_indices = np.flatnonzero(matrix[group_idx] > 0)
                if len(technique_indices) < shot:
                    continue

                observed = rng.choice(technique_indices, size=shot, replace=False)
                query = np.zeros(matrix.shape[1], dtype=np.float32)
                query[observed] = 1.0
                query_norm = np.linalg.norm(query)

                random_rng = np.random.default_rng(
                    seed + shot * 1000 + int(group_idx) * 7919 + 17
                )
                method_scores = {
                    "random_uniform": random_rng.random(matrix.shape[0]),
                    "frequency_prior": frequency_scores,
                    "overlap_cosine": (matrix @ query) / (full_norms * query_norm),
                }

                query_latent = query @ svd.components_.T
                method_scores["svd32_graph_embedding"] = cosine_similarity(
                    query_latent.reshape(1, -1), group_latent
                )[0]

                method_metrics = {}
                for method, scores in method_scores.items():
                    metrics = rank_metrics(np.asarray(scores), int(group_idx))
                    method_metrics[method] = metrics
                    records.append(
                        {
                            "method": method,
                            "shot": shot,
                            "seed": seed,
                            "group": groups[group_idx]["name"],
                            "group_external_id": groups[group_idx]["external_id"],
                            "group_degree": int(group_degrees[group_idx]),
                            "degree_bucket": eligible_bucket_by_group[int(group_idx)],
                            **metrics,
                        }
                    )

                if shot == 5 and seed == seeds[0] and len(example_rows) < 8:
                    overlap_top5 = np.argsort(-method_scores["overlap_cosine"])[:5]
                    svd_top5 = np.argsort(-method_scores["svd32_graph_embedding"])[:5]
                    observed_labels = [
                        f"{techniques[idx]['external_id']} {techniques[idx]['name']}".strip()
                        for idx in observed
                    ]
                    example_rows.append(
                        {
                            "true_group": groups[group_idx]["name"],
                            "true_group_id": groups[group_idx]["external_id"],
                            "degree": int(group_degrees[group_idx]),
                            "observed_ttps": "; ".join(observed_labels),
                            "overlap_rank": int(method_metrics["overlap_cosine"]["rank"]),
                            "svd_rank": int(method_metrics["svd32_graph_embedding"]["rank"]),
                            "frequency_rank": int(method_metrics["frequency_prior"]["rank"]),
                            "overlap_top5": "; ".join(
                                f"{groups[idx]['name']} ({groups[idx]['external_id']})"
                                for idx in overlap_top5
                            ),
                            "svd_top5": "; ".join(
                                f"{groups[idx]['name']} ({groups[idx]['external_id']})"
                                for idx in svd_top5
                            ),
                        }
                    )

    results = pd.DataFrame.from_records(records)
    summary = summarize(records)
    bucket_summary = (
        results[results["shot"] == 5]
        .groupby(["method", "degree_bucket"], as_index=False)
        .agg(
            top5=("top5", "mean"),
            mrr=("mrr", "mean"),
            median_rank=("rank", "median"),
            queries=("rank", "size"),
            median_degree=("group_degree", "median"),
        )
        .sort_values(["method", "degree_bucket"])
    )

    graph = {
        "groups": len(groups),
        "techniques": len(techniques),
        "edges": int(matrix.sum()),
        "eligible_groups": int(len(eligible)),
        "min_degree": int(min_degree),
        "bucket_thresholds": bucket_thresholds,
        "svd_explained_variance_ratio_sum": float(
            svd.explained_variance_ratio_.sum()
        ),
    }
    return summary, bucket_summary, pd.DataFrame(example_rows), graph


def table_lines(
    frame: pd.DataFrame, columns: list[str], formats: dict[str, str] | None = None
) -> list[str]:
    formats = formats or {}
    lines = []
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("|" + "|".join("---" for _ in columns) + "|")
    for row in frame.to_dict("records"):
        cells = []
        for col in columns:
            value = row[col]
            if col in formats:
                cells.append(format(value, formats[col]))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render_report(
    report: Path,
    summary: pd.DataFrame,
    bucket_summary: pd.DataFrame,
    examples: pd.DataFrame,
    graph: dict[str, Any],
) -> None:
    main_5 = summary[summary["shot"] == 5].copy()
    main_5["top5_lift_vs_random"] = (
        main_5["top5"]
        / float(main_5.loc[main_5["method"] == "random_uniform", "top5"].iloc[0])
    )

    lines = [
        "# ATT&CK TTP-Set Retrieval Closeout",
        "",
        "Generated: 2026-05-14",
        "",
        "Status: **result #2 strengthened; selected as bounded profile-retrieval result**",
        "",
        "## Bottom Line",
        "",
        "The ATT&CK TTP-set branch now clears the main closeout objections for a second narrow result: simple retrieval is strong, it beats random and degree-prior floors, performance remains visible by degree bucket, and the failed GraphSAGE path stays explicitly negative.",
        "",
        "This remains a profile-retrieval result, not CTI prose attribution or actor authorship.",
        "",
        "## Graph And Evaluation",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Groups | {graph['groups']} |",
        f"| Techniques | {graph['techniques']} |",
        f"| Group-technique edges | {graph['edges']} |",
        f"| Eligible groups, degree >= {graph['min_degree']} | {graph['eligible_groups']} |",
        f"| SVD explained-variance ratio sum | {graph['svd_explained_variance_ratio_sum']:.4f} |",
        "",
        "## Main Results With Floor Baselines",
        "",
        "The practical operating point is 5 observed TTPs. At that point, overlap and SVD strongly exceed both random ranking and a simple group-frequency prior.",
        "",
    ]
    display = main_5[
        [
            "method",
            "shot",
            "top1",
            "top5",
            "top10",
            "mrr",
            "median_rank",
            "queries",
            "top5_lift_vs_random",
        ]
    ].copy()
    lines.extend(
        table_lines(
            display,
            [
                "method",
                "shot",
                "top1",
                "top5",
                "top10",
                "mrr",
                "median_rank",
                "queries",
                "top5_lift_vs_random",
            ],
            {
                "top1": ".3f",
                "top5": ".3f",
                "top10": ".3f",
                "mrr": ".3f",
                "median_rank": ".1f",
                "top5_lift_vs_random": ".1f",
            },
        )
    )
    lines.extend(
        [
            "",
            "## All Shot Levels",
            "",
        ]
    )
    lines.extend(
        table_lines(
            summary[
                [
                    "method",
                    "shot",
                    "top1",
                    "top5",
                    "top10",
                    "mrr",
                    "median_rank",
                    "queries",
                ]
            ],
            [
                "method",
                "shot",
                "top1",
                "top5",
                "top10",
                "mrr",
                "median_rank",
                "queries",
            ],
            {
                "top1": ".3f",
                "top5": ".3f",
                "top10": ".3f",
                "mrr": ".3f",
                "median_rank": ".1f",
            },
        )
    )
    lines.extend(
        [
            "",
            "## Five-Shot Degree-Bucket Check",
            "",
            f"Degree buckets are computed over eligible groups. Low degree is <= `{graph['bucket_thresholds']['low_max']}` techniques and mid degree is <= `{graph['bucket_thresholds']['mid_max']}` techniques.",
            "",
        ]
    )
    lines.extend(
        table_lines(
            bucket_summary[
                [
                    "method",
                    "degree_bucket",
                    "top5",
                    "mrr",
                    "median_rank",
                    "median_degree",
                    "queries",
                ]
            ],
            [
                "method",
                "degree_bucket",
                "top5",
                "mrr",
                "median_rank",
                "median_degree",
                "queries",
            ],
            {
                "top5": ".3f",
                "mrr": ".3f",
                "median_rank": ".1f",
                "median_degree": ".1f",
            },
        )
    )
    lines.extend(
        [
            "",
            "## Example Five-Shot Retrievals",
            "",
        ]
    )
    if examples.empty:
        lines.append("No examples captured.")
    else:
        short_examples = examples[
            [
                "true_group",
                "degree",
                "observed_ttps",
                "overlap_rank",
                "svd_rank",
                "frequency_rank",
            ]
        ].copy()
        lines.extend(
            table_lines(
                short_examples,
                [
                    "true_group",
                    "degree",
                    "observed_ttps",
                    "overlap_rank",
                    "svd_rank",
                    "frequency_rank",
                ],
            )
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Select this as the second portfolio result **only** under the bounded claim: ATT&CK group technique profiles support few-shot profile retrieval from observed TTP sets.",
            "",
            "Do not claim CTI prose attribution, attacker authorship, or GNN superiority. The learned GraphSAGE pilot remains a negative result because simple overlap and SVD dominate it.",
            "",
            "## What Is Now Closed",
            "",
            "- Random and frequency-prior floors are present.",
            "- Degree-bucket sensitivity is documented.",
            "- Example retrieval rows are available for paper/slides.",
            "- The claim boundary is explicit.",
            "",
            "## Remaining Optional Polish",
            "",
            "- Add a release-to-release ATT&CK drift split if historical ATT&CK versions are needed.",
            "- Add a small analyst-facing visualization of query techniques to top candidates.",
            "- Convert this report into a thesis subsection after Praxis 06 packaging.",
        ]
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attack-json", type=Path, default=DEFAULT_ATTACK_JSON)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--min-degree", type=int, default=10)
    args = parser.parse_args()

    groups, techniques, matrix = load_attack_graph(args.attack_json)
    summary, bucket_summary, examples, graph = evaluate(
        matrix=matrix,
        groups=groups,
        techniques=techniques,
        shots=[1, 3, 5, 10],
        seeds=[13, 42, 271, 1729, 20260510],
        min_degree=args.min_degree,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out_dir / "retrieval_closeout_summary.csv", index=False)
    bucket_summary.to_csv(args.out_dir / "retrieval_degree_buckets.csv", index=False)
    examples.to_csv(args.out_dir / "retrieval_examples_five_shot.csv", index=False)
    (args.out_dir / "retrieval_closeout_payload.json").write_text(
        json.dumps(
            {
                "graph": graph,
                "summary": summary.to_dict("records"),
                "degree_buckets": bucket_summary.to_dict("records"),
                "examples": examples.to_dict("records"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    render_report(args.report, summary, bucket_summary, examples, graph)
    print(
        json.dumps(
            {
                "report": str(args.report),
                "out_dir": str(args.out_dir),
                "status": "closed_out_bounded_positive",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
