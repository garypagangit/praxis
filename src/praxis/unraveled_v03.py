from __future__ import annotations

import copy
import gc
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch_geometric.loader import DataLoader as GraphDataLoader
from torch_geometric.loader import ImbalancedSampler

import praxis.unraveled_v02 as v02


STAGE_NAMES = v02.STAGE_NAMES
GRAPH_MODEL_NAMES = v02.GRAPH_MODEL_NAMES
TABULAR_MODEL_NAMES = v02.TABULAR_MODEL_NAMES
ALL_MODEL_NAMES = GRAPH_MODEL_NAMES + TABULAR_MODEL_NAMES

SPLIT_NAMES = ("train", "val", "test")
SPLIT_TO_INDEX = {name: index for index, name in enumerate(SPLIT_NAMES)}

DEFAULTS = {
    "pipeline": "unraveled_v03",
    "run_name": "praxisv03-unraveled-stage-balanced",
    "output_dir": "runs",
    "notes": (
        "Praxisv03 benchmark on Unraveled with stage-balanced capture_day splits, "
        "CB-Focal loss, imbalanced sampling, and fairer Optuna budgets."
    ),
    "data_dir": "imports/unraveled/data/network-flows",
    "cache_dir": "data/processed/unraveled_v02",
    "cache_name": "benchmark_cache.csv",
    "cache_metadata_name": "benchmark_cache_metadata.json",
    "split_mode": "stage_balanced_capture_day",
    "split_group_col": "capture_day",
    "split_blocks": 4,
    "val_size": 0.15,
    "test_size": 0.15,
    "random_seed": 42,
    "include_cover_up": False,
    "benign_keep_rate": 0.05,
    "min_benign_per_file": 64,
    "force_rebuild_cache": False,
    "max_files": None,
    "feature_profile": "clean",
    "max_missing_fraction": 0.98,
    "scaler": "robust",
    "temporal_delta_seed_mode": "carry_split_state",
    "include_delta_features": True,
    "graph_k": 5,
    "stgcn_temporal_k": 4,
    "flows_per_graph": 512,
    "min_graph_size": 64,
    "graph_batch_size": 4,
    "tabular_batch_size": 2048,
    "sequence_length": 512,
    "min_sequence_length": 64,
    "sequence_batch_size": 8,
    "train_epochs": 50,
    "dgi_pretrain_epochs": 25,
    "optuna_trials": 20,
    "optuna_timeout_seconds": None,
    "fixed_model_params": None,
    "early_stopping_patience": 8,
    "run_dgi_pretraining": True,
    "enabled_models": ALL_MODEL_NAMES,
    "force_cpu": False,
    "resume_existing_results": False,
    "loss_name": "cb_focal",
    "cb_beta": 0.999,
    "focal_gamma": 2.0,
    "stage_loss_multipliers": None,
    "imbalance_sampler": "proxy_rare_class",
    "min_stage_total_to_balance": 200,
    "min_train_stage_fraction": 0.35,
    "min_eval_stage_fraction": 0.10,
    "stage_balanced_restarts": 200,
    "stage_balanced_local_moves": 200,
    "stage_balanced_temporal_weight": 1.5,
    "stage_balanced_benign_weight": 0.1,
    "stage_balanced_minority_power": 0.5,
}


def resolve_enabled_models(settings: dict[str, Any]) -> tuple[list[str], list[str]]:
    requested = settings.get("enabled_models", ALL_MODEL_NAMES)
    if isinstance(requested, str):
        requested_models = [item.strip() for item in requested.split(",") if item.strip()]
    else:
        requested_models = [str(item).strip() for item in requested]

    invalid = sorted(set(requested_models) - set(ALL_MODEL_NAMES))
    if invalid:
        raise ValueError(f"Unsupported Praxisv03 model(s): {', '.join(invalid)}")

    graph_models = [name for name in GRAPH_MODEL_NAMES if name in requested_models]
    tabular_models = [name for name in TABULAR_MODEL_NAMES if name in requested_models]
    return graph_models, tabular_models


def resolve_fixed_model_params(settings: dict[str, Any], model_name: str) -> dict[str, Any] | None:
    configured = settings.get("fixed_model_params")
    if configured is None:
        return None
    if not isinstance(configured, dict):
        raise ValueError("Praxisv03 fixed_model_params must be a mapping of model names to params.")

    normalized_target = str(model_name).strip().lower()
    for configured_name, params in configured.items():
        if str(configured_name).strip().lower() != normalized_target:
            continue
        if not isinstance(params, dict):
            raise ValueError(
                f"Praxisv03 fixed_model_params for `{model_name}` must be a JSON object."
            )
        return copy.deepcopy(params)

    return None


def compute_stage_weights(total_stage_counts: np.ndarray, settings: dict[str, Any]) -> np.ndarray:
    power = float(settings.get("stage_balanced_minority_power", 0.5))
    benign_weight = float(settings.get("stage_balanced_benign_weight", 0.1))
    safe_counts = np.maximum(total_stage_counts.astype(np.float64), 1.0)
    weights = (safe_counts.max() / safe_counts) ** power
    weights[0] = benign_weight
    return weights.astype(np.float64)


def derive_stage_minimums(total_stage_counts: np.ndarray, settings: dict[str, Any]) -> dict[str, np.ndarray]:
    minimums = {
        "train": np.zeros(len(STAGE_NAMES), dtype=np.float64),
        "val": np.zeros(len(STAGE_NAMES), dtype=np.float64),
        "test": np.zeros(len(STAGE_NAMES), dtype=np.float64),
    }
    min_stage_total = int(settings.get("min_stage_total_to_balance", 200))
    min_train_fraction = float(settings.get("min_train_stage_fraction", 0.35))
    min_eval_fraction = float(settings.get("min_eval_stage_fraction", 0.10))

    for stage_index in range(1, len(STAGE_NAMES)):
        total = float(total_stage_counts[stage_index])
        if total < min_stage_total:
            continue
        minimums["train"][stage_index] = total * min_train_fraction
        minimums["val"][stage_index] = total * min_eval_fraction
        minimums["test"][stage_index] = total * min_eval_fraction

    return minimums


