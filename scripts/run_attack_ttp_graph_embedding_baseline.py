from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity


def active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def attack_external_id(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return str(ref.get("external_id") or "")
    return ""


def load_attack_graph(path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], np.ndarray]:
    bundle = json.loads(path.read_text(encoding="utf-8"))
    objects = [obj for obj in bundle["objects"] if active(obj)]

    groups_by_id = {
        obj["id"]: {
            "stix_id": obj["id"],
            "name": obj.get("name", ""),
            "external_id": attack_external_id(obj),
        }
        for obj in objects
        if obj.get("type") == "intrusion-set"
    }
    techniques_by_id = {
        obj["id"]: {
            "stix_id": obj["id"],
            "name": obj.get("name", ""),
            "external_id": attack_external_id(obj),
        }
        for obj in objects
        if obj.get("type") == "attack-pattern"
    }
    group_to_techniques: dict[str, set[str]] = defaultdict(set)
    for obj in objects:
        if obj.get("type") != "relationship":
            continue
        if obj.get("relationship_type") != "uses":
            continue
        source = obj.get("source_ref")
        target = obj.get("target_ref")
        if source in groups_by_id and target in techniques_by_id:
            group_to_techniques[source].add(target)

    group_ids = sorted(groups_by_id)
    technique_ids = sorted(techniques_by_id)
    group_index = {group_id: idx for idx, group_id in enumerate(group_ids)}
    technique_index = {
        technique_id: idx for idx, technique_id in enumerate(technique_ids)
    }
    matrix = np.zeros((len(group_ids), len(technique_ids)), dtype=np.float32)
    for group_id, technique_set in group_to_techniques.items():
        for technique_id in technique_set:
            matrix[group_index[group_id], technique_index[technique_id]] = 1.0
    groups = [groups_by_id[group_id] for group_id in group_ids]
    techniques = [techniques_by_id[technique_id] for technique_id in technique_ids]
    return groups, techniques, matrix


def rank_metrics(scores: np.ndarray, true_index: int) -> dict[str, float]:
    order = np.argsort(-scores)
    rank = int(np.where(order == true_index)[0][0]) + 1
    return {
        "top1": float(rank == 1),
        "top5": float(rank <= 5),
        "top10": float(rank <= 10),
        "mrr": 1.0 / rank,
        "rank": float(rank),
    }


