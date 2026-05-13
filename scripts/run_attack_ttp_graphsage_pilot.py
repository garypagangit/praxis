from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from torch import nn
from torch_geometric.nn import SAGEConv


def active(obj: dict[str, Any]) -> bool:
    return not obj.get("revoked", False) and not obj.get("x_mitre_deprecated", False)


def attack_external_id(obj: dict[str, Any]) -> str:
    for ref in obj.get("external_references", []):
        if ref.get("source_name") == "mitre-attack":
            return str(ref.get("external_id") or "")
    return ""


def technique_tactics(obj: dict[str, Any]) -> list[str]:
    phases = obj.get("kill_chain_phases") or []
    return sorted(
        {
            str(phase.get("phase_name", ""))
            for phase in phases
            if phase.get("kill_chain_name") == "mitre-attack"
            and phase.get("phase_name")
        }
    )


def load_attack_graph(
    path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], np.ndarray]:
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
            "tactics": technique_tactics(obj),
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


def make_edge_holdout(
    matrix: np.ndarray,
    rng: np.random.Generator,
    min_degree: int,
    holdout_frac: float,
) -> tuple[np.ndarray, dict[int, np.ndarray], np.ndarray]:
    train = matrix.copy()
    degrees = matrix.sum(axis=1).astype(int)
    eligible = np.where(degrees >= min_degree)[0]
    heldout: dict[int, np.ndarray] = {}
    for group_idx in eligible:
        techs = np.flatnonzero(matrix[group_idx] > 0)
        holdout_n = max(1, int(round(len(techs) * holdout_frac)))
        holdout_n = min(holdout_n, len(techs) - 1)
        held = rng.choice(techs, size=holdout_n, replace=False)
        train[group_idx, held] = 0.0
        heldout[int(group_idx)] = np.array(sorted(held), dtype=int)
    return train, heldout, eligible


def build_node_features(
    train_matrix: np.ndarray,
    techniques: list[dict[str, Any]],
) -> torch.Tensor:
    tactics = sorted({tactic for tech in techniques for tactic in tech["tactics"]})
    tactic_index = {tactic: idx for idx, tactic in enumerate(tactics)}
    feature_dim = 3 + len(tactics)
    n_groups, n_techniques = train_matrix.shape
    features = np.zeros((n_groups + n_techniques, feature_dim), dtype=np.float32)

    group_degree = np.log1p(train_matrix.sum(axis=1))
    tech_degree = np.log1p(train_matrix.sum(axis=0))
    max_degree = max(float(group_degree.max()), float(tech_degree.max()), 1.0)

    features[:n_groups, 0] = 1.0
    features[:n_groups, 2] = group_degree / max_degree
    features[n_groups:, 1] = 1.0
    features[n_groups:, 2] = tech_degree / max_degree
    for tech_idx, tech in enumerate(techniques):
        for tactic in tech["tactics"]:
            features[n_groups + tech_idx, 3 + tactic_index[tactic]] = 1.0
    return torch.from_numpy(features)


def train_edges_to_edge_index(train_matrix: np.ndarray) -> tuple[torch.Tensor, np.ndarray]:
    n_groups = train_matrix.shape[0]
    pairs = np.argwhere(train_matrix > 0)
    forward = np.column_stack([pairs[:, 0], n_groups + pairs[:, 1]])
    reverse = np.column_stack([n_groups + pairs[:, 1], pairs[:, 0]])
    edge_index_np = np.vstack([forward, reverse]).T
    return torch.from_numpy(edge_index_np).long(), pairs.astype(int)


class GraphSageLinkPredictor(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float) -> None:
        super().__init__()
        self.conv1 = SAGEConv(input_dim, hidden_dim)
        self.conv2 = SAGEConv(hidden_dim, hidden_dim)
        self.dropout = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        z = self.conv1(x, edge_index)
        z = F.relu(z)
        z = F.dropout(z, p=self.dropout, training=self.training)
        z = self.conv2(z, edge_index)
        return F.normalize(z, p=2, dim=1)


