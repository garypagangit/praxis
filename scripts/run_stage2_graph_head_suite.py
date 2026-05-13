from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch_geometric.loader import DataLoader as GraphDataLoader
from torch_geometric.loader import ImbalancedSampler

import praxis.unraveled_v02 as v02
import praxis.unraveled_v03 as v03


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_stage2_de_multiplier_suite import render_markdown_table, write_json
from scripts.run_two_stage_feature_subset_revision import (
    STAGE2_NAMES,
    build_end_to_end_outputs,
    build_feature_subsets,
    choose_threshold,
    compute_per_class_f1,
    compute_recon_auc_scores,
    predict_probs,
    set_seed,
    train_stage1_mlp,
)


GRAPH_PARAM_DEFS: dict[str, dict[str, Any]] = {
    "GCN-DGI": {
        "hidden_dim": 256,
        "dropout": 0.24574024012639728,
        "lr": 0.00176952176975623,
        "weight_decay": 0.0035106710986356803,
        "use_dgi_pretraining": True,
    },
    "RGCN": {
        "hidden_dim": 256,
        "dropout": 0.2952698247725787,
        "lr": 0.0002635083505421187,
        "weight_decay": 3.0655786866011134e-05,
        "use_dgi_pretraining": False,
    },
    "GATv2": {
        "hidden_dim": 128,
        "dropout": 0.3427443652280258,
        "lr": 0.00013513155376407125,
        "weight_decay": 8.552528099160789e-05,
        "heads": 4,
        "attention_dropout": 0.20495510863739339,
        "use_dgi_pretraining": False,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate relational attack-only Stage 2 graph heads inside the fixed "
            "recon_top30 cascade using end-to-end validation selection."
        )
    )
    parser.add_argument("--config", required=True, help="Support-floor base config JSON.")
    parser.add_argument("--run-name", required=True, help="Output folder under runs/.")
    parser.add_argument("--seeds", default="42,43,44", help="Comma-separated seeds.")
    parser.add_argument("--candidate", default="recon_top30", help="Stage 1 feature-subset candidate.")
    parser.add_argument("--models", default="GCN-DGI,RGCN,GATv2", help="Comma-separated graph head model names.")
    parser.add_argument(
        "--s6-feature-importance-csv",
        default="results/S6_mlp_feature_importance/feature_importance.csv",
        help="Overall MLP feature-importance CSV.",
    )
    parser.add_argument(
        "--reference-single-csv",
        default="runs/mlp-support-floor-3seed-ablation-20260423/raw_seed_results.csv",
        help="Single-stage official baseline raw-results CSV.",
    )
    parser.add_argument(
        "--reference-cascade-csv",
        default="runs/stage2-end2end-selection-suite-20260428/raw_results.csv",
        help="Best prior cascade raw-results CSV.",
    )
    return parser.parse_args()


def parse_seeds(raw: str) -> list[int]:
    seeds = [int(item.strip()) for item in raw.split(",") if item.strip()]
    if not seeds:
        raise ValueError("At least one seed is required.")
    return seeds


def parse_models(raw: str) -> list[str]:
    models = [item.strip() for item in raw.split(",") if item.strip()]
    if not models:
        raise ValueError("At least one graph model is required.")
    unknown = [item for item in models if item not in GRAPH_PARAM_DEFS]
    if unknown:
        raise ValueError(f"Unknown graph models: {', '.join(unknown)}")
    return models


def load_settings(config_path: Path) -> dict[str, Any]:
    settings = dict(v03.DEFAULTS)
    settings.update(json.loads(config_path.read_text(encoding="utf-8")))
    return settings


def build_attack_only_loss(labels: np.ndarray, device: torch.device) -> nn.Module:
    weights = v02.compute_class_weights(labels, num_classes=len(STAGE2_NAMES)).to(device)
    return nn.CrossEntropyLoss(weight=weights)


def build_attack_graph_sampler(graphs: list[Any], train_labels: np.ndarray) -> ImbalancedSampler | None:
    counts = np.bincount(train_labels.astype(np.int64), minlength=len(STAGE2_NAMES)).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    class_weights = counts.max() / counts
    proxy_labels: list[int] = []
    for graph in graphs:
        present = np.unique(graph.y.detach().cpu().numpy().astype(np.int64))
        best_label = max(present.tolist(), key=lambda label: (float(class_weights[label]), int(label)))
        proxy_labels.append(int(best_label))
    return ImbalancedSampler(torch.tensor(proxy_labels, dtype=torch.long))