def evaluate(
    matrix: np.ndarray,
    groups: list[dict[str, str]],
    components: np.ndarray,
    group_latent: np.ndarray,
    shots: list[int],
    seeds: list[int],
    min_degree: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    group_degrees = matrix.sum(axis=1).astype(int)
    eligible = np.where(group_degrees >= min_degree)[0]
    full_norms = np.linalg.norm(matrix, axis=1)
    full_norms[full_norms == 0] = 1.0

    records = []
    examples = []
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

                overlap_scores = matrix @ query
                overlap_scores = overlap_scores / (full_norms * np.linalg.norm(query))
                overlap = rank_metrics(overlap_scores, int(group_idx))
                records.append(
                    {
                        "method": "overlap_cosine",
                        "shot": shot,
                        "seed": seed,
                        "group": groups[group_idx]["name"],
                        **overlap,
                    }
                )

                query_latent = query @ components.T
                latent_scores = cosine_similarity(
                    query_latent.reshape(1, -1), group_latent
                )[0]
                latent = rank_metrics(latent_scores, int(group_idx))
                records.append(
                    {
                        "method": "svd32_graph_embedding",
                        "shot": shot,
                        "seed": seed,
                        "group": groups[group_idx]["name"],
                        **latent,
                    }
                )

                if seed == seeds[0] and shot in {1, 5} and len(examples) < 12:
                    top5 = np.argsort(-latent_scores)[:5]
                    examples.append(
                        {
                            "shot": shot,
                            "true_group": groups[group_idx]["name"],
                            "true_group_id": groups[group_idx]["external_id"],
                            "true_rank_svd": int(latent["rank"]),
                            "top5_svd": [
                                f"{groups[idx]['name']} ({groups[idx]['external_id']})"
                                for idx in top5
                            ],
                        }
                    )

    results = pd.DataFrame.from_records(records)
    summary = (
        results.groupby(["method", "shot"], as_index=False)
        .agg(
            top1=("top1", "mean"),
            top5=("top5", "mean"),
            top10=("top10", "mean"),
            mrr=("mrr", "mean"),
            median_rank=("rank", "median"),
            queries=("rank", "size"),
        )
        .sort_values(["shot", "method"])
    )
    return summary, pd.DataFrame(examples)


def render_report(path: Path, payload: dict[str, Any]) -> None:
    summary = pd.DataFrame(payload["summary"])
    lines = [
        "# ATT&CK TTP Graph Attribution Baseline",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{payload['decision']}`",
        "",
        payload["rationale"],
        "",
        "## Graph",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Groups | {payload['graph']['groups']} |",
        f"| Techniques | {payload['graph']['techniques']} |",
        f"| Group-technique edges | {payload['graph']['edges']} |",
        f"| Eligible groups, degree >= {payload['eval']['min_degree']} | {payload['eval']['eligible_groups']} |",
        "",
        "## Few-Shot Attribution Results",
        "",
        "| Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['method']} | {int(row['shot'])} | {row['top1']:.3f} | "
            f"{row['top5']:.3f} | {row['top10']:.3f} | {row['mrr']:.3f} | "
            f"{row['median_rank']:.1f} | {int(row['queries'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The overlap baseline is intentionally strong because it scores directly against full ATT&CK group technique profiles.",
            "- The SVD embedding baseline is a cheap stand-in for a graph embedding. If it were flat, a GNN would be hard to justify.",
            "- This evaluates attribution from observed TTP sets, not attribution from raw CTI prose.",
            "",
            "## Next Logical Step",
            "",
            "Promote this branch to a real graph experiment: create temporal/group-held-out splits, add technique/tactic metadata features, and compare SVD/nearest-neighbor against a small GraphSAGE or relational GCN. Keep document-level APTNotes claims separate until report-to-group labels are available.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--attack-json",
        type=Path,
        default=Path(
            "external/datasets/mitre-attack/enterprise-attack/enterprise-attack.json"
        ),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/attack-ttp-graph-attribution-baseline-20260510"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_BASELINE_20260510.md"
        ),
    )
    parser.add_argument("--min-degree", type=int, default=10)
    args = parser.parse_args()

    groups, techniques, matrix = load_attack_graph(args.attack_json)
    n_components = min(32, matrix.shape[0] - 1, matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=13)
    group_latent = svd.fit_transform(matrix)
    summary, examples = evaluate(
        matrix=matrix,
        groups=groups,
        components=svd.components_,
        group_latent=group_latent,
        shots=[1, 3, 5, 10],
        seeds=[13, 42, 271, 1729, 20260510],
        min_degree=args.min_degree,
    )

    best_svd_top5_at_5 = float(
        summary[
            (summary["method"] == "svd32_graph_embedding") & (summary["shot"] == 5)
        ]["top5"].iloc[0]
    )
    decision = (
        "PROCEED - ATTRIBUTION SIGNAL PRESENT"
        if best_svd_top5_at_5 >= 0.35
        else "WEAK - GRAPH EMBEDDING SIGNAL NOT YET ENOUGH"
    )
    rationale = (
        "The cheap SVD graph embedding recovers enough held-out group identity from small TTP sets to justify a real GNN baseline."
        if best_svd_top5_at_5 >= 0.35
        else "The cheap graph embedding does not retrieve groups reliably enough to justify a larger GNN yet."
    )
    graph = {
        "groups": len(groups),
        "techniques": len(techniques),
        "edges": int(matrix.sum()),
    }
    eval_summary = {
        "min_degree": args.min_degree,
        "eligible_groups": int((matrix.sum(axis=1) >= args.min_degree).sum()),
        "svd_explained_variance_ratio_sum": float(
            svd.explained_variance_ratio_.sum()
        ),
    }
    payload = {
        "decision": decision,
        "rationale": rationale,
        "graph": graph,
        "eval": eval_summary,
        "summary": summary.to_dict("records"),
        "examples": examples.to_dict("records"),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out_dir / "few_shot_summary.csv", index=False)
    examples.to_csv(args.out_dir / "retrieval_examples.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    render_report(args.report, payload)
    print(json.dumps({"report": str(args.report), "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