def sample_negative_edges(
    rng: np.random.Generator,
    positive_pairs: np.ndarray,
    train_matrix: np.ndarray,
) -> np.ndarray:
    n_groups, n_techniques = train_matrix.shape
    negatives = np.empty_like(positive_pairs)
    filled = 0
    while filled < len(positive_pairs):
        group_idx = rng.integers(0, n_groups, size=len(positive_pairs) - filled)
        tech_idx = rng.integers(0, n_techniques, size=len(positive_pairs) - filled)
        mask = train_matrix[group_idx, tech_idx] == 0
        accepted = np.column_stack([group_idx[mask], tech_idx[mask]])
        take = min(len(accepted), len(positive_pairs) - filled)
        if take:
            negatives[filled : filled + take] = accepted[:take]
            filled += take
    return negatives


def train_graphsage(
    train_matrix: np.ndarray,
    techniques: list[dict[str, Any]],
    seed: int,
    epochs: int,
    hidden_dim: int,
    dropout: float,
    lr: float,
    weight_decay: float,
) -> tuple[np.ndarray, list[float]]:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    device = torch.device("cpu")

    x = build_node_features(train_matrix, techniques).to(device)
    edge_index, positive_pairs = train_edges_to_edge_index(train_matrix)
    edge_index = edge_index.to(device)
    positive_pairs_t = torch.from_numpy(positive_pairs).long().to(device)
    model = GraphSageLinkPredictor(x.shape[1], hidden_dim, dropout).to(device)
    opt = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=weight_decay
    )
    n_groups = train_matrix.shape[0]
    losses: list[float] = []

    for _ in range(epochs):
        model.train()
        negative_pairs = sample_negative_edges(rng, positive_pairs, train_matrix)
        negative_pairs_t = torch.from_numpy(negative_pairs).long().to(device)

        z = model(x, edge_index)
        pos_scores = (
            z[positive_pairs_t[:, 0]]
            * z[n_groups + positive_pairs_t[:, 1]]
        ).sum(dim=1)
        neg_scores = (
            z[negative_pairs_t[:, 0]]
            * z[n_groups + negative_pairs_t[:, 1]]
        ).sum(dim=1)
        scores = torch.cat([pos_scores, neg_scores])
        labels = torch.cat(
            [torch.ones_like(pos_scores), torch.zeros_like(neg_scores)]
        )
        loss = F.binary_cross_entropy_with_logits(scores, labels)
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(float(loss.detach().cpu()))

    model.eval()
    with torch.inference_mode():
        embeddings = model(x, edge_index).cpu().numpy()
    return embeddings, losses


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


def cosine_rank(
    query: np.ndarray,
    candidate_matrix: np.ndarray,
    true_index: int,
) -> dict[str, float]:
    query_norm = np.linalg.norm(query)
    if query_norm == 0:
        scores = np.zeros(candidate_matrix.shape[0], dtype=np.float32)
    else:
        candidate_norms = np.linalg.norm(candidate_matrix, axis=1)
        candidate_norms[candidate_norms == 0] = 1.0
        scores = candidate_matrix @ query / (candidate_norms * query_norm)
    return rank_metrics(scores, true_index)