def build_graphs_with_row_ids(
    df: pd.DataFrame,
    feature_cols: list[str],
    model_name: str,
    flows_per_graph: int,
    min_graph_size: int,
    graph_k: int,
    stgcn_temporal_k: int,
    gml: Any,
    shift_labels: bool,
) -> tuple[list[Any], float]:
    working = df.copy().reset_index(drop=True)
    working["diag_row_id"] = np.arange(len(working), dtype=np.int64)
    graphs: list[Any] = []
    covered_row_ids: list[np.ndarray] = []

    ordered_groups = working.groupby("source_file")["timestamp_sort"].min().sort_values().index.tolist()
    for source_file in ordered_groups:
        source_df = (
            working[working["source_file"] == source_file]
            .sort_values("timestamp_sort")
            .reset_index(drop=True)
        )
        for start in range(0, len(source_df), flows_per_graph):
            chunk = source_df.iloc[start : start + flows_per_graph].copy()
            if len(chunk) < min_graph_size:
                continue
            if model_name == "RGCN":
                graph = gml.build_graph_with_custom_k_rgcn(chunk, feature_cols, k=graph_k)
            else:
                graph = gml.build_graph_with_custom_k(chunk, feature_cols, k=graph_k)
            if graph is None:
                continue
            if shift_labels:
                graph.y = graph.y - 1
            graph.row_ids = torch.tensor(chunk["diag_row_id"].to_numpy(dtype=np.int64), dtype=torch.long)
            graph.source_file = source_file
            graphs.append(graph)
            covered_row_ids.append(chunk["diag_row_id"].to_numpy(dtype=np.int64))

    covered = np.concatenate(covered_row_ids) if covered_row_ids else np.asarray([], dtype=np.int64)
    coverage = float(len(np.unique(covered)) / max(len(working), 1))
    return graphs, coverage


def predict_graph_model_with_row_ids(
    model: nn.Module,
    graphs: list[Any],
    device: torch.device,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray]:
    loader = GraphDataLoader(graphs, batch_size=batch_size, shuffle=False)
    row_ids_list: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []
    model.eval()
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = v02.graph_forward(model, batch)
            probs = torch.softmax(logits, dim=1)
            row_ids_list.append(batch.row_ids.cpu().numpy())
            probs_list.append(probs.cpu().numpy())
    row_ids = np.concatenate(row_ids_list)
    probs = np.vstack(probs_list)
    order = np.argsort(row_ids)
    return row_ids[order], probs[order]


def evaluate_attack_graph_model(
    model: nn.Module,
    graphs: list[Any],
    device: torch.device,
    batch_size: int,
) -> tuple[dict[str, Any], dict[str, float]]:
    loader = GraphDataLoader(graphs, batch_size=batch_size, shuffle=False)
    model.eval()
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []
    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = v02.graph_forward(model, batch)
            probs = torch.softmax(logits, dim=1)
            preds.append(probs.argmax(dim=1).cpu().numpy())
            labels.append(batch.y.cpu().numpy())
            probs_list.append(probs.cpu().numpy())
    y_true = np.concatenate(labels)
    y_pred = np.concatenate(preds)
    probs = np.vstack(probs_list)
    metrics = v02.compute_metrics(y_true, y_pred, probs, STAGE2_NAMES)
    per_class = {
        name: value
        for name, value in compute_per_class_f1(y_true + 1, y_pred + 1).items()
        if name != "Benign"
    }
    return metrics, per_class


def instantiate_attack_graph_model(model_name: str, num_features: int, gml: Any) -> nn.Module:
    params = GRAPH_PARAM_DEFS[model_name]
    hidden_dim = int(params["hidden_dim"])
    dropout = float(params["dropout"])
    if model_name == "GATv2":
        return gml.NodeLevelGATv2(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            attention_dropout=float(params["attention_dropout"]),
            heads=int(params["heads"]),
            num_classes=len(STAGE2_NAMES),
        )
    if model_name == "RGCN":
        return gml.NodeLevelRGCN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            num_classes=len(STAGE2_NAMES),
        )
    if model_name == "GCN-DGI":
        return gml.NodeLevelGCN_DGI(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            pretrained_encoder=None,
            num_classes=len(STAGE2_NAMES),
        )
    raise ValueError(f"Unsupported attack graph model: {model_name}")