def build_group_stage_stats(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    stage_counts = df.groupby([group_col, "MultiLabel"]).size().unstack(fill_value=0)
    for stage_index in range(len(STAGE_NAMES)):
        if stage_index not in stage_counts.columns:
            stage_counts[stage_index] = 0

    stats = (
        df.groupby(group_col)
        .agg(
            first_timestamp=("timestamp_sort", "min"),
            rows=("MultiLabel", "size"),
        )
        .join(stage_counts[[stage_index for stage_index in range(len(STAGE_NAMES))]])
        .sort_values("first_timestamp")
    )
    return stats


def score_stage_balanced_assignment(
    assignment: np.ndarray,
    rows_arr: np.ndarray,
    stage_arr: np.ndarray,
    time_rank: np.ndarray,
    row_targets: dict[str, float],
    stage_targets: dict[str, np.ndarray],
    stage_minimums: dict[str, np.ndarray],
    stage_weights: np.ndarray,
    temporal_weight: float,
) -> tuple[float, dict[str, float], dict[str, np.ndarray], dict[str, list[int]]]:
    split_rows = {name: 0.0 for name in SPLIT_NAMES}
    split_counts = {
        name: np.zeros(stage_arr.shape[1], dtype=np.float64)
        for name in SPLIT_NAMES
    }
    split_indices = {name: [] for name in SPLIT_NAMES}

    for group_index, split_index in enumerate(assignment):
        split_name = SPLIT_NAMES[int(split_index)]
        split_rows[split_name] += float(rows_arr[group_index])
        split_counts[split_name] += stage_arr[group_index]
        split_indices[split_name].append(group_index)

    score = 0.0
    desired_mean_time = {"train": 0.35, "val": 0.65, "test": 0.82}
    row_weights = {"train": 0.7, "val": 1.2, "test": 1.2}
    stage_weights_by_split = {"train": 0.6, "val": 1.0, "test": 1.0}
    minimum_penalty_weights = np.array([0.0, 0.04, 0.03, 0.03, 0.05], dtype=np.float64)

    for split_name in SPLIT_NAMES:
        if not split_indices[split_name]:
            return float("inf"), split_rows, split_counts, split_indices

        score += (
            abs(split_rows[split_name] - row_targets[split_name]) / max(row_targets[split_name], 1.0)
        ) * row_weights[split_name]

        stage_diff = np.abs(split_counts[split_name] - stage_targets[split_name]) / np.maximum(
            stage_targets[split_name], 1.0
        )
        score += float((stage_diff * stage_weights).sum()) * stage_weights_by_split[split_name]

        deficits = np.maximum(stage_minimums[split_name] - split_counts[split_name], 0.0)
        score += float((deficits * minimum_penalty_weights).sum())

        mean_rank = float(np.mean(time_rank[np.asarray(split_indices[split_name], dtype=np.int64)]))
        score += abs(mean_rank - desired_mean_time[split_name]) * temporal_weight

    return score, split_rows, split_counts, split_indices


def find_stage_balanced_group_split(
    df: pd.DataFrame,
    group_col: str,
    val_size: float,
    test_size: float,
    settings: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    group_stats = build_group_stage_stats(df, group_col)
    group_names = group_stats.index.tolist()
    rows_arr = group_stats["rows"].to_numpy(dtype=np.float64)
    stage_arr = group_stats[[stage_index for stage_index in range(len(STAGE_NAMES))]].to_numpy(dtype=np.float64)
    total_rows = float(rows_arr.sum())
    total_stage_counts = stage_arr.sum(axis=0)
    time_rank = np.arange(len(group_names), dtype=np.float64) / max(len(group_names) - 1, 1)

    row_targets = {
        "train": total_rows * (1.0 - float(val_size) - float(test_size)),
        "val": total_rows * float(val_size),
        "test": total_rows * float(test_size),
    }
    stage_targets = {
        split_name: total_stage_counts * (row_targets[split_name] / max(total_rows, 1.0))
        for split_name in SPLIT_NAMES
    }
    stage_minimums = derive_stage_minimums(total_stage_counts, settings)
    stage_weights = compute_stage_weights(total_stage_counts, settings)
    temporal_weight = float(settings.get("stage_balanced_temporal_weight", 1.5))

    rarity_score = (stage_arr * stage_weights.reshape(1, -1)).sum(axis=1) / np.maximum(rows_arr, 1.0)
    order = list(range(len(group_names)))
    order.sort(key=lambda index: (rarity_score[index], time_rank[index], rows_arr[index]), reverse=True)

    rng = np.random.default_rng(int(settings["random_seed"]))
    restarts = max(int(settings.get("stage_balanced_restarts", 200)), 1)
    local_moves = max(int(settings.get("stage_balanced_local_moves", 200)), 1)

    best_assignment: np.ndarray | None = None
    best_score = float("inf")
    best_rows: dict[str, float] | None = None
    best_counts: dict[str, np.ndarray] | None = None
    best_indices: dict[str, list[int]] | None = None

    for restart in range(restarts):
        if restart == 0:
            process_order = order.copy()
        else:
            jitter = rng.uniform(0.0, 0.25, size=len(order))
            process_order = sorted(
                order,
                key=lambda index: (
                    rarity_score[index] + jitter[index],
                    time_rank[index],
                    rows_arr[index],
                ),
                reverse=True,
            )

        assignment = np.zeros(len(group_names), dtype=np.int64)
        if process_order:
            assignment[process_order[0]] = SPLIT_TO_INDEX["test"]
        if len(process_order) > 1:
            assignment[process_order[1]] = SPLIT_TO_INDEX["val"]

        seeded = set(process_order[:2])
        for group_index in process_order:
            if group_index in seeded:
                continue
            candidate_scores: list[tuple[float, int]] = []
            for split_name in SPLIT_NAMES:
                candidate_assignment = assignment.copy()
                candidate_assignment[group_index] = SPLIT_TO_INDEX[split_name]
                candidate_score, _, _, _ = score_stage_balanced_assignment(
                    candidate_assignment,
                    rows_arr=rows_arr,
                    stage_arr=stage_arr,
                    time_rank=time_rank,
                    row_targets=row_targets,
                    stage_targets=stage_targets,
                    stage_minimums=stage_minimums,
                    stage_weights=stage_weights,
                    temporal_weight=temporal_weight,
                )
                candidate_scores.append((candidate_score, SPLIT_TO_INDEX[split_name]))

            assignment[group_index] = min(candidate_scores, key=lambda item: item[0])[1]

        current_score, split_rows, split_counts, split_indices = score_stage_balanced_assignment(
            assignment,
            rows_arr=rows_arr,
            stage_arr=stage_arr,
            time_rank=time_rank,
            row_targets=row_targets,
            stage_targets=stage_targets,
            stage_minimums=stage_minimums,
            stage_weights=stage_weights,
            temporal_weight=temporal_weight,
        )

        for _ in range(local_moves):
            improved = False
            for group_index in rng.permutation(len(group_names)):
                original_split = int(assignment[group_index])
                for candidate_split in rng.permutation(len(SPLIT_NAMES)):
                    if int(candidate_split) == original_split:
                        continue
                    candidate_assignment = assignment.copy()
                    candidate_assignment[group_index] = int(candidate_split)
                    candidate_score, candidate_rows, candidate_counts, candidate_indices = (
                        score_stage_balanced_assignment(
                            candidate_assignment,
                            rows_arr=rows_arr,
                            stage_arr=stage_arr,
                            time_rank=time_rank,
                            row_targets=row_targets,
                            stage_targets=stage_targets,
                            stage_minimums=stage_minimums,
                            stage_weights=stage_weights,
                            temporal_weight=temporal_weight,
                        )
                    )
                    if candidate_score + 1e-9 < current_score:
                        assignment = candidate_assignment
                        current_score = candidate_score
                        split_rows = candidate_rows
                        split_counts = candidate_counts
                        split_indices = candidate_indices
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break

        if current_score < best_score:
            best_score = current_score
            best_assignment = assignment.copy()
            best_rows = split_rows
            best_counts = {name: value.copy() for name, value in split_counts.items()}
            best_indices = {name: list(value) for name, value in split_indices.items()}

    if best_assignment is None or best_rows is None or best_counts is None or best_indices is None:
        raise RuntimeError(f"Praxisv03 stage-balanced split failed for `{group_col}`.")

    split_groups = {
        split_name: [group_names[index] for index in best_indices[split_name]]
        for split_name in SPLIT_NAMES
    }

    train_df = (
        df[df[group_col].isin(split_groups["train"])]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    val_df = (
        df[df[group_col].isin(split_groups["val"])]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    test_df = (
        df[df[group_col].isin(split_groups["test"])]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )

    summary = {
        "objective_score": best_score,
        "group_col": group_col,
        "groups_per_split": {split_name: len(split_groups[split_name]) for split_name in SPLIT_NAMES},
        "split_groups": split_groups,
        "row_targets": {name: int(round(value)) for name, value in row_targets.items()},
        "rows_per_split": {name: int(round(best_rows[name])) for name in SPLIT_NAMES},
        "stage_targets": {
            name: {STAGE_NAMES[idx]: int(round(value[idx])) for idx in range(len(STAGE_NAMES))}
            for name, value in stage_targets.items()
        },
        "stage_counts": {
            name: {STAGE_NAMES[idx]: int(round(best_counts[name][idx])) for idx in range(len(STAGE_NAMES))}
            for name in SPLIT_NAMES
        },
        "stage_minimums": {
            name: {STAGE_NAMES[idx]: int(round(stage_minimums[name][idx])) for idx in range(len(STAGE_NAMES))}
            for name in SPLIT_NAMES
        },
    }
    return train_df, val_df, test_df, summary


def prepare_features_and_splits_v03(
    df: pd.DataFrame,
    settings: dict[str, Any],
    gml: Any,
    run_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], dict[str, Any]]:
    numeric_feature_cols = v02.infer_numeric_feature_columns(df)
    split_mode = str(settings.get("split_mode", "stage_balanced_capture_day")).lower()
    holdout_support_floor = v02.parse_holdout_stage_support_floor(
        settings.get("holdout_min_stage_support")
    )
    split_search_summary: dict[str, Any] | None = None

    if split_mode == "stage_balanced_capture_day":
        split_group_col = "capture_day"
        train_df, val_df, test_df, split_search_summary = find_stage_balanced_group_split(
            df=df,
            group_col=split_group_col,
            val_size=float(settings["val_size"]),
            test_size=float(settings["test_size"]),
            settings=settings,
        )
    elif split_mode == "stage_balanced_source_file":
        split_group_col = "source_file"
        train_df, val_df, test_df, split_search_summary = find_stage_balanced_group_split(
            df=df,
            group_col=split_group_col,
            val_size=float(settings["val_size"]),
            test_size=float(settings["test_size"]),
            settings=settings,
        )
    elif split_mode == "within_group_temporal":
        split_group_col = str(settings["split_group_col"])
        train_df, val_df, test_df = v02.split_within_group_temporal(
            df=df,
            group_col=split_group_col,
            val_size=float(settings["val_size"]),
            test_size=float(settings["test_size"]),
            split_blocks=int(settings["split_blocks"]),
            gml=gml,
        )
    elif split_mode == "held_out_capture_day":
        split_group_col = "capture_day"
        if holdout_support_floor is None:
            train_df, val_df, test_df = v02.split_by_group_holdout(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
            )
        else:
            train_df, val_df, test_df, split_search_summary = v02.split_by_group_holdout_support_aware(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
                stage_support_floor=holdout_support_floor,
            )
    elif split_mode == "held_out_source_file":
        split_group_col = "source_file"
        if holdout_support_floor is None:
            train_df, val_df, test_df = v02.split_by_group_holdout(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
            )
        else:
            train_df, val_df, test_df, split_search_summary = v02.split_by_group_holdout_support_aware(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
                stage_support_floor=holdout_support_floor,
            )
    else:
        raise ValueError(f"Unsupported Praxisv03 split_mode: {split_mode}")

    train_df, val_df, test_df, feature_cols, encodings = v02.add_frequency_features(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        feature_cols=numeric_feature_cols,
        feature_profile=str(settings.get("feature_profile", "clean")).lower(),
    )

    train_df, val_df, test_df, feature_cols = gml.compute_temporal_features_split_aware(
        train_df,
        val_df,
        test_df,
        feature_cols,
        delta_seed_mode=str(
            settings.get("temporal_delta_seed_mode", "carry_split_state")
        ).lower(),
        include_delta_features=bool(settings.get("include_delta_features", True)),
    )

    feature_cols, dropped_features = v02.select_feature_columns(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        feature_cols=feature_cols,
        settings=settings,
    )

    for frame in (train_df, val_df, test_df):
        frame[feature_cols] = frame[feature_cols].apply(pd.to_numeric, errors="coerce")
        frame[feature_cols] = frame[feature_cols].replace([np.inf, -np.inf], np.nan)
        frame[feature_cols] = frame[feature_cols].fillna(0.0)

    scaler = v02.fit_scaler(str(settings["scaler"]).lower())
    train_df[feature_cols] = np.nan_to_num(scaler.fit_transform(train_df[feature_cols]), nan=0.0)
    val_df[feature_cols] = np.nan_to_num(scaler.transform(val_df[feature_cols]), nan=0.0)
    test_df[feature_cols] = np.nan_to_num(scaler.transform(test_df[feature_cols]), nan=0.0)

    preprocess_summary = {
        "split_mode": split_mode,
        "split_group_col": split_group_col,
        "feature_cols": feature_cols,
        "feature_count": len(feature_cols),
        "dropped_features": dropped_features,
        "feature_profile": str(settings.get("feature_profile", "clean")).lower(),
        "scaler": str(settings["scaler"]),
        "temporal_delta_seed_mode": str(
            settings.get("temporal_delta_seed_mode", "carry_split_state")
        ).lower(),
        "include_delta_features": bool(settings.get("include_delta_features", True)),
        "categorical_frequency_maps": {
            column: {"unique_values": len(mapping)}
            for column, mapping in encodings.items()
        },
        "splits": {
            "train": v02.summarize_split(train_df),
            "val": v02.summarize_split(val_df),
            "test": v02.summarize_split(test_df),
        },
        "group_overlap": {
            "train_val": int(len(set(train_df[split_group_col]) & set(val_df[split_group_col]))),
            "train_test": int(len(set(train_df[split_group_col]) & set(test_df[split_group_col]))),
            "val_test": int(len(set(val_df[split_group_col]) & set(test_df[split_group_col]))),
        },
        "source_file_overlap": {
            "train_val": int(len(set(train_df["source_file"]) & set(val_df["source_file"]))),
            "train_test": int(len(set(train_df["source_file"]) & set(test_df["source_file"]))),
            "val_test": int(len(set(val_df["source_file"]) & set(test_df["source_file"]))),
        },
    }
    if holdout_support_floor is not None:
        preprocess_summary["holdout_min_stage_support"] = {
            split_name: {
                STAGE_NAMES[idx]: int(holdout_support_floor[split_name][idx])
                for idx in range(len(STAGE_NAMES))
            }
            for split_name in ("train", "val", "test")
        }
    if split_search_summary is not None:
        if split_mode.startswith("stage_balanced_"):
            preprocess_summary["stage_balanced_split"] = split_search_summary
        else:
            preprocess_summary["strict_holdout_split"] = split_search_summary

    v02.write_json(run_dir / "preprocess-summary.json", preprocess_summary)
    return train_df, val_df, test_df, feature_cols, preprocess_summary


def compute_effective_class_weights(
    labels: np.ndarray,
    num_classes: int,
    beta: float,
) -> torch.Tensor:
    counts = np.bincount(labels[labels >= 0], minlength=num_classes).astype(np.float64)
    counts = np.maximum(counts, 1.0)
    effective_num = 1.0 - np.power(beta, counts)
    weights = (1.0 - beta) / np.maximum(effective_num, 1e-12)
    weights = weights / weights.mean()
    return torch.tensor(weights.astype(np.float32), dtype=torch.float32)


def normalize_stage_key(value: str) -> str:
    return "".join(character for character in value.strip().lower() if character.isalnum())


def resolve_stage_loss_multipliers(settings: dict[str, Any]) -> torch.Tensor:
    multipliers = np.ones(len(STAGE_NAMES), dtype=np.float32)
    raw = settings.get("stage_loss_multipliers")
    if raw is None:
        return torch.tensor(multipliers, dtype=torch.float32)

    if isinstance(raw, (list, tuple)):
        if len(raw) != len(STAGE_NAMES):
            raise ValueError(
                f"stage_loss_multipliers must have {len(STAGE_NAMES)} values when passed as a list."
            )
        multipliers = np.asarray(raw, dtype=np.float32)
    elif isinstance(raw, dict):
        name_to_index = {
            normalize_stage_key(stage_name): index for index, stage_name in enumerate(STAGE_NAMES)
        }
        for key, value in raw.items():
            if isinstance(key, int):
                index = key
            else:
                key_text = str(key).strip()
                if key_text.isdigit():
                    index = int(key_text)
                else:
                    normalized = normalize_stage_key(key_text)
                    if normalized not in name_to_index:
                        raise ValueError(f"Unknown stage in stage_loss_multipliers: {key}")
                    index = name_to_index[normalized]

            if index < 0 or index >= len(STAGE_NAMES):
                raise ValueError(f"Stage index out of range in stage_loss_multipliers: {index}")
            multipliers[index] = float(value)
    else:
        raise ValueError("stage_loss_multipliers must be null, a list, or a dict.")

    if np.any(multipliers <= 0.0):
        raise ValueError("stage_loss_multipliers values must be positive.")

    multipliers = multipliers / max(float(multipliers.mean()), 1e-8)
    return torch.tensor(multipliers.astype(np.float32), dtype=torch.float32)


class ClassBalancedFocalLoss(nn.Module):
    def __init__(
        self,
        alpha: torch.Tensor | None,
        gamma: float = 2.0,
        ignore_index: int | None = None,
    ):
        super().__init__()
        self.gamma = float(gamma)
        self.ignore_index = ignore_index
        if alpha is None:
            self.register_buffer("alpha", torch.empty(0))
        else:
            self.register_buffer("alpha", alpha.to(torch.float32))

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        if logits.ndim > 2:
            logits = logits.reshape(-1, logits.shape[-1])
            targets = targets.reshape(-1)

        if self.ignore_index is not None:
            mask = targets != self.ignore_index
            logits = logits[mask]
            targets = targets[mask]

        if targets.numel() == 0:
            return logits.new_tensor(0.0)

        log_probs = F.log_softmax(logits, dim=1)
        log_pt = log_probs.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt = log_pt.exp()
        focal_weight = torch.pow(1.0 - pt, self.gamma)

        if self.alpha.numel():
            focal_weight = focal_weight * self.alpha[targets]

        loss = -focal_weight * log_pt
        return loss.mean()


def build_loss(
    settings: dict[str, Any],
    labels: np.ndarray,
    device: torch.device,
    ignore_index: int | None = None,
) -> nn.Module:
    stage_multipliers = resolve_stage_loss_multipliers(settings).to(device)
    loss_name = str(settings.get("loss_name", "cb_focal")).lower()
    if loss_name == "cb_focal":
        alpha = compute_effective_class_weights(
            labels=labels,
            num_classes=len(STAGE_NAMES),
            beta=float(settings.get("cb_beta", 0.999)),
        ).to(device)
        alpha = alpha * stage_multipliers
        alpha = alpha / alpha.mean().clamp_min(1e-8)
        return ClassBalancedFocalLoss(
            alpha=alpha,
            gamma=float(settings.get("focal_gamma", 2.0)),
            ignore_index=ignore_index,
        )

    weights = v02.compute_class_weights(labels, num_classes=len(STAGE_NAMES)).to(device)
    weights = weights * stage_multipliers
    weights = weights / weights.mean().clamp_min(1e-8)
    return nn.CrossEntropyLoss(weight=weights, ignore_index=ignore_index if ignore_index is not None else -100)


def build_proxy_sampling_labels(items: list[np.ndarray], class_weights: np.ndarray) -> np.ndarray:
    proxy_labels = []
    for labels in items:
        present = np.unique(labels.astype(np.int64))
        best_label = max(present.tolist(), key=lambda label: (float(class_weights[label]), int(label)))
        proxy_labels.append(int(best_label))
    return np.asarray(proxy_labels, dtype=np.int64)


def build_graph_sampler(graphs, train_labels: np.ndarray, settings: dict[str, Any]):
    if str(settings.get("imbalance_sampler", "proxy_rare_class")).lower() == "none":
        return None

    label_weights = compute_stage_weights(
        np.bincount(train_labels, minlength=len(STAGE_NAMES)).astype(np.float64),
        settings,
    )
    proxy_labels = build_proxy_sampling_labels(
        [graph.y.detach().cpu().numpy() for graph in graphs],
        class_weights=label_weights,
    )
    return ImbalancedSampler(torch.tensor(proxy_labels, dtype=torch.long))


def build_row_sampler(labels: np.ndarray, settings: dict[str, Any]):
    if str(settings.get("imbalance_sampler", "proxy_rare_class")).lower() == "none":
        return None
    return ImbalancedSampler(torch.tensor(labels.astype(np.int64), dtype=torch.long))


def build_sequence_sampler(
    chunks: list[tuple[np.ndarray, np.ndarray]],
    train_labels: np.ndarray,
    settings: dict[str, Any],
):
    if str(settings.get("imbalance_sampler", "proxy_rare_class")).lower() == "none":
        return None

    label_weights = compute_stage_weights(
        np.bincount(train_labels, minlength=len(STAGE_NAMES)).astype(np.float64),
        settings,
    )
    proxy_labels = build_proxy_sampling_labels(
        [chunk[1] for chunk in chunks],
        class_weights=label_weights,
    )
    return ImbalancedSampler(torch.tensor(proxy_labels, dtype=torch.long))


def maybe_clear_device_cache() -> None:
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def train_graph_model_v03(
    model: nn.Module,
    train_loader: GraphDataLoader,
    val_loader: GraphDataLoader,
    device: torch.device,
    train_labels: np.ndarray,
    settings: dict[str, Any],
    lr: float,
    weight_decay: float,
    trial: optuna.Trial | None = None,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = build_loss(settings=settings, labels=train_labels, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(settings["train_epochs"]) + 1):
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

            total_loss += float(loss.item()) * batch.y.numel()
            total_examples += int(batch.y.numel())

        val_metrics = v02.evaluate_graph_model(model, val_loader, device)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": val_metrics["f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"    Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
        )

        if trial is not None:
            trial.report(float(val_metrics["f1"]), step=epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if val_metrics["f1"] > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Praxisv03 graph training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


def train_row_model_v03(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    train_labels: np.ndarray,
    device: torch.device,
    settings: dict[str, Any],
    lr: float,
    weight_decay: float,
    trial: optuna.Trial | None = None,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = build_loss(settings=settings, labels=train_labels, device=device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0

        for xs, ys in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits, ys)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * int(ys.numel())
            total_examples += int(ys.numel())

        val_metrics = v02.evaluate_row_model(model, val_loader, device)
        train_loss = total_loss / max(total_examples, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": val_metrics["f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"    Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
        )

        if trial is not None:
            trial.report(float(val_metrics["f1"]), step=epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if val_metrics["f1"] > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Praxisv03 row-model training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


def train_sequence_model_v03(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    train_labels: np.ndarray,
    device: torch.device,
    settings: dict[str, Any],
    lr: float,
    weight_decay: float,
    trial: optuna.Trial | None = None,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = build_loss(
        settings=settings,
        labels=train_labels,
        device=device,
        ignore_index=-100,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, int(settings["train_epochs"]) + 1):
        model.train()
        total_loss = 0.0
        total_tokens = 0

        for xs, ys, mask in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            mask = mask.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits.view(-1, logits.shape[-1]), ys.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * int(mask.sum().item())
            total_tokens += int(mask.sum().item())

        val_metrics = v02.evaluate_sequence_model(model, val_loader, device)
        train_loss = total_loss / max(total_tokens, 1)
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "val_f1": val_metrics["f1"],
                "val_accuracy": val_metrics["accuracy"],
            }
        )
        print(
            f"    Epoch {epoch:02d} | loss={train_loss:.4f} | "
            f"val_f1={val_metrics['f1']:.4f} | val_acc={val_metrics['accuracy']:.4f}"
        )

        if trial is not None:
            trial.report(float(val_metrics["f1"]), step=epoch)
            if trial.should_prune():
                raise optuna.TrialPruned()

        if val_metrics["f1"] > best_score:
            best_score = float(val_metrics["f1"])
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= int(settings["early_stopping_patience"]):
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Praxisv03 sequence-model training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


def create_study(settings: dict[str, Any], suffix: str) -> optuna.Study:
    seed = v02.stable_seed(int(settings["random_seed"]), suffix)
    sampler = optuna.samplers.TPESampler(seed=seed, multivariate=True)
    pruner = optuna.pruners.HyperbandPruner(
        min_resource=max(1, int(settings["train_epochs"]) // 10),
        max_resource=max(1, int(settings["train_epochs"])),
    )
    return optuna.create_study(direction="maximize", sampler=sampler, pruner=pruner)


def suggest_graph_params_v03(trial: optuna.Trial, model_name: str) -> dict[str, Any]:
    hidden_dim_choices = [128, 256] if model_name == "GCN-DGI" else [64, 128, 256]
    params = {
        "hidden_dim": trial.suggest_categorical("hidden_dim", hidden_dim_choices),
        "dropout": trial.suggest_float("dropout", 0.2, 0.5),
        "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 5e-3, log=True),
    }
    if model_name == "GATv2":
        params["heads"] = trial.suggest_categorical("heads", [4, 8])
        params["attention_dropout"] = trial.suggest_float("attention_dropout", 0.0, 0.3)
    if model_name == "ST-GCN":
        params["num_st_blocks"] = trial.suggest_int("num_st_blocks", 2, 3)
    return params


def suggest_mlp_params_v03(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "hidden_dim": trial.suggest_categorical("hidden_dim", [128, 256, 512]),
        "num_layers": trial.suggest_int("num_layers", 2, 4),
        "dropout": trial.suggest_float("dropout", 0.1, 0.4),
        "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }


def suggest_mamba_params_v03(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "d_model": trial.suggest_categorical("d_model", [64, 96, 128]),
        "n_layers": trial.suggest_int("n_layers", 2, 4),
        "d_state": trial.suggest_categorical("d_state", [8, 16]),
        "d_conv": trial.suggest_categorical("d_conv", [4, 8]),
        "dropout": trial.suggest_float("dropout", 0.1, 0.35),
        "lr": trial.suggest_float("lr", 1e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }


def optimize_graph_model_v03(
    model_name: str,
    train_graphs,
    val_graphs,
    settings: dict[str, Any],
    device: torch.device,
    gml: Any,
    pretrained_encoder: Any = None,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_labels = np.concatenate([graph.y.cpu().numpy() for graph in train_graphs]).astype(np.int64)
    train_sampler = build_graph_sampler(train_graphs, train_labels=train_labels, settings=settings)
    train_loader = GraphDataLoader(
        train_graphs,
        batch_size=int(settings["graph_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
    )
    val_loader = GraphDataLoader(
        val_graphs,
        batch_size=int(settings["graph_batch_size"]),
        shuffle=False,
    )
    num_features = int(train_graphs[0].x.shape[1])

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []
    fixed_params = resolve_fixed_model_params(settings, model_name)

    def run_with_params(
        params: dict[str, Any],
        trial: optuna.Trial | None = None,
    ) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
        model = v02.instantiate_graph_model(
            model_name=model_name,
            num_features=num_features,
            params=params,
            gml=gml,
            pretrained_encoder=pretrained_encoder,
        )
        model, val_metrics, history = train_graph_model_v03(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            train_labels=train_labels,
            settings=settings,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            trial=trial,
        )
        return model, val_metrics, history

    if fixed_params is not None:
        print(f"Using fixed Praxisv03 parameters for graph model: {model_name}")
        model, val_metrics, history = run_with_params(fixed_params)
        return model, fixed_params, val_metrics, history

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_graph_params_v03(trial, model_name)
        try:
            model, val_metrics, history = run_with_params(params, trial=trial)
            score = float(val_metrics["f1"])
            if best_metrics is None or score > float(best_metrics["f1"]):
                best_model = model
                best_params = params
                best_metrics = val_metrics
                best_history = history
            return score
        finally:
            maybe_clear_device_cache()

    study = create_study(settings, f"graph:{model_name}")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
        gc_after_trial=True,
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError(f"Optuna did not produce a best Praxisv03 {model_name} model.")

    return best_model, best_params, best_metrics, best_history


def optimize_mlp_model_v03(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_cols: list[str],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_x, train_y = v02.build_row_arrays(train_df, feature_cols)
    val_x, val_y = v02.build_row_arrays(val_df, feature_cols)

    train_sampler = build_row_sampler(train_y, settings=settings)
    train_loader = DataLoader(
        v02.RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
    )
    val_loader = DataLoader(
        v02.RowDataset(val_x, val_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=False,
    )

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []
    fixed_params = resolve_fixed_model_params(settings, "MLP")

    def run_with_params(
        params: dict[str, Any],
        trial: optuna.Trial | None = None,
    ) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
        model = v02.MLPStageClassifier(
            num_features=len(feature_cols),
            hidden_dim=int(params["hidden_dim"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
            num_classes=len(STAGE_NAMES),
        )
        model, val_metrics, history = train_row_model_v03(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=train_y,
            device=device,
            settings=settings,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            trial=trial,
        )
        return model, val_metrics, history

    if fixed_params is not None:
        print("Using fixed Praxisv03 parameters for tabular model: MLP")
        model, val_metrics, history = run_with_params(fixed_params)
        return model, fixed_params, val_metrics, history

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_mlp_params_v03(trial)
        try:
            model, val_metrics, history = run_with_params(params, trial=trial)
            score = float(val_metrics["f1"])
            if best_metrics is None or score > float(best_metrics["f1"]):
                best_model = model
                best_params = params
                best_metrics = val_metrics
                best_history = history
            return score
        finally:
            maybe_clear_device_cache()

    study = create_study(settings, "mlp")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
        gc_after_trial=True,
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError("Optuna did not produce a best Praxisv03 MLP model.")

    return best_model, best_params, best_metrics, best_history


def optimize_mamba_model_v03(
    train_chunks: list[tuple[np.ndarray, np.ndarray]],
    val_chunks: list[tuple[np.ndarray, np.ndarray]],
    feature_cols: list[str],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_labels = np.concatenate([chunk[1] for chunk in train_chunks]).astype(np.int64)
    train_sampler = build_sequence_sampler(train_chunks, train_labels=train_labels, settings=settings)
    train_loader = DataLoader(
        v02.SequenceChunkDataset(train_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=train_sampler is None,
        sampler=train_sampler,
        collate_fn=v02.collate_sequence_chunks,
    )
    val_loader = DataLoader(
        v02.SequenceChunkDataset(val_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=False,
        collate_fn=v02.collate_sequence_chunks,
    )

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []
    fixed_params = resolve_fixed_model_params(settings, "Mamba")

    def run_with_params(
        params: dict[str, Any],
        trial: optuna.Trial | None = None,
    ) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
        model = v02.MambaStageClassifier(
            num_features=len(feature_cols),
            d_model=int(params["d_model"]),
            n_layers=int(params["n_layers"]),
            d_state=int(params["d_state"]),
            d_conv=int(params["d_conv"]),
            dropout=float(params["dropout"]),
            num_classes=len(STAGE_NAMES),
        )
        model, val_metrics, history = train_sequence_model_v03(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=train_labels,
            device=device,
            settings=settings,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            trial=trial,
        )
        return model, val_metrics, history

    if fixed_params is not None:
        print("Using fixed Praxisv03 parameters for sequence model: Mamba")
        model, val_metrics, history = run_with_params(fixed_params)
        return model, fixed_params, val_metrics, history

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_mamba_params_v03(trial)
        try:
            model, val_metrics, history = run_with_params(params, trial=trial)
            score = float(val_metrics["f1"])
            if best_metrics is None or score > float(best_metrics["f1"]):
                best_model = model
                best_params = params
                best_metrics = val_metrics
                best_history = history
            return score
        finally:
            maybe_clear_device_cache()

    study = create_study(settings, "mamba")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
        gc_after_trial=True,
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError("Optuna did not produce a best Praxisv03 Mamba model.")

    return best_model, best_params, best_metrics, best_history


def save_metrics_table(run_dir: Path, results: dict[str, Any]) -> None:
    rows = []
    for model_name, payload in results.items():
        test_metrics = payload["test_metrics"]
        rows.append(
            {
                "model": model_name,
                "accuracy": test_metrics["accuracy"],
                "precision": test_metrics["precision"],
                "recall": test_metrics["recall"],
                "f1": test_metrics["f1"],
                "roc_auc": test_metrics["roc_auc"],
                "pr_auc": test_metrics["pr_auc"],
            }
        )

    metrics_df = pd.DataFrame(rows)
    if not metrics_df.empty:
        metrics_df = metrics_df.sort_values("f1", ascending=False)
    metrics_df.to_csv(run_dir / "metrics-table.csv", index=False)
    v02.write_json(run_dir / "metrics-table.json", {"rows": metrics_df.to_dict(orient="records")})


def save_per_class_metrics(run_dir: Path, results: dict[str, Any]) -> None:
    rows: list[dict[str, Any]] = []
    for model_name, payload in results.items():
        confusion = np.asarray(payload["test_metrics"]["confusion_matrix"], dtype=np.int64)
        for class_index, stage_name in enumerate(STAGE_NAMES):
            support = int(confusion[class_index].sum())
            true_positive = int(confusion[class_index, class_index])
            predicted = int(confusion[:, class_index].sum())
            precision = true_positive / predicted if predicted else 0.0
            recall = true_positive / support if support else 0.0
            f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
            rows.append(
                {
                    "model": model_name,
                    "stage": stage_name,
                    "support": support,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1,
                }
            )

    per_class_df = pd.DataFrame(rows)
    per_class_df.to_csv(run_dir / "per-class-metrics.csv", index=False)
    v02.write_json(run_dir / "per-class-metrics.json", {"rows": per_class_df.to_dict(orient="records")})


def result_path_for_model(run_dir: Path, model_name: str) -> Path:
    return run_dir / f"{model_name.lower().replace('-', '_')}_results.json"


def checkpoint_path_for_model(run_dir: Path, model_name: str) -> Path:
    return run_dir / f"{model_name.lower().replace('-', '_')}_state_dict.pt"


def save_model_checkpoint(run_dir: Path, model_name: str, model: nn.Module) -> Path:
    checkpoint_path = checkpoint_path_for_model(run_dir, model_name)
    torch.save(model.state_dict(), checkpoint_path)
    return checkpoint_path


def load_existing_results(run_dir: Path, model_names: list[str]) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for model_name in model_names:
        path = result_path_for_model(run_dir, model_name)
        if not path.exists():
            continue
        results[model_name] = json.loads(path.read_text(encoding="utf-8"))
    return results


def run_unraveled_v03(settings: dict[str, Any]) -> Path:
    repo_root = v02.resolve_repo_root()
    merged = dict(DEFAULTS)
    merged.update(settings)

    if bool(merged["include_cover_up"]):
        raise ValueError("Praxisv03 currently benchmarks the 5 stable Unraveled stages and excludes Cover up.")

    graph_models, tabular_models = resolve_enabled_models(merged)
    run_dir = v02.resolve_path(repo_root, merged["output_dir"]) / merged["run_name"]
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": merged,
        "environment": v02.detect_environment(),
        "enabled_models": {
            "graph_models": graph_models,
            "tabular_models": tabular_models,
        },
    }
    v02.write_json(run_dir / "metadata.json", metadata)

    v02.set_random_seed(int(merged["random_seed"]))
    device = v02.choose_device(bool(merged["force_cpu"]))
    print(f"Praxisv03 device: {device}")

    gml = v02.load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = v02.load_or_build_cache(merged, repo_root)
    v02.write_json(
        run_dir / "cache-summary.json",
        {
            "cache_path": cache_path,
            "cache_metadata_path": cache_metadata_path,
            "rows": int(len(df)),
            "stage_counts": cache_metadata.get("stage_counts", {}),
        },
    )

    train_df, val_df, test_df, feature_cols, preprocess_summary = prepare_features_and_splits_v03(
        df=df,
        settings=merged,
        gml=gml,
        run_dir=run_dir,
    )

    results: dict[str, Any] = {}
    if bool(merged.get("resume_existing_results")):
        results.update(load_existing_results(run_dir, ALL_MODEL_NAMES))
        if results:
            print(
                "Resuming Praxisv03 run with existing model artifacts: "
                + ", ".join(sorted(results))
            )

    for model_name in graph_models:
        if model_name in results:
            print(f"Skipping Praxisv03 graph model already on disk: {model_name}")
            continue
        print(f"\n{'=' * 80}")
        print(f"Praxisv03 graph model: {model_name}")
        print(f"{'=' * 80}")

        train_graphs = v02.build_graphs_for_frame(
            df=train_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(merged["flows_per_graph"]),
            min_graph_size=int(merged["min_graph_size"]),
            graph_k=int(merged["graph_k"]),
            stgcn_temporal_k=int(merged["stgcn_temporal_k"]),
            gml=gml,
        )
        val_graphs = v02.build_graphs_for_frame(
            df=val_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(merged["flows_per_graph"]),
            min_graph_size=int(merged["min_graph_size"]),
            graph_k=int(merged["graph_k"]),
            stgcn_temporal_k=int(merged["stgcn_temporal_k"]),
            gml=gml,
        )
        test_graphs = v02.build_graphs_for_frame(
            df=test_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(merged["flows_per_graph"]),
            min_graph_size=int(merged["min_graph_size"]),
            graph_k=int(merged["graph_k"]),
            stgcn_temporal_k=int(merged["stgcn_temporal_k"]),
            gml=gml,
        )

        if not train_graphs or not val_graphs or not test_graphs:
            raise RuntimeError(f"{model_name} graph construction produced an empty split.")

        pretrained_encoder = None
        if model_name == "GCN-DGI" and bool(merged["run_dgi_pretraining"]):
            dgi_loader = GraphDataLoader(
                train_graphs,
                batch_size=int(merged["graph_batch_size"]),
                shuffle=True,
            )
            pretrained_encoder = gml.pretrain_with_dgi(
                train_loader=dgi_loader,
                num_features=int(train_graphs[0].x.shape[1]),
                device=device,
                hidden_dim=128,
                epochs=int(merged["dgi_pretrain_epochs"]),
                verbose=True,
            )

        best_model, best_params, val_metrics, history = optimize_graph_model_v03(
            model_name=model_name,
            train_graphs=train_graphs,
            val_graphs=val_graphs,
            settings=merged,
            device=device,
            gml=gml,
            pretrained_encoder=pretrained_encoder,
        )

        test_loader = GraphDataLoader(
            test_graphs,
            batch_size=int(merged["graph_batch_size"]),
            shuffle=False,
        )
        test_metrics = v02.evaluate_graph_model(best_model, test_loader, device)
        checkpoint_path = save_model_checkpoint(run_dir, model_name, best_model)
        results[model_name] = {
            "best_params": best_params,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "history": history,
            "checkpoint_path": str(checkpoint_path),
            "graph_counts": {
                "train": len(train_graphs),
                "val": len(val_graphs),
                "test": len(test_graphs),
            },
        }
        v02.write_json(result_path_for_model(run_dir, model_name), results[model_name])

    if "MLP" in tabular_models:
        if "MLP" in results:
            print("Skipping Praxisv03 tabular model already on disk: MLP")
        else:
            print(f"\n{'=' * 80}")
            print("Praxisv03 tabular model: MLP")
            print(f"{'=' * 80}")
            mlp_model, best_params, val_metrics, history = optimize_mlp_model_v03(
                train_df=train_df,
                val_df=val_df,
                feature_cols=feature_cols,
                settings=merged,
                device=device,
            )
            test_x, test_y = v02.build_row_arrays(test_df, feature_cols)
            test_loader = DataLoader(
                v02.RowDataset(test_x, test_y),
                batch_size=int(merged["tabular_batch_size"]),
                shuffle=False,
            )
            test_metrics = v02.evaluate_row_model(mlp_model, test_loader, device)
            checkpoint_path = save_model_checkpoint(run_dir, "MLP", mlp_model)
            results["MLP"] = {
                "best_params": best_params,
                "val_metrics": val_metrics,
                "test_metrics": test_metrics,
                "history": history,
                "checkpoint_path": str(checkpoint_path),
                "row_counts": {
                    "train": int(len(train_df)),
                    "val": int(len(val_df)),
                    "test": int(len(test_df)),
                },
            }
            v02.write_json(result_path_for_model(run_dir, "MLP"), results["MLP"])

    if "Mamba" in tabular_models:
        if "Mamba" in results:
            print("Skipping Praxisv03 sequence model already on disk: Mamba")
        else:
            print(f"\n{'=' * 80}")
            print("Praxisv03 sequence model: Mamba")
            print(f"{'=' * 80}")

            train_chunks = v02.build_sequence_chunks(
                train_df,
                feature_cols=feature_cols,
                sequence_length=int(merged["sequence_length"]),
                min_sequence_length=int(merged["min_sequence_length"]),
            )
            val_chunks = v02.build_sequence_chunks(
                val_df,
                feature_cols=feature_cols,
                sequence_length=int(merged["sequence_length"]),
                min_sequence_length=int(merged["min_sequence_length"]),
            )
            test_chunks = v02.build_sequence_chunks(
                test_df,
                feature_cols=feature_cols,
                sequence_length=int(merged["sequence_length"]),
                min_sequence_length=int(merged["min_sequence_length"]),
            )

            if not train_chunks or not val_chunks or not test_chunks:
                raise RuntimeError("Mamba sequence chunking produced an empty split.")

            mamba_model, best_params, val_metrics, history = optimize_mamba_model_v03(
                train_chunks=train_chunks,
                val_chunks=val_chunks,
                feature_cols=feature_cols,
                settings=merged,
                device=device,
            )
            test_loader = DataLoader(
                v02.SequenceChunkDataset(test_chunks),
                batch_size=int(merged["sequence_batch_size"]),
                shuffle=False,
                collate_fn=v02.collate_sequence_chunks,
            )
            test_metrics = v02.evaluate_sequence_model(mamba_model, test_loader, device)
            checkpoint_path = save_model_checkpoint(run_dir, "Mamba", mamba_model)
            results["Mamba"] = {
                "best_params": best_params,
                "val_metrics": val_metrics,
                "test_metrics": test_metrics,
                "history": history,
                "checkpoint_path": str(checkpoint_path),
                "sequence_counts": {
                    "train": len(train_chunks),
                    "val": len(val_chunks),
                    "test": len(test_chunks),
                },
            }
            v02.write_json(result_path_for_model(run_dir, "Mamba"), results["Mamba"])

    save_metrics_table(run_dir, results)
    save_per_class_metrics(run_dir, results)

    summary = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": merged["pipeline"],
        "run_name": merged["run_name"],
        "device": str(device),
        "cache_path": cache_path,
        "feature_count": preprocess_summary["feature_count"],
        "results": results,
    }
    v02.write_json(run_dir / "results-summary.json", summary)
    return run_dir