def evaluate_methods(
    full_matrix: np.ndarray,
    train_matrix: np.ndarray,
    heldout: dict[int, np.ndarray],
    eligible: np.ndarray,
    graph_embeddings: np.ndarray,
    shots: list[int],
    seeds: list[int],
) -> pd.DataFrame:
    svd_components = min(32, train_matrix.shape[0] - 1, train_matrix.shape[1] - 1)
    svd = TruncatedSVD(n_components=svd_components, random_state=13)
    group_latent = svd.fit_transform(train_matrix)
    n_groups = train_matrix.shape[0]
    group_z = graph_embeddings[:n_groups]
    technique_z = graph_embeddings[n_groups:]
    group_train_norms = np.linalg.norm(train_matrix, axis=1)
    group_train_norms[group_train_norms == 0] = 1.0

    records = []
    for mode in ["known_profile", "held_edge"]:
        for shot in shots:
            for seed in seeds:
                rng = np.random.default_rng(seed + shot * 1000)
                for group_idx in eligible:
                    if mode == "known_profile":
                        candidate_techs = np.flatnonzero(train_matrix[group_idx] > 0)
                    else:
                        candidate_techs = heldout.get(int(group_idx), np.array([], dtype=int))
                    if len(candidate_techs) < shot:
                        continue
                    observed = rng.choice(candidate_techs, size=shot, replace=False)
                    query = np.zeros(full_matrix.shape[1], dtype=np.float32)
                    query[observed] = 1.0

                    overlap_scores = train_matrix @ query
                    overlap_scores = overlap_scores / (
                        group_train_norms * max(np.linalg.norm(query), 1.0)
                    )
                    records.append(
                        {
                            "mode": mode,
                            "method": "overlap_cosine_train",
                            "shot": shot,
                            "seed": seed,
                            **rank_metrics(overlap_scores, int(group_idx)),
                        }
                    )

                    query_latent = query @ svd.components_.T
                    records.append(
                        {
                            "mode": mode,
                            "method": "svd32_train_graph",
                            "shot": shot,
                            "seed": seed,
                            **cosine_rank(query_latent, group_latent, int(group_idx)),
                        }
                    )

                    query_z = technique_z[observed].mean(axis=0)
                    records.append(
                        {
                            "mode": mode,
                            "method": "graphsage_linkpred",
                            "shot": shot,
                            "seed": seed,
                            **cosine_rank(query_z, group_z, int(group_idx)),
                        }
                    )

    results = pd.DataFrame.from_records(records)
    return (
        results.groupby(["mode", "method", "shot"], as_index=False)
        .agg(
            top1=("top1", "mean"),
            top5=("top5", "mean"),
            top10=("top10", "mean"),
            mrr=("mrr", "mean"),
            median_rank=("rank", "median"),
            queries=("rank", "size"),
        )
        .sort_values(["mode", "shot", "method"])
    )