def maybe_pretrain_dgi(
    model_name: str,
    train_graphs: list[Any],
    gml: Any,
    device: torch.device,
    batch_size: int,
    epochs: int,
) -> Any:
    if model_name != "GCN-DGI" or not bool(GRAPH_PARAM_DEFS[model_name]["use_dgi_pretraining"]):
        return None
    loader = GraphDataLoader(train_graphs, batch_size=batch_size, shuffle=True)
    return gml.pretrain_with_dgi(
        train_loader=loader,
        num_features=int(train_graphs[0].x.shape[1]),
        device=device,
        hidden_dim=96,
        epochs=int(epochs),
        verbose=True,
    )


def inject_pretrained_encoder(model: nn.Module, encoder: Any) -> None:
    if encoder is None:
        return
    own_state = model.state_dict()
    encoder_state = encoder.state_dict()
    for key, value in encoder_state.items():
        if key in own_state and own_state[key].shape == value.shape:
            own_state[key] = value.detach().cpu().clone()
    model.load_state_dict(own_state)


def train_attack_graph_model_end2end_selected(
    model_name: str,
    train_graphs: list[Any],
    val_attack_graphs: list[Any],
    val_full_graphs: list[Any],
    val_original_y: np.ndarray,
    val_stage1_probs: np.ndarray,
    stage1_threshold: float,
    device: torch.device,
    batch_size: int,
    epochs: int,
    patience: int,
    gml: Any,
    dgi_pretrain_epochs: int,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    train_labels = np.concatenate([graph.y.detach().cpu().numpy() for graph in train_graphs]).astype(np.int64)
    sampler = build_attack_graph_sampler(graphs=train_graphs, train_labels=train_labels)
    train_loader = GraphDataLoader(
        train_graphs,
        batch_size=batch_size,
        shuffle=sampler is None,
        sampler=sampler,
    )

    pretrained_encoder = maybe_pretrain_dgi(
        model_name=model_name,
        train_graphs=train_graphs,
        gml=gml,
        device=device,
        batch_size=batch_size,
        epochs=dgi_pretrain_epochs,
    )
    model = instantiate_attack_graph_model(model_name, int(train_graphs[0].x.shape[1]), gml).to(device)
    inject_pretrained_encoder(model, pretrained_encoder)

    criterion = build_attack_only_loss(train_labels, device=device)
    params = GRAPH_PARAM_DEFS[model_name]
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(params["lr"]),
        weight_decay=float(params["weight_decay"]),
    )

    prior_counts = np.bincount(train_labels, minlength=len(STAGE2_NAMES)).astype(np.float32)
    stage2_prior = prior_counts / max(prior_counts.sum(), 1.0)

    best_state: dict[str, Any] | None = None
    best_snapshot: dict[str, Any] | None = None
    best_key: tuple[float, float, float, float] | None = None
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = v02.graph_forward(model, batch)
            loss = criterion(logits, batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * int(batch.y.numel())
            total_examples += int(batch.y.numel())

        val_attack_metrics, val_attack_per_class = evaluate_attack_graph_model(
            model=model,
            graphs=val_attack_graphs,
            device=device,
            batch_size=batch_size,
        )

        val_row_ids, val_probs_sparse = predict_graph_model_with_row_ids(
            model=model,
            graphs=val_full_graphs,
            device=device,
            batch_size=batch_size,
        )
        full_val_probs = np.tile(stage2_prior.reshape(1, -1), (len(val_original_y), 1)).astype(np.float32)
        full_val_probs[val_row_ids] = val_probs_sparse

        end_val_pred, end_val_probs = build_end_to_end_outputs(
            stage1_probs=val_stage1_probs,
            stage2_probs=full_val_probs,
            threshold=float(stage1_threshold),
        )
        end_val_metrics = v02.compute_metrics(val_original_y, end_val_pred, end_val_probs, v02.STAGE_NAMES)
        end_val_per_class = compute_per_class_f1(val_original_y, end_val_pred)

        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "attack_val_macro_f1": float(val_attack_metrics["f1"]),
                "attack_val_de_f1": float(val_attack_per_class["Data Exfiltration"]),
                "end_val_macro_f1": float(end_val_metrics["f1"]),
                "end_val_recon_f1": float(end_val_per_class["Reconnaissance"]),
                "end_val_de_f1": float(end_val_per_class["Data Exfiltration"]),
            }
        )
        print(
            f"      Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"end_val_macro={end_val_metrics['f1']:.4f} | "
            f"end_val_de={end_val_per_class['Data Exfiltration']:.4f}"
        )

        current_key = (
            float(end_val_metrics["f1"]),
            float(end_val_per_class["Data Exfiltration"]),
            float(end_val_per_class["Reconnaissance"]),
            float(val_attack_metrics["f1"]),
        )
        if best_key is None or current_key > best_key:
            best_key = current_key
            best_snapshot = {
                "attack_val_metrics": val_attack_metrics,
                "attack_val_per_class": val_attack_per_class,
                "end_val_metrics": end_val_metrics,
                "end_val_per_class": end_val_per_class,
                "selected_epoch": epoch,
            }
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_snapshot is None:
        raise RuntimeError("Attack-only graph Stage 2 completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_snapshot, history, {
        "prior_recon": float(stage2_prior[0]),
        "prior_foothold": float(stage2_prior[1]),
        "prior_lm": float(stage2_prior[2]),
        "prior_de": float(stage2_prior[3]),
    }


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    settings = load_settings(config_path)
    repo_root = v02.resolve_repo_root()
    run_dir = (v02.resolve_path(repo_root, settings["output_dir"]) / args.run_name).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    seeds = parse_seeds(args.seeds)
    model_names = parse_models(args.models)
    device = torch.device("cpu")
    mlp_params = v03.resolve_fixed_model_params(settings, "MLP")
    if mlp_params is None:
        raise ValueError("Base config must define fixed_model_params for MLP.")

    v02.set_random_seed(int(settings["random_seed"]))
    gml = v02.load_gml_module(repo_root)
    df, _, cache_path, _ = v02.load_or_build_cache(settings, repo_root)
    train_df, val_df, test_df, feature_cols, preprocess_summary = v03.prepare_features_and_splits_v03(
        df=df,
        settings=settings,
        gml=gml,
        run_dir=run_dir,
    )

    overall_importance = pd.read_csv(v02.resolve_path(repo_root, args.s6_feature_importance_csv))
    overall_importance = overall_importance[
        (overall_importance["dataset"] == "Unraveled") & (overall_importance["model"] == "MLP")
    ][["feature", "importance"]]
    recon_auc_df = compute_recon_auc_scores(train_df, feature_cols)
    candidates = build_feature_subsets(feature_cols, overall_importance, recon_auc_df)
    if str(args.candidate) not in candidates:
        raise ValueError(f"Unknown candidate: {args.candidate}")
    stage1_features = candidates[str(args.candidate)]

    train_x_stage1 = train_df[stage1_features].values.astype(np.float32)
    val_x_stage1 = val_df[stage1_features].values.astype(np.float32)
    test_x_stage1 = test_df[stage1_features].values.astype(np.float32)
    train_binary_y = (train_df["MultiLabel"].values != 0).astype(np.int64)
    val_binary_y = (val_df["MultiLabel"].values != 0).astype(np.int64)
    test_binary_y = (test_df["MultiLabel"].values != 0).astype(np.int64)
    val_original_y = val_df["MultiLabel"].values.astype(np.int64)
    test_original_y = test_df["MultiLabel"].values.astype(np.int64)

    attack_train_df = train_df[train_df["MultiLabel"] != 0].copy()
    attack_val_df = val_df[val_df["MultiLabel"] != 0].copy()
    attack_test_df = test_df[test_df["MultiLabel"] != 0].copy()

    reference_single = pd.read_csv(v02.resolve_path(repo_root, args.reference_single_csv))
    reference_single = reference_single[reference_single["variant"] == "adasyn_weighted_ce"].sort_values("seed")
    reference_cascade = pd.read_csv(v02.resolve_path(repo_root, args.reference_cascade_csv))
    reference_cascade = reference_cascade[
        (reference_cascade["family"] == "adasyn_weighted_ce") & (reference_cascade["de_multiplier"] == 1.0)
    ].sort_values("seed")

    stage1_rows: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    stage1_cache: dict[int, dict[str, Any]] = {}

    for seed in seeds:
        print(f"\nTraining fixed Stage 1 for seed {seed}...")
        set_seed(seed)
        stage1_model = train_stage1_mlp(
            train_x=train_x_stage1,
            train_y=train_binary_y,
            val_x=val_x_stage1,
            val_y=val_binary_y,
            params=mlp_params,
            settings=settings,
            device=device,
        )
        val_stage1_probs = predict_probs(
            stage1_model,
            val_x_stage1,
            val_binary_y,
            int(settings["tabular_batch_size"]),
            device,
        )
        test_stage1_probs = predict_probs(
            stage1_model,
            test_x_stage1,
            test_binary_y,
            int(settings["tabular_batch_size"]),
            device,
        )
        threshold_row = choose_threshold(val_original_y, val_binary_y, val_stage1_probs)
        stage1_cache[int(seed)] = {
            "threshold": float(threshold_row["threshold"]),
            "val_stage1_probs": val_stage1_probs,
            "test_stage1_probs": test_stage1_probs,
        }
        stage1_rows.append(
            {
                "seed": int(seed),
                "candidate": str(args.candidate),
                "threshold": float(threshold_row["threshold"]),
                "val_attack_recall": float(threshold_row["val_attack_recall"]),
                "val_benign_f1": float(threshold_row["val_benign_f1"]),
                "val_recon_attack_recall": float(threshold_row["val_recon_attack_recall"]),
            }
        )

    coverage_rows: list[dict[str, Any]] = []
    for model_name in model_names:
        print(f"\nPreparing graphs for `{model_name}`...")
        train_graphs, train_coverage = build_graphs_with_row_ids(
            df=attack_train_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(settings["flows_per_graph"]),
            min_graph_size=int(settings["min_graph_size"]),
            graph_k=int(settings["graph_k"]),
            stgcn_temporal_k=int(settings["stgcn_temporal_k"]),
            gml=gml,
            shift_labels=True,
        )
        val_attack_graphs, val_attack_coverage = build_graphs_with_row_ids(
            df=attack_val_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(settings["flows_per_graph"]),
            min_graph_size=int(settings["min_graph_size"]),
            graph_k=int(settings["graph_k"]),
            stgcn_temporal_k=int(settings["stgcn_temporal_k"]),
            gml=gml,
            shift_labels=True,
        )
        test_attack_graphs, test_attack_coverage = build_graphs_with_row_ids(
            df=attack_test_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(settings["flows_per_graph"]),
            min_graph_size=int(settings["min_graph_size"]),
            graph_k=int(settings["graph_k"]),
            stgcn_temporal_k=int(settings["stgcn_temporal_k"]),
            gml=gml,
            shift_labels=True,
        )
        val_full_graphs, val_full_coverage = build_graphs_with_row_ids(
            df=val_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(settings["flows_per_graph"]),
            min_graph_size=int(settings["min_graph_size"]),
            graph_k=int(settings["graph_k"]),
            stgcn_temporal_k=int(settings["stgcn_temporal_k"]),
            gml=gml,
            shift_labels=False,
        )
        test_full_graphs, test_full_coverage = build_graphs_with_row_ids(
            df=test_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(settings["flows_per_graph"]),
            min_graph_size=int(settings["min_graph_size"]),
            graph_k=int(settings["graph_k"]),
            stgcn_temporal_k=int(settings["stgcn_temporal_k"]),
            gml=gml,
            shift_labels=False,
        )

        coverage_rows.append(
            {
                "model": model_name,
                "train_attack_coverage": train_coverage,
                "val_attack_coverage": val_attack_coverage,
                "test_attack_coverage": test_attack_coverage,
                "val_full_coverage": val_full_coverage,
                "test_full_coverage": test_full_coverage,
                "train_graphs": len(train_graphs),
                "val_attack_graphs": len(val_attack_graphs),
                "test_attack_graphs": len(test_attack_graphs),
                "val_full_graphs": len(val_full_graphs),
                "test_full_graphs": len(test_full_graphs),
            }
        )

        if not train_graphs or not val_attack_graphs or not test_attack_graphs or not val_full_graphs or not test_full_graphs:
            raise RuntimeError(f"{model_name} attack-only graph construction produced an empty split.")

        print(f"Running attack-only graph Stage 2 `{model_name}`...")
        for seed in seeds:
            set_seed(seed)
            model, selection_snapshot, history, prior_summary = train_attack_graph_model_end2end_selected(
                model_name=model_name,
                train_graphs=copy.deepcopy(train_graphs),
                val_attack_graphs=copy.deepcopy(val_attack_graphs),
                val_full_graphs=copy.deepcopy(val_full_graphs),
                val_original_y=val_original_y,
                val_stage1_probs=stage1_cache[int(seed)]["val_stage1_probs"],
                stage1_threshold=float(stage1_cache[int(seed)]["threshold"]),
                device=device,
                batch_size=int(settings["graph_batch_size"]),
                epochs=int(settings["train_epochs"]),
                patience=int(settings["early_stopping_patience"]),
                gml=gml,
                dgi_pretrain_epochs=int(settings["dgi_pretrain_epochs"]),
            )

            attack_test_metrics, attack_test_per_class = evaluate_attack_graph_model(
                model=model,
                graphs=test_attack_graphs,
                device=device,
                batch_size=int(settings["graph_batch_size"]),
            )
            test_row_ids, test_probs_sparse = predict_graph_model_with_row_ids(
                model=model,
                graphs=test_full_graphs,
                device=device,
                batch_size=int(settings["graph_batch_size"]),
            )
            prior = np.asarray(
                [
                    prior_summary["prior_recon"],
                    prior_summary["prior_foothold"],
                    prior_summary["prior_lm"],
                    prior_summary["prior_de"],
                ],
                dtype=np.float32,
            )
            full_test_probs = np.tile(prior.reshape(1, -1), (len(test_df), 1)).astype(np.float32)
            full_test_probs[test_row_ids] = test_probs_sparse
            end_test_pred, end_test_probs = build_end_to_end_outputs(
                stage1_probs=stage1_cache[int(seed)]["test_stage1_probs"],
                stage2_probs=full_test_probs,
                threshold=float(stage1_cache[int(seed)]["threshold"]),
            )
            end_test_metrics = v02.compute_metrics(test_original_y, end_test_pred, end_test_probs, v02.STAGE_NAMES)
            end_test_per_class = compute_per_class_f1(test_original_y, end_test_pred)

            prev_row = reference_cascade[reference_cascade["seed"] == int(seed)].iloc[0]
            single_row = reference_single[reference_single["seed"] == int(seed)].iloc[0]

            raw_rows.append(
                {
                    "model": model_name,
                    "seed": int(seed),
                    "selected_epoch": int(selection_snapshot["selected_epoch"]),
                    "threshold": float(stage1_cache[int(seed)]["threshold"]),
                    "attack_accuracy": float(attack_test_metrics["accuracy"]),
                    "attack_macro_f1": float(attack_test_metrics["f1"]),
                    "attack_pr_auc": float(attack_test_metrics["pr_auc"]) if attack_test_metrics["pr_auc"] is not None else np.nan,
                    "attack_recon_f1": float(attack_test_per_class["Reconnaissance"]),
                    "attack_de_f1": float(attack_test_per_class["Data Exfiltration"]),
                    "end_accuracy": float(end_test_metrics["accuracy"]),
                    "end_macro_f1": float(end_test_metrics["f1"]),
                    "end_pr_auc": float(end_test_metrics["pr_auc"]) if end_test_metrics["pr_auc"] is not None else np.nan,
                    "end_recon_f1": float(end_test_per_class["Reconnaissance"]),
                    "end_de_f1": float(end_test_per_class["Data Exfiltration"]),
                    "delta_vs_prev_end_macro": float(end_test_metrics["f1"] - prev_row["end_macro_f1"]),
                    "delta_vs_prev_end_de": float(end_test_per_class["Data Exfiltration"] - prev_row["end_de_f1"]),
                    "delta_vs_single_end_macro": float(end_test_metrics["f1"] - single_row["macro_f1"]),
                    "delta_vs_single_end_de": float(end_test_per_class["Data Exfiltration"] - single_row["de_f1"]),
                }
            )

            artifact_dir = run_dir / "seed_runs" / model_name / f"seed_{seed}"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), artifact_dir / "stage2_graph_state_dict.pt")
            write_json(
                artifact_dir / "results.json",
                {
                    "model": model_name,
                    "seed": int(seed),
                    "params": GRAPH_PARAM_DEFS[model_name],
                    "selection_snapshot": selection_snapshot,
                    "history": history,
                    "prior_summary": prior_summary,
                    "attack_only_test_metrics": attack_test_metrics,
                    "attack_only_test_per_class_f1": attack_test_per_class,
                    "end_to_end_test_metrics": end_test_metrics,
                    "end_to_end_test_per_class_f1": end_test_per_class,
                },
            )

    coverage_frame = pd.DataFrame(coverage_rows).sort_values("model").reset_index(drop=True)
    coverage_frame.to_csv(run_dir / "graph_coverage.csv", index=False)
    stage1_frame = pd.DataFrame(stage1_rows).sort_values("seed").reset_index(drop=True)
    stage1_frame.to_csv(run_dir / "stage1_fixed.csv", index=False)

    raw_frame = pd.DataFrame(raw_rows).sort_values(["model", "seed"]).reset_index(drop=True)
    raw_frame.to_csv(run_dir / "raw_results.csv", index=False)

    summary_frame = raw_frame.groupby("model").agg(
        end_accuracy_mean=("end_accuracy", "mean"),
        end_accuracy_std=("end_accuracy", "std"),
        end_macro_f1_mean=("end_macro_f1", "mean"),
        end_macro_f1_std=("end_macro_f1", "std"),
        end_pr_auc_mean=("end_pr_auc", "mean"),
        end_pr_auc_std=("end_pr_auc", "std"),
        end_recon_f1_mean=("end_recon_f1", "mean"),
        end_recon_f1_std=("end_recon_f1", "std"),
        end_de_f1_mean=("end_de_f1", "mean"),
        end_de_f1_std=("end_de_f1", "std"),
        delta_vs_prev_end_macro_mean=("delta_vs_prev_end_macro", "mean"),
        delta_vs_prev_end_de_mean=("delta_vs_prev_end_de", "mean"),
        delta_vs_single_end_macro_mean=("delta_vs_single_end_macro", "mean"),
        delta_vs_single_end_de_mean=("delta_vs_single_end_de", "mean"),
    ).reset_index()
    summary_frame = summary_frame.sort_values(["end_macro_f1_mean", "end_de_f1_mean"], ascending=[False, False]).reset_index(drop=True)
    summary_frame.to_csv(run_dir / "summary_mean_std.csv", index=False)

    decision = {
        "best_model": summary_frame.iloc[0].to_dict(),
        "beats_prior_cascade_macro": bool((summary_frame["delta_vs_prev_end_macro_mean"] > 0.0).any()),
        "beats_prior_cascade_de": bool((summary_frame["delta_vs_prev_end_de_mean"] > 0.0).any()),
        "beats_single_stage_with_de_hold": bool(
            ((summary_frame["delta_vs_single_end_macro_mean"] > 0.0) & (summary_frame["delta_vs_single_end_de_mean"] >= -0.10)).any()
        ),
    }
    write_json(
        run_dir / "summary.json",
        {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "config_path": str(config_path),
            "candidate": str(args.candidate),
            "models": model_names,
            "cache_path": str(cache_path),
            "preprocess_summary": preprocess_summary,
            "stage1_rows": stage1_frame.to_dict(orient="records"),
            "coverage_rows": coverage_frame.to_dict(orient="records"),
            "summary_rows": summary_frame.to_dict(orient="records"),
            "decision": decision,
        },
    )

    report_lines = [
        "# Stage 2 Graph Head Suite",
        "",
        f"Config: `{config_path.name}`",
        f"Candidate: `{args.candidate}`",
        f"Models: `{', '.join(model_names)}`",
        "",
        "## Coverage",
        "",
        render_markdown_table(coverage_frame),
        "",
        "## Summary",
        "",
        render_markdown_table(summary_frame),
        "",
        "## Decision",
        "",
        "```json",
        json.dumps(v02.coerce_json(decision), indent=2),
        "```",
        "",
    ]
    (run_dir / "report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Coverage: {run_dir / 'graph_coverage.csv'}")
    print(f"Raw results: {run_dir / 'raw_results.csv'}")
    print(f"Summary: {run_dir / 'summary_mean_std.csv'}")
    print(f"Report: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