def render_report(path: Path, payload: dict[str, Any]) -> None:
    summary = pd.DataFrame(payload["summary"])
    lines = [
        "# ATT&CK TTP GraphSAGE Pilot",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{payload['decision']}`",
        "",
        payload["rationale"],
        "",
        "## Graph And Split",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Groups | {payload['graph']['groups']} |",
        f"| Techniques | {payload['graph']['techniques']} |",
        f"| Full group-technique edges | {payload['graph']['full_edges']} |",
        f"| Train group-technique edges | {payload['graph']['train_edges']} |",
        f"| Held-out group-technique edges | {payload['graph']['heldout_edges']} |",
        f"| Eligible groups, degree >= {payload['eval']['min_degree']} | {payload['eval']['eligible_groups']} |",
        f"| GraphSAGE final train loss | {payload['training']['final_loss']:.4f} |",
        "",
        "## Results",
        "",
        "| Mode | Method | Shots | Top-1 | Top-5 | Top-10 | MRR | Median rank | Queries |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['mode']} | {row['method']} | {int(row['shot'])} | "
            f"{row['top1']:.3f} | {row['top5']:.3f} | {row['top10']:.3f} | "
            f"{row['mrr']:.3f} | {row['median_rank']:.1f} | {int(row['queries'])} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `known_profile` asks whether a partial observed TTP set can retrieve the known ATT&CK group profile.",
            "- `held_edge` hides some group-technique edges during training and asks whether the embedding generalizes to withheld TTP associations.",
            "- This is still ATT&CK-profile attribution, not raw CTI prose attribution.",
            "",
            "## Next Logical Step",
            "",
            payload["next_gate"],
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
        default=Path("runs/attack-ttp-graphsage-pilot-20260510"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/gnn_attribution_ttp_graph_embeddings/ATTACK_TTP_GRAPHSAGE_PILOT_20260510.md"
        ),
    )
    parser.add_argument("--min-degree", type=int, default=10)
    parser.add_argument("--holdout-frac", type=float, default=0.2)
    parser.add_argument("--epochs", type=int, default=350)
    parser.add_argument("--hidden-dim", type=int, default=64)
    args = parser.parse_args()

    groups, techniques, matrix = load_attack_graph(args.attack_json)
    split_rng = np.random.default_rng(20260510)
    train_matrix, heldout, eligible = make_edge_holdout(
        matrix, split_rng, min_degree=args.min_degree, holdout_frac=args.holdout_frac
    )
    graph_embeddings, losses = train_graphsage(
        train_matrix=train_matrix,
        techniques=techniques,
        seed=20260510,
        epochs=args.epochs,
        hidden_dim=args.hidden_dim,
        dropout=0.15,
        lr=0.01,
        weight_decay=1e-4,
    )
    summary = evaluate_methods(
        full_matrix=matrix,
        train_matrix=train_matrix,
        heldout=heldout,
        eligible=eligible,
        graph_embeddings=graph_embeddings,
        shots=[1, 3, 5],
        seeds=[13, 42, 271, 1729, 20260510],
    )

    def metric(mode: str, method: str, shot: int, column: str) -> float:
        row = summary[
            (summary["mode"] == mode)
            & (summary["method"] == method)
            & (summary["shot"] == shot)
        ]
        return float(row[column].iloc[0]) if len(row) else 0.0

    known_top5 = metric("known_profile", "graphsage_linkpred", 5, "top5")
    held_top5 = metric("held_edge", "graphsage_linkpred", 3, "top5")
    svd_known_top5 = metric("known_profile", "svd32_train_graph", 5, "top5")
    if known_top5 >= 0.50 and held_top5 >= 0.10:
        decision = "PROCEED - GRAPHSAGE BASELINE VIABLE"
        rationale = (
            "GraphSAGE retrieves known ATT&CK group profiles and shows above-random "
            "generalization on withheld group-technique edges."
        )
        next_gate = (
            "Promote to a frozen multi-seed graph attribution protocol with GraphSAGE, "
            "R-GCN, SVD, and overlap baselines; keep CTI prose claims separate."
        )
    elif known_top5 >= svd_known_top5 - 0.05:
        decision = "MIXED - GRAPHSAGE CLOSE TO SVD BUT HELD-EDGE WEAK"
        rationale = (
            "GraphSAGE is competitive on known-profile attribution, but withheld-edge "
            "generalization is not strong enough for a robustness claim."
        )
        next_gate = (
            "Continue only as a known-profile ATT&CK attribution experiment, or add "
            "richer technique/group text features before claiming generalization."
        )
    else:
        decision = "WEAK - GRAPHSAGE DOES NOT BEAT CHEAP BASELINES"
        rationale = (
            "The learned graph encoder does not justify replacing the simpler SVD/overlap baselines yet."
        )
        next_gate = (
            "Do not spend more GPU/engineering here until metadata features or a better "
            "split objective are defined."
        )

    payload = {
        "decision": decision,
        "rationale": rationale,
        "next_gate": next_gate,
        "graph": {
            "groups": len(groups),
            "techniques": len(techniques),
            "full_edges": int(matrix.sum()),
            "train_edges": int(train_matrix.sum()),
            "heldout_edges": int(matrix.sum() - train_matrix.sum()),
        },
        "eval": {
            "min_degree": args.min_degree,
            "eligible_groups": int(len(eligible)),
            "holdout_frac": args.holdout_frac,
        },
        "training": {
            "epochs": args.epochs,
            "hidden_dim": args.hidden_dim,
            "initial_loss": losses[0],
            "final_loss": losses[-1],
        },
        "summary": summary.to_dict("records"),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary.to_csv(args.out_dir / "summary.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    render_report(args.report, payload)
    print(json.dumps({"report": str(args.report), "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
