from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import platform
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import pandas as pd
import torch
import torch.nn as nn
from mambapy.mamba import Mamba, MambaConfig
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import RobustScaler, StandardScaler, label_binarize
from torch.utils.data import DataLoader, Dataset
from torch_geometric.loader import DataLoader as GraphDataLoader


STAGE_NAMES = [
    "Benign",
    "Reconnaissance",
    "Establish Foothold",
    "Lateral Movement",
    "Data Exfiltration",
]

STAGE_TO_LABEL = {
    "benign": 0,
    "reconnaissance": 1,
    "establish foothold": 2,
    "lateral movement": 3,
    "data exfiltration": 4,
}

ALLOWED_STAGE_LABELS = set(STAGE_TO_LABEL)

RAW_STRING_COLUMNS = [
    "application_name",
    "application_category_name",
    "requested_server_name",
    "content_type",
]

ALWAYS_EXCLUDE_FEATURE_COLUMNS = {
    "Signature",
    "user_agent",
    "client_fingerprint",
    "server_fingerprint",
}

NUMERIC_EXCLUDE_COLUMNS = {
    "id",
    "expiration_id",
    "bidirectional_first_seen_ms",
    "bidirectional_last_seen_ms",
    "src2dst_first_seen_ms",
    "src2dst_last_seen_ms",
    "dst2src_first_seen_ms",
    "dst2src_last_seen_ms",
}

GRAPH_MODEL_NAMES = ["GATv2", "RGCN", "ST-GCN", "GIN", "GCN-DGI"]
TABULAR_MODEL_NAMES = ["MLP", "Mamba"]
ALL_MODEL_NAMES = GRAPH_MODEL_NAMES + TABULAR_MODEL_NAMES

DEFAULTS = {
    "pipeline": "unraveled_v02",
    "run_name": "praxisv02-unraveled-cpu",
    "output_dir": "runs",
    "notes": "Praxisv02 benchmark on Unraveled with 5 GNN models and a Mamba baseline.",
    "data_dir": "imports/unraveled/data/network-flows",
    "cache_dir": "data/processed/unraveled_v02",
    "cache_name": "benchmark_cache.csv",
    "cache_metadata_name": "benchmark_cache_metadata.json",
    "split_mode": "within_group_temporal",
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
    "feature_profile": "full",
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
    "train_epochs": 12,
    "dgi_pretrain_epochs": 8,
    "optuna_trials": 2,
    "optuna_timeout_seconds": None,
    "early_stopping_patience": 4,
    "run_dgi_pretraining": True,
    "force_cpu": True,
}


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def detect_environment() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
    }


def coerce_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): coerce_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [coerce_json(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(coerce_json(payload), indent=2), encoding="utf-8")


def load_gml_module(repo_root: Path):
    script_path = repo_root / "imports" / "gml_to_detect_apt_final" / "gml_to_detect_apt_final.py"
    if not script_path.exists():
        raise FileNotFoundError(f"Missing imported GML pipeline: {script_path}")

    spec = importlib.util.spec_from_file_location("praxis_gml_imported", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec from {script_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def set_random_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def choose_device(force_cpu: bool) -> torch.device:
    if force_cpu or not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device("cuda")


def normalize_stage(value: object) -> str | None:
    if pd.isna(value):
        return None
    stage = str(value).strip().lower()
    if stage in ALLOWED_STAGE_LABELS:
        return stage
    if stage == "cover up":
        return "cover up"
    return None


def normalize_text_value(value: object) -> str:
    if pd.isna(value):
        return "<na>"
    text = str(value).strip().lower()
    return text if text else "<na>"


def stable_seed(base_seed: int, value: str) -> int:
    digest = hashlib.sha256(f"{base_seed}:{value}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16) % (2**31 - 1)


def normalize_stage_key(value: object) -> str:
    return "".join(character for character in str(value).strip().lower() if character.isalnum())


def infer_sensor(path: Path) -> str:
    return path.name.split("_")[0].lower()


def infer_numeric_feature_columns(df: pd.DataFrame) -> list[str]:
    numeric_cols: list[str] = []
    for column in df.columns:
        if not pd.api.types.is_numeric_dtype(df[column]):
            continue
        if column in NUMERIC_EXCLUDE_COLUMNS or column == "MultiLabel":
            continue
        numeric_cols.append(column)
    return numeric_cols


def load_single_unraveled_file(
    path: Path,
    base_seed: int,
    benign_keep_rate: float,
    min_benign_per_file: int,
    include_cover_up: bool,
) -> pd.DataFrame:
    df = pd.read_csv(path, engine="python", on_bad_lines="skip")
    df["StageClean"] = df["Stage"].apply(normalize_stage)

    allowed = ALLOWED_STAGE_LABELS | ({"cover up"} if include_cover_up else set())
    df = df[df["StageClean"].isin(allowed)].copy()
    if df.empty:
        return df

    df["sensor"] = infer_sensor(path)
    df["source_file"] = str(path.relative_to(path.parents[1])).replace("\\", "/")
    df["capture_day"] = path.parent.name
    df["timestamp_sort"] = pd.to_datetime(
        df["bidirectional_first_seen_ms"], unit="ms", errors="coerce", utc=True
    ).dt.tz_convert(None)
    df = df.dropna(subset=["timestamp_sort"]).copy()
    df["Src IP"] = df["src_ip"].astype(str)
    df["Dst IP"] = df["dst_ip"].astype(str)

    if not include_cover_up:
        df = df[df["StageClean"] != "cover up"].copy()

    df["MultiLabel"] = df["StageClean"].map(STAGE_TO_LABEL)
    df = df.dropna(subset=["MultiLabel"]).copy()
    df["MultiLabel"] = df["MultiLabel"].astype(np.int64)

    benign_mask = df["MultiLabel"] == 0
    attack_df = df.loc[~benign_mask].copy()
    benign_df = df.loc[benign_mask].copy()

    if benign_keep_rate < 1.0 and len(benign_df) > 0:
        sample_size = max(min_benign_per_file, int(round(len(benign_df) * benign_keep_rate)))
        sample_size = min(sample_size, len(benign_df))
        benign_df = benign_df.sample(
            n=sample_size,
            random_state=stable_seed(base_seed, str(path)),
        )

    keep_columns = [
        "source_file",
        "capture_day",
        "sensor",
        "timestamp_sort",
        "StageClean",
        "MultiLabel",
        "Src IP",
        "Dst IP",
    ]

    combined = pd.concat([attack_df, benign_df], ignore_index=True)
    if combined.empty:
        return combined

    for column in RAW_STRING_COLUMNS:
        if column in combined.columns:
            keep_columns.append(column)

    numeric_columns = infer_numeric_feature_columns(combined)
    keep_columns.extend(column for column in numeric_columns if column not in keep_columns)
    combined = combined[keep_columns].sort_values("timestamp_sort").reset_index(drop=True)

    combined["has_requested_server_name"] = (
        combined["requested_server_name"].apply(normalize_text_value) != "<na>"
        if "requested_server_name" in combined.columns
        else 0
    ).astype(np.float32)
    combined["has_content_type"] = (
        combined["content_type"].apply(normalize_text_value) != "<na>"
        if "content_type" in combined.columns
        else 0
    ).astype(np.float32)
    combined["is_gateway"] = (combined["sensor"] == "netgw").astype(np.float32)
    return combined


def build_unraveled_cache(
    settings: dict[str, Any],
    data_dir: Path,
    cache_path: Path,
    cache_metadata_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    paths = sorted(data_dir.rglob("*_Flow_labeled.csv"))
    if settings.get("max_files"):
        paths = paths[: int(settings["max_files"])]

    frames: list[pd.DataFrame] = []
    file_summaries: list[dict[str, Any]] = []

    for index, path in enumerate(paths, start=1):
        frame = load_single_unraveled_file(
            path=path,
            base_seed=int(settings["random_seed"]),
            benign_keep_rate=float(settings["benign_keep_rate"]),
            min_benign_per_file=int(settings["min_benign_per_file"]),
            include_cover_up=bool(settings["include_cover_up"]),
        )
        if frame.empty:
            continue

        frames.append(frame)
        stage_counts = frame["StageClean"].value_counts().sort_index().to_dict()
        file_summaries.append(
            {
                "path": str(path),
                "rows_kept": int(len(frame)),
                "stage_counts": {str(key): int(value) for key, value in stage_counts.items()},
            }
        )

        if index % 25 == 0:
            print(f"  Cached {index}/{len(paths)} files...")

    if not frames:
        raise ValueError("No Unraveled rows were loaded into the Praxisv02 benchmark cache.")

    df = pd.concat(frames, ignore_index=True)
    df.sort_values("timestamp_sort", inplace=True)
    df.reset_index(drop=True, inplace=True)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache_path, index=False)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": settings,
        "rows": int(len(df)),
        "columns": df.columns.tolist(),
        "stage_counts": {
            str(key): int(value)
            for key, value in df["StageClean"].value_counts().sort_index().to_dict().items()
        },
        "file_count": len(file_summaries),
        "files": file_summaries,
    }
    write_json(cache_metadata_path, metadata)
    return df, metadata


def load_or_build_cache(
    settings: dict[str, Any],
    repo_root: Path,
) -> tuple[pd.DataFrame, dict[str, Any], Path, Path]:
    cache_dir = resolve_path(repo_root, settings["cache_dir"])
    cache_path = cache_dir / settings["cache_name"]
    cache_metadata_path = cache_dir / settings["cache_metadata_name"]
    data_dir = resolve_path(repo_root, settings["data_dir"])

    if cache_path.exists() and cache_metadata_path.exists() and not settings.get("force_rebuild_cache"):
        metadata = json.loads(cache_metadata_path.read_text(encoding="utf-8"))
        cached_settings = metadata.get("settings", {})
        relevant_keys = [
            "data_dir",
            "max_files",
            "include_cover_up",
            "benign_keep_rate",
            "min_benign_per_file",
        ]
        if all(cached_settings.get(key) == settings.get(key) for key in relevant_keys):
            print(f"Using cached Praxisv02 benchmark: {cache_path}")
            df = pd.read_csv(cache_path, parse_dates=["timestamp_sort"], low_memory=False)
            return df, metadata, cache_path, cache_metadata_path
        print("Existing Praxisv02 cache settings do not match this run. Rebuilding cache...")

    print("Building Praxisv02 Unraveled benchmark cache from local CSV files...")
    df, metadata = build_unraveled_cache(settings, data_dir, cache_path, cache_metadata_path)
    return df, metadata, cache_path, cache_metadata_path


def split_within_group_temporal(
    df: pd.DataFrame,
    group_col: str,
    val_size: float,
    test_size: float,
    split_blocks: int,
    gml: Any,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered_groups = df.groupby(group_col)["timestamp_sort"].min().sort_values().index.tolist()
    train_frames: list[pd.DataFrame] = []
    val_frames: list[pd.DataFrame] = []
    test_frames: list[pd.DataFrame] = []

    print(f"\nSplitting Praxisv02 benchmark by `{group_col}`...")
    for group_name in ordered_groups:
        group_df = (
            df[df[group_col] == group_name]
            .sort_values("timestamp_sort")
            .reset_index(drop=True)
        )
        group_train, group_val, group_test = gml._hybrid_stratified_split_three_way(
            group_df,
            val_size=val_size,
            test_size=test_size,
            n_blocks=split_blocks,
        )
        train_frames.append(group_train)
        val_frames.append(group_val)
        test_frames.append(group_test)

    train_df = pd.concat(train_frames, ignore_index=True).sort_values("timestamp_sort").reset_index(drop=True)
    val_df = pd.concat(val_frames, ignore_index=True).sort_values("timestamp_sort").reset_index(drop=True)
    test_df = pd.concat(test_frames, ignore_index=True).sort_values("timestamp_sort").reset_index(drop=True)
    return train_df, val_df, test_df


def split_by_group_holdout(
    df: pd.DataFrame,
    group_col: str,
    val_size: float,
    test_size: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    group_stats = (
        df.groupby(group_col)
        .agg(
            first_timestamp=("timestamp_sort", "min"),
            rows=("MultiLabel", "size"),
        )
        .sort_values("first_timestamp")
    )

    groups = group_stats.index.tolist()
    total_rows = int(group_stats["rows"].sum())
    val_target = total_rows * val_size
    test_target = total_rows * test_size

    test_groups: list[str] = []
    val_groups: list[str] = []
    train_groups: list[str] = []
    test_rows = 0
    val_rows = 0

    for group_name in reversed(groups):
        rows = int(group_stats.loc[group_name, "rows"])
        if test_rows < test_target or not test_groups:
            test_groups.append(group_name)
            test_rows += rows
            continue
        if val_rows < val_target or not val_groups:
            val_groups.append(group_name)
            val_rows += rows
            continue
        train_groups.append(group_name)

    if not train_groups:
        raise ValueError(f"Strict holdout on `{group_col}` left no training groups.")

    train_df = (
        df[df[group_col].isin(train_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    val_df = (
        df[df[group_col].isin(val_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    test_df = (
        df[df[group_col].isin(test_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    return train_df, val_df, test_df


def parse_holdout_stage_support_floor(
    raw: Any,
) -> dict[str, np.ndarray] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("holdout_min_stage_support must be a mapping of split names to stage floors.")

    floors = {
        "train": np.zeros(len(STAGE_NAMES), dtype=np.int64),
        "val": np.zeros(len(STAGE_NAMES), dtype=np.int64),
        "test": np.zeros(len(STAGE_NAMES), dtype=np.int64),
    }
    stage_name_to_index = {
        normalize_stage_key(stage_name): index for index, stage_name in enumerate(STAGE_NAMES)
    }

    for split_key, split_payload in raw.items():
        split_name = str(split_key).strip().lower()
        if split_name not in floors:
            raise ValueError(
                "holdout_min_stage_support keys must be train, val, or test. "
                f"Got: {split_key}"
            )
        if not isinstance(split_payload, dict):
            raise ValueError(
                f"holdout_min_stage_support[{split_key!r}] must be a mapping of stage names to counts."
            )

        for stage_key, value in split_payload.items():
            if isinstance(stage_key, int):
                stage_index = stage_key
            else:
                key_text = str(stage_key).strip()
                if key_text.isdigit():
                    stage_index = int(key_text)
                else:
                    normalized = normalize_stage_key(key_text)
                    if normalized not in stage_name_to_index:
                        raise ValueError(
                            f"Unknown stage in holdout_min_stage_support[{split_key!r}]: {stage_key}"
                        )
                    stage_index = stage_name_to_index[normalized]

            if stage_index < 0 or stage_index >= len(STAGE_NAMES):
                raise ValueError(
                    f"Stage index out of range in holdout_min_stage_support[{split_key!r}]: {stage_index}"
                )

            floors[split_name][stage_index] = int(value)

    return floors


def split_by_group_holdout_support_aware(
    df: pd.DataFrame,
    group_col: str,
    val_size: float,
    test_size: float,
    stage_support_floor: dict[str, np.ndarray],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    group_stats = (
        df.groupby(group_col)
        .agg(
            first_timestamp=("timestamp_sort", "min"),
            rows=("MultiLabel", "size"),
        )
        .sort_values("first_timestamp")
    )
    stage_counts = df.groupby([group_col, "MultiLabel"]).size().unstack(fill_value=0)
    for stage_index in range(len(STAGE_NAMES)):
        if stage_index not in stage_counts.columns:
            stage_counts[stage_index] = 0
    group_stats = group_stats.join(stage_counts[[stage_index for stage_index in range(len(STAGE_NAMES))]])

    groups = group_stats.index.tolist()
    if len(groups) < 3:
        raise ValueError(f"Strict holdout on `{group_col}` requires at least 3 groups.")

    rows_arr = group_stats["rows"].to_numpy(dtype=np.int64)
    stage_arr = group_stats[[stage_index for stage_index in range(len(STAGE_NAMES))]].to_numpy(dtype=np.int64)
    total_rows = int(rows_arr.sum())
    row_targets = {
        "train": total_rows * max(1.0 - float(val_size) - float(test_size), 0.0),
        "val": total_rows * float(val_size),
        "test": total_rows * float(test_size),
    }

    prefix_rows = np.concatenate([[0], np.cumsum(rows_arr, dtype=np.int64)])
    prefix_stage = np.vstack(
        [
            np.zeros((1, len(STAGE_NAMES)), dtype=np.int64),
            np.cumsum(stage_arr, axis=0, dtype=np.int64),
        ]
    )

    best_candidate: dict[str, Any] | None = None
    valid_candidate_count = 0
    best_partial_candidate: dict[str, Any] | None = None

    def build_split_counts(start: int, end: int) -> np.ndarray:
        return prefix_stage[end] - prefix_stage[start]

    for train_end in range(1, len(groups) - 1):
        train_rows = int(prefix_rows[train_end])
        train_counts = build_split_counts(0, train_end)
        if np.any(train_counts < stage_support_floor["train"]):
            deficits = stage_support_floor["train"] - train_counts
            deficits = np.maximum(deficits, 0)
            partial_score = float(deficits.sum())
            if best_partial_candidate is None or partial_score < best_partial_candidate["deficit_score"]:
                best_partial_candidate = {
                    "train_end": train_end,
                    "val_end": train_end + 1,
                    "train_counts": train_counts.copy(),
                    "val_counts": np.zeros(len(STAGE_NAMES), dtype=np.int64),
                    "test_counts": np.zeros(len(STAGE_NAMES), dtype=np.int64),
                    "train_rows": train_rows,
                    "val_rows": 0,
                    "test_rows": 0,
                    "deficit_score": partial_score,
                }
            continue

        for val_end in range(train_end + 1, len(groups)):
            val_rows_count = int(prefix_rows[val_end] - prefix_rows[train_end])
            test_rows_count = int(prefix_rows[len(groups)] - prefix_rows[val_end])
            if val_rows_count <= 0 or test_rows_count <= 0:
                continue

            val_counts = build_split_counts(train_end, val_end)
            test_counts = build_split_counts(val_end, len(groups))
            split_counts = {
                "train": train_counts,
                "val": val_counts,
                "test": test_counts,
            }
            if any(np.any(split_counts[split_name] < stage_support_floor[split_name]) for split_name in split_counts):
                deficits = {
                    split_name: np.maximum(stage_support_floor[split_name] - split_counts[split_name], 0)
                    for split_name in split_counts
                }
                deficit_score = float(sum(deficit.sum() for deficit in deficits.values()))
                if (
                    best_partial_candidate is None
                    or deficit_score < best_partial_candidate["deficit_score"]
                ):
                    best_partial_candidate = {
                        "train_end": train_end,
                        "val_end": val_end,
                        "train_counts": train_counts.copy(),
                        "val_counts": val_counts.copy(),
                        "test_counts": test_counts.copy(),
                        "train_rows": train_rows,
                        "val_rows": val_rows_count,
                        "test_rows": test_rows_count,
                        "deficit_score": deficit_score,
                    }
                continue

            valid_candidate_count += 1
            row_counts = {
                "train": train_rows,
                "val": val_rows_count,
                "test": test_rows_count,
            }
            row_score = sum(
                abs(row_counts[split_name] - row_targets[split_name]) / max(row_targets[split_name], 1.0)
                for split_name in ("train", "val", "test")
            )
            if best_candidate is None or row_score < best_candidate["row_score"]:
                best_candidate = {
                    "train_end": train_end,
                    "val_end": val_end,
                    "row_score": float(row_score),
                    "train_rows": train_rows,
                    "val_rows": val_rows_count,
                    "test_rows": test_rows_count,
                    "train_counts": train_counts.copy(),
                    "val_counts": val_counts.copy(),
                    "test_counts": test_counts.copy(),
                }

    if best_candidate is None:
        details = {}
        if best_partial_candidate is not None:
            details = {
                "closest_candidate_rows": {
                    "train": int(best_partial_candidate["train_rows"]),
                    "val": int(best_partial_candidate["val_rows"]),
                    "test": int(best_partial_candidate["test_rows"]),
                },
                "closest_candidate_counts": {
                    "train": {
                        STAGE_NAMES[idx]: int(best_partial_candidate["train_counts"][idx])
                        for idx in range(len(STAGE_NAMES))
                    },
                    "val": {
                        STAGE_NAMES[idx]: int(best_partial_candidate["val_counts"][idx])
                        for idx in range(len(STAGE_NAMES))
                    },
                    "test": {
                        STAGE_NAMES[idx]: int(best_partial_candidate["test_counts"][idx])
                        for idx in range(len(STAGE_NAMES))
                    },
                },
                "deficit_score": float(best_partial_candidate["deficit_score"]),
            }
        raise ValueError(
            f"Could not find a strict holdout split on `{group_col}` that satisfies "
            f"holdout_min_stage_support. Details: {details}"
        )

    train_groups = groups[: best_candidate["train_end"]]
    val_groups = groups[best_candidate["train_end"] : best_candidate["val_end"]]
    test_groups = groups[best_candidate["val_end"] :]

    train_df = (
        df[df[group_col].isin(train_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    val_df = (
        df[df[group_col].isin(val_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )
    test_df = (
        df[df[group_col].isin(test_groups)]
        .sort_values("timestamp_sort")
        .reset_index(drop=True)
    )

    summary = {
        "group_col": group_col,
        "candidate_count": int(valid_candidate_count),
        "row_targets": {split_name: int(round(row_targets[split_name])) for split_name in row_targets},
        "rows_per_split": {
            "train": int(best_candidate["train_rows"]),
            "val": int(best_candidate["val_rows"]),
            "test": int(best_candidate["test_rows"]),
        },
        "groups_per_split": {
            "train": int(len(train_groups)),
            "val": int(len(val_groups)),
            "test": int(len(test_groups)),
        },
        "row_score": float(best_candidate["row_score"]),
        "stage_support_floor": {
            split_name: {
                STAGE_NAMES[idx]: int(stage_support_floor[split_name][idx])
                for idx in range(len(STAGE_NAMES))
            }
            for split_name in ("train", "val", "test")
        },
        "stage_counts": {
            "train": {
                STAGE_NAMES[idx]: int(best_candidate["train_counts"][idx])
                for idx in range(len(STAGE_NAMES))
            },
            "val": {
                STAGE_NAMES[idx]: int(best_candidate["val_counts"][idx])
                for idx in range(len(STAGE_NAMES))
            },
            "test": {
                STAGE_NAMES[idx]: int(best_candidate["test_counts"][idx])
                for idx in range(len(STAGE_NAMES))
            },
        },
        "split_groups": {
            "train": [str(item) for item in train_groups],
            "val": [str(item) for item in val_groups],
            "test": [str(item) for item in test_groups],
        },
    }
    return train_df, val_df, test_df, summary


def add_frequency_features(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    feature_profile: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], dict[str, dict[str, int]]]:
    encodings: dict[str, dict[str, int]] = {}
    updated_feature_cols = list(feature_cols)

    for column in RAW_STRING_COLUMNS:
        if column not in train_df.columns:
            continue

        if feature_profile == "clean":
            train_df.drop(columns=[column], inplace=True)
            val_df.drop(columns=[column], inplace=True)
            test_df.drop(columns=[column], inplace=True)
            continue

        train_norm = train_df[column].apply(normalize_text_value)
        val_norm = val_df[column].apply(normalize_text_value)
        test_norm = test_df[column].apply(normalize_text_value)

        counts = train_norm.value_counts().to_dict()
        encodings[column] = {str(key): int(value) for key, value in counts.items()}

        feature_name = f"{column}_freq"
        train_df[feature_name] = train_norm.map(lambda value: np.log1p(counts.get(value, 0))).astype(np.float32)
        val_df[feature_name] = val_norm.map(lambda value: np.log1p(counts.get(value, 0))).astype(np.float32)
        test_df[feature_name] = test_norm.map(lambda value: np.log1p(counts.get(value, 0))).astype(np.float32)
        updated_feature_cols.append(feature_name)

        train_df.drop(columns=[column], inplace=True)
        val_df.drop(columns=[column], inplace=True)
        test_df.drop(columns=[column], inplace=True)

    for binary_column in ["has_requested_server_name", "has_content_type", "is_gateway"]:
        if binary_column in train_df.columns and binary_column not in updated_feature_cols:
            updated_feature_cols.append(binary_column)

    return train_df, val_df, test_df, updated_feature_cols, encodings


def select_feature_columns(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: list[str],
    settings: dict[str, Any],
) -> tuple[list[str], dict[str, str]]:
    selected: list[str] = []
    dropped: dict[str, str] = {}
    max_missing_fraction = float(settings.get("max_missing_fraction", 0.98))

    for column in feature_cols:
        if column in ALWAYS_EXCLUDE_FEATURE_COLUMNS:
            dropped[column] = "explicit_exclude"
            continue

        if column not in train_df.columns:
            dropped[column] = "missing_after_preprocessing"
            continue

        series = pd.to_numeric(train_df[column], errors="coerce")
        missing_fraction = float(series.isna().mean())
        if missing_fraction >= max_missing_fraction:
            dropped[column] = f"missing_fraction={missing_fraction:.3f}"
            continue

        non_null = series.dropna()
        if non_null.empty or non_null.nunique() <= 1:
            dropped[column] = "constant_or_all_null"
            continue

        selected.append(column)

    return selected, dropped


def fit_scaler(name: str):
    if name == "standard":
        return StandardScaler()
    return RobustScaler(quantile_range=(10.0, 90.0))


def summarize_split(df: pd.DataFrame) -> dict[str, Any]:
    return {
        "rows": int(len(df)),
        "stage_counts": {
            STAGE_NAMES[idx]: int((df["MultiLabel"] == idx).sum())
            for idx in range(len(STAGE_NAMES))
        },
        "sensor_counts": {
            str(key): int(value)
            for key, value in df["sensor"].value_counts().sort_index().to_dict().items()
        },
        "capture_day_count": int(df["capture_day"].nunique()),
        "source_file_count": int(df["source_file"].nunique()),
    }


def prepare_features_and_splits(
    df: pd.DataFrame,
    settings: dict[str, Any],
    gml: Any,
    run_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[str], dict[str, Any]]:
    numeric_feature_cols = infer_numeric_feature_columns(df)
    split_mode = str(settings.get("split_mode", "within_group_temporal")).lower()
    holdout_support_floor = parse_holdout_stage_support_floor(
        settings.get("holdout_min_stage_support")
    )
    split_search_summary: dict[str, Any] | None = None
    if split_mode == "within_group_temporal":
        split_group_col = str(settings["split_group_col"])
        train_df, val_df, test_df = split_within_group_temporal(
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
            train_df, val_df, test_df = split_by_group_holdout(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
            )
        else:
            train_df, val_df, test_df, split_search_summary = split_by_group_holdout_support_aware(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
                stage_support_floor=holdout_support_floor,
            )
    elif split_mode == "held_out_source_file":
        split_group_col = "source_file"
        if holdout_support_floor is None:
            train_df, val_df, test_df = split_by_group_holdout(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
            )
        else:
            train_df, val_df, test_df, split_search_summary = split_by_group_holdout_support_aware(
                df=df,
                group_col=split_group_col,
                val_size=float(settings["val_size"]),
                test_size=float(settings["test_size"]),
                stage_support_floor=holdout_support_floor,
            )
    else:
        raise ValueError(f"Unsupported Praxisv02 split_mode: {split_mode}")

    train_df, val_df, test_df, feature_cols, encodings = add_frequency_features(
        train_df=train_df,
        val_df=val_df,
        test_df=test_df,
        feature_cols=numeric_feature_cols,
        feature_profile=str(settings.get("feature_profile", "full")).lower(),
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

    feature_cols, dropped_features = select_feature_columns(
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

    scaler = fit_scaler(str(settings["scaler"]).lower())
    train_df[feature_cols] = np.nan_to_num(scaler.fit_transform(train_df[feature_cols]), nan=0.0)
    val_df[feature_cols] = np.nan_to_num(scaler.transform(val_df[feature_cols]), nan=0.0)
    test_df[feature_cols] = np.nan_to_num(scaler.transform(test_df[feature_cols]), nan=0.0)

    preprocess_summary = {
        "split_mode": split_mode,
        "split_group_col": split_group_col,
        "feature_cols": feature_cols,
        "feature_count": len(feature_cols),
        "dropped_features": dropped_features,
        "feature_profile": str(settings.get("feature_profile", "full")).lower(),
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
            "train": summarize_split(train_df),
            "val": summarize_split(val_df),
            "test": summarize_split(test_df),
        },
        "group_overlap": {
            "train_val": int(len(set(train_df[split_group_col]) & set(val_df[split_group_col]))),
            "train_test": int(len(set(train_df[split_group_col]) & set(test_df[split_group_col]))),
            "val_test": int(len(set(val_df[split_group_col]) & set(test_df[split_group_col]))),
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
        preprocess_summary["strict_holdout_split"] = split_search_summary
    write_json(run_dir / "preprocess-summary.json", preprocess_summary)
    return train_df, val_df, test_df, feature_cols, preprocess_summary


def build_graphs_for_frame(
    df: pd.DataFrame,
    feature_cols: list[str],
    model_name: str,
    flows_per_graph: int,
    min_graph_size: int,
    graph_k: int,
    stgcn_temporal_k: int,
    gml: Any,
):
    graphs = []
    ordered_groups = df.groupby("source_file")["timestamp_sort"].min().sort_values().index.tolist()

    for source_file in ordered_groups:
        source_df = (
            df[df["source_file"] == source_file]
            .sort_values("timestamp_sort")
            .reset_index(drop=True)
        )
        for start in range(0, len(source_df), flows_per_graph):
            chunk = source_df.iloc[start : start + flows_per_graph].copy()
            if len(chunk) < min_graph_size:
                continue
            if model_name == "RGCN":
                graph = gml.build_graph_with_custom_k_rgcn(chunk, feature_cols, k=graph_k)
            elif model_name == "ST-GCN":
                graph = gml.build_graph_with_custom_k_stgnn(
                    chunk,
                    feature_cols,
                    k=graph_k,
                    temporal_k=stgcn_temporal_k,
                )
            else:
                graph = gml.build_graph_with_custom_k(chunk, feature_cols, k=graph_k)
            if graph is None:
                continue
            graph.source_file = source_file
            graphs.append(graph)

    return graphs


def graph_forward(model: nn.Module, batch) -> torch.Tensor:
    edge_type = getattr(batch, "edge_type", None)
    temporal_sort_order = getattr(batch, "temporal_sort_order", None)
    if edge_type is not None:
        return model(batch.x, batch.edge_index, batch.batch, edge_type=edge_type)
    if temporal_sort_order is not None:
        return model(
            batch.x,
            batch.edge_index,
            batch.batch,
            temporal_sort_order=temporal_sort_order,
        )
    return model(batch.x, batch.edge_index, batch.batch)


def compute_class_weights(labels: np.ndarray, num_classes: int) -> torch.Tensor:
    counts = np.bincount(labels, minlength=num_classes)
    counts = np.maximum(counts, 1)
    weights = counts.sum() / counts
    weights = weights / weights.mean()
    weights = np.clip(weights, 0.5, 8.0).astype(np.float32)
    return torch.tensor(weights, dtype=torch.float32)


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    probs: np.ndarray,
    class_names: list[str],
) -> dict[str, Any]:
    num_classes = len(class_names)
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=list(range(num_classes))).tolist(),
    }

    try:
        metrics["roc_auc"] = float(
            roc_auc_score(
                y_true,
                probs,
                multi_class="ovr",
                average="macro",
                labels=list(range(num_classes)),
            )
        )
    except Exception:
        metrics["roc_auc"] = None

    try:
        y_true_bin = label_binarize(y_true, classes=list(range(num_classes)))
        metrics["pr_auc"] = float(average_precision_score(y_true_bin, probs, average="macro"))
    except Exception:
        metrics["pr_auc"] = None

    metrics["per_class_support"] = {
        class_names[idx]: int((y_true == idx).sum()) for idx in range(num_classes)
    }
    return metrics


def evaluate_graph_model(
    model: nn.Module,
    loader: GraphDataLoader,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []

    with torch.no_grad():
        for batch in loader:
            batch = batch.to(device)
            logits = graph_forward(model, batch)
            probs = torch.softmax(logits, dim=1)
            preds.append(probs.argmax(dim=1).cpu().numpy())
            labels.append(batch.y.cpu().numpy())
            probs_list.append(probs.cpu().numpy())

    y_true = np.concatenate(labels)
    y_pred = np.concatenate(preds)
    probs = np.vstack(probs_list)
    return compute_metrics(y_true, y_pred, probs, STAGE_NAMES)


def train_graph_model(
    model: nn.Module,
    train_loader: GraphDataLoader,
    val_loader: GraphDataLoader,
    device: torch.device,
    train_labels: np.ndarray,
    lr: float,
    weight_decay: float,
    epochs: int,
    patience: int,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = nn.CrossEntropyLoss(
        weight=compute_class_weights(train_labels, num_classes=len(STAGE_NAMES)).to(device)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_examples = 0

        for batch in train_loader:
            batch = batch.to(device)
            optimizer.zero_grad()
            logits = graph_forward(model, batch)
            loss = criterion(logits, batch.y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * batch.y.numel()
            total_examples += int(batch.y.numel())

        val_metrics = evaluate_graph_model(model, val_loader, device)
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

        if val_metrics["f1"] > best_score:
            best_score = val_metrics["f1"]
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Graph model training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


class RowDataset(Dataset):
    def __init__(self, x: np.ndarray, y: np.ndarray):
        self.x = torch.from_numpy(x.astype(np.float32))
        self.y = torch.from_numpy(y.astype(np.int64))

    def __len__(self) -> int:
        return int(self.y.shape[0])

    def __getitem__(self, index: int):
        return self.x[index], self.y[index]


def build_row_arrays(df: pd.DataFrame, feature_cols: list[str]) -> tuple[np.ndarray, np.ndarray]:
    x = df[feature_cols].values.astype(np.float32)
    y = df["MultiLabel"].values.astype(np.int64)
    return x, y


class MLPStageClassifier(nn.Module):
    def __init__(
        self,
        num_features: int,
        hidden_dim: int,
        num_layers: int,
        dropout: float,
        num_classes: int,
    ):
        super().__init__()
        layers: list[nn.Module] = []
        in_dim = num_features
        for _ in range(num_layers):
            layers.extend(
                [
                    nn.Linear(in_dim, hidden_dim),
                    nn.BatchNorm1d(hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(dropout),
                ]
            )
            in_dim = hidden_dim
        layers.append(nn.Linear(in_dim, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)


def evaluate_row_model(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []

    with torch.no_grad():
        for xs, ys in loader:
            xs = xs.to(device)
            ys = ys.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=1)
            preds.append(probs.argmax(dim=1).cpu().numpy())
            labels.append(ys.cpu().numpy())
            probs_list.append(probs.cpu().numpy())

    y_true = np.concatenate(labels)
    y_pred = np.concatenate(preds)
    probs = np.vstack(probs_list)
    return compute_metrics(y_true, y_pred, probs, STAGE_NAMES)


def train_row_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    train_labels: np.ndarray,
    device: torch.device,
    lr: float,
    weight_decay: float,
    epochs: int,
    patience: int,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = nn.CrossEntropyLoss(
        weight=compute_class_weights(train_labels, num_classes=len(STAGE_NAMES)).to(device)
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
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

        val_metrics = evaluate_row_model(model, val_loader, device)
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

        if val_metrics["f1"] > best_score:
            best_score = val_metrics["f1"]
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Row model training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


class SequenceChunkDataset(Dataset):
    def __init__(self, chunks: list[tuple[np.ndarray, np.ndarray]]):
        self.chunks = chunks

    def __len__(self) -> int:
        return len(self.chunks)

    def __getitem__(self, index: int):
        return self.chunks[index]


def build_sequence_chunks(
    df: pd.DataFrame,
    feature_cols: list[str],
    sequence_length: int,
    min_sequence_length: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    chunks: list[tuple[np.ndarray, np.ndarray]] = []
    ordered_groups = df.groupby("source_file")["timestamp_sort"].min().sort_values().index.tolist()

    for source_file in ordered_groups:
        source_df = (
            df[df["source_file"] == source_file]
            .sort_values("timestamp_sort")
            .reset_index(drop=True)
        )
        xs = source_df[feature_cols].values.astype(np.float32)
        ys = source_df["MultiLabel"].values.astype(np.int64)

        for start in range(0, len(source_df), sequence_length):
            x_chunk = xs[start : start + sequence_length]
            y_chunk = ys[start : start + sequence_length]
            if len(x_chunk) < min_sequence_length:
                continue
            chunks.append((x_chunk, y_chunk))

    return chunks


def collate_sequence_chunks(batch):
    max_len = max(item[0].shape[0] for item in batch)
    feat_dim = batch[0][0].shape[1]
    xs = torch.zeros((len(batch), max_len, feat_dim), dtype=torch.float32)
    ys = torch.full((len(batch), max_len), -100, dtype=torch.long)
    mask = torch.zeros((len(batch), max_len), dtype=torch.bool)

    for index, (x_chunk, y_chunk) in enumerate(batch):
        length = x_chunk.shape[0]
        xs[index, :length] = torch.from_numpy(x_chunk)
        ys[index, :length] = torch.from_numpy(y_chunk)
        mask[index, :length] = True

    return xs, ys, mask


class MambaStageClassifier(nn.Module):
    def __init__(
        self,
        num_features: int,
        d_model: int,
        n_layers: int,
        d_state: int,
        d_conv: int,
        dropout: float,
        num_classes: int,
    ):
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(num_features, d_model),
            nn.LayerNorm(d_model),
        )
        self.input_dropout = nn.Dropout(dropout)
        self.backbone = Mamba(
            MambaConfig(
                d_model=d_model,
                n_layers=n_layers,
                d_state=d_state,
                d_conv=d_conv,
                use_cuda=False,
            )
        )
        self.output_norm = nn.LayerNorm(d_model)
        self.output_dropout = nn.Dropout(dropout)
        self.head = nn.Linear(d_model, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.input_dropout(self.input_proj(x))
        x = self.backbone(x)
        x = self.output_dropout(self.output_norm(x))
        return self.head(x)


def evaluate_sequence_model(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    model.eval()
    preds: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    probs_list: list[np.ndarray] = []

    with torch.no_grad():
        for xs, ys, mask in loader:
            xs = xs.to(device)
            ys = ys.to(device)
            mask = mask.to(device)
            logits = model(xs)
            probs = torch.softmax(logits, dim=-1)
            flat_mask = mask.view(-1)
            flat_probs = probs.view(-1, probs.shape[-1])[flat_mask]
            flat_labels = ys.view(-1)[flat_mask]
            preds.append(flat_probs.argmax(dim=1).cpu().numpy())
            labels.append(flat_labels.cpu().numpy())
            probs_list.append(flat_probs.cpu().numpy())

    y_true = np.concatenate(labels)
    y_pred = np.concatenate(preds)
    probs = np.vstack(probs_list)
    return compute_metrics(y_true, y_pred, probs, STAGE_NAMES)


def train_sequence_model(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    train_labels: np.ndarray,
    device: torch.device,
    lr: float,
    weight_decay: float,
    epochs: int,
    patience: int,
) -> tuple[nn.Module, dict[str, Any], list[dict[str, Any]]]:
    model = model.to(device)
    criterion = nn.CrossEntropyLoss(
        weight=compute_class_weights(train_labels, num_classes=len(STAGE_NAMES)).to(device),
        ignore_index=-100,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)

    best_state: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_score = -float("inf")
    wait = 0
    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_tokens = 0

        for xs, ys, mask in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            optimizer.zero_grad()
            logits = model(xs)
            loss = criterion(logits.view(-1, logits.shape[-1]), ys.view(-1))
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            total_loss += float(loss.item()) * int(mask.sum().item())
            total_tokens += int(mask.sum().item())

        val_metrics = evaluate_sequence_model(model, val_loader, device)
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

        if val_metrics["f1"] > best_score:
            best_score = val_metrics["f1"]
            best_metrics = val_metrics
            best_state = copy.deepcopy(model.state_dict())
            wait = 0
        else:
            wait += 1
            if wait >= patience:
                break

    if best_state is None or best_metrics is None:
        raise RuntimeError("Sequence model training completed without a best checkpoint.")

    model.load_state_dict(best_state)
    return model, best_metrics, history


def instantiate_graph_model(
    model_name: str,
    num_features: int,
    params: dict[str, Any],
    gml: Any,
    pretrained_encoder: Any = None,
) -> nn.Module:
    hidden_dim = int(params.get("hidden_dim", 96))
    dropout = float(params.get("dropout", 0.3))

    if model_name == "GATv2":
        return gml.NodeLevelGATv2(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            attention_dropout=float(params.get("attention_dropout", 0.1)),
            heads=int(params.get("heads", 4)),
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "RGCN":
        return gml.NodeLevelRGCN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "ST-GCN":
        return gml.NodeLevelSTGCN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            num_st_blocks=int(params.get("num_st_blocks", 2)),
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "GIN":
        return gml.NodeLevelGIN(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            num_classes=len(STAGE_NAMES),
        )
    if model_name == "GCN-DGI":
        return gml.NodeLevelGCN_DGI(
            num_features=num_features,
            hidden_dim=hidden_dim,
            dropout=dropout,
            pretrained_encoder=pretrained_encoder,
            num_classes=len(STAGE_NAMES),
        )
    raise ValueError(f"Unsupported graph model: {model_name}")


def suggest_graph_params(trial: optuna.Trial, model_name: str) -> dict[str, Any]:
    params = {
        "hidden_dim": trial.suggest_categorical("hidden_dim", [64, 96]),
        "dropout": trial.suggest_float("dropout", 0.15, 0.45),
        "lr": trial.suggest_float("lr", 5e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }
    if model_name == "GATv2":
        params["heads"] = trial.suggest_categorical("heads", [4, 8])
        params["attention_dropout"] = trial.suggest_float("attention_dropout", 0.0, 0.25)
    if model_name == "ST-GCN":
        params["num_st_blocks"] = trial.suggest_int("num_st_blocks", 2, 3)
    if model_name == "GCN-DGI":
        params["hidden_dim"] = 96
    return params


def suggest_mamba_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "d_model": trial.suggest_categorical("d_model", [64, 96]),
        "n_layers": trial.suggest_int("n_layers", 2, 3),
        "d_state": trial.suggest_categorical("d_state", [8, 16]),
        "d_conv": trial.suggest_categorical("d_conv", [4, 8]),
        "dropout": trial.suggest_float("dropout", 0.1, 0.35),
        "lr": trial.suggest_float("lr", 5e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }


def suggest_mlp_params(trial: optuna.Trial) -> dict[str, Any]:
    return {
        "hidden_dim": trial.suggest_categorical("hidden_dim", [128, 256]),
        "num_layers": trial.suggest_int("num_layers", 2, 3),
        "dropout": trial.suggest_float("dropout", 0.1, 0.4),
        "lr": trial.suggest_float("lr", 5e-4, 3e-3, log=True),
        "weight_decay": trial.suggest_float("weight_decay", 1e-6, 1e-3, log=True),
    }


def optimize_graph_model(
    model_name: str,
    train_graphs,
    val_graphs,
    settings: dict[str, Any],
    device: torch.device,
    gml: Any,
    pretrained_encoder: Any = None,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_loader = GraphDataLoader(
        train_graphs,
        batch_size=int(settings["graph_batch_size"]),
        shuffle=True,
    )
    val_loader = GraphDataLoader(
        val_graphs,
        batch_size=int(settings["graph_batch_size"]),
        shuffle=False,
    )
    train_labels = np.concatenate([graph.y.cpu().numpy() for graph in train_graphs])
    num_features = int(train_graphs[0].x.shape[1])

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_graph_params(trial, model_name)
        model = instantiate_graph_model(
            model_name=model_name,
            num_features=num_features,
            params=params,
            gml=gml,
            pretrained_encoder=pretrained_encoder,
        )
        model, val_metrics, history = train_graph_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            device=device,
            train_labels=train_labels,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            epochs=int(settings["train_epochs"]),
            patience=int(settings["early_stopping_patience"]),
        )
        score = float(val_metrics["f1"])
        if best_metrics is None or score > best_metrics["f1"]:
            best_model = model
            best_params = params
            best_metrics = val_metrics
            best_history = history
        return score

    study = optuna.create_study(direction="maximize")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError(f"Optuna did not produce a best {model_name} model.")

    return best_model, best_params, best_metrics, best_history


def optimize_mlp_model(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_cols: list[str],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_x, train_y = build_row_arrays(train_df, feature_cols)
    val_x, val_y = build_row_arrays(val_df, feature_cols)

    train_loader = DataLoader(
        RowDataset(train_x, train_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=True,
    )
    val_loader = DataLoader(
        RowDataset(val_x, val_y),
        batch_size=int(settings["tabular_batch_size"]),
        shuffle=False,
    )

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_mlp_params(trial)
        model = MLPStageClassifier(
            num_features=len(feature_cols),
            hidden_dim=int(params["hidden_dim"]),
            num_layers=int(params["num_layers"]),
            dropout=float(params["dropout"]),
            num_classes=len(STAGE_NAMES),
        )
        model, val_metrics, history = train_row_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=train_y,
            device=device,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            epochs=int(settings["train_epochs"]),
            patience=int(settings["early_stopping_patience"]),
        )
        score = float(val_metrics["f1"])
        if best_metrics is None or score > best_metrics["f1"]:
            best_model = model
            best_params = params
            best_metrics = val_metrics
            best_history = history
        return score

    study = optuna.create_study(direction="maximize")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError("Optuna did not produce a best MLP model.")

    return best_model, best_params, best_metrics, best_history


def optimize_mamba_model(
    train_chunks: list[tuple[np.ndarray, np.ndarray]],
    val_chunks: list[tuple[np.ndarray, np.ndarray]],
    feature_cols: list[str],
    settings: dict[str, Any],
    device: torch.device,
) -> tuple[nn.Module, dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    train_loader = DataLoader(
        SequenceChunkDataset(train_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=True,
        collate_fn=collate_sequence_chunks,
    )
    val_loader = DataLoader(
        SequenceChunkDataset(val_chunks),
        batch_size=int(settings["sequence_batch_size"]),
        shuffle=False,
        collate_fn=collate_sequence_chunks,
    )
    train_labels = np.concatenate([chunk[1] for chunk in train_chunks])

    best_model: nn.Module | None = None
    best_params: dict[str, Any] | None = None
    best_metrics: dict[str, Any] | None = None
    best_history: list[dict[str, Any]] = []

    def objective(trial: optuna.Trial) -> float:
        nonlocal best_model, best_params, best_metrics, best_history
        params = suggest_mamba_params(trial)
        model = MambaStageClassifier(
            num_features=len(feature_cols),
            d_model=int(params["d_model"]),
            n_layers=int(params["n_layers"]),
            d_state=int(params["d_state"]),
            d_conv=int(params["d_conv"]),
            dropout=float(params["dropout"]),
            num_classes=len(STAGE_NAMES),
        )
        model, val_metrics, history = train_sequence_model(
            model=model,
            train_loader=train_loader,
            val_loader=val_loader,
            train_labels=train_labels,
            device=device,
            lr=float(params["lr"]),
            weight_decay=float(params["weight_decay"]),
            epochs=int(settings["train_epochs"]),
            patience=int(settings["early_stopping_patience"]),
        )
        score = float(val_metrics["f1"])
        if best_metrics is None or score > best_metrics["f1"]:
            best_model = model
            best_params = params
            best_metrics = val_metrics
            best_history = history
        return score

    study = optuna.create_study(direction="maximize")
    study.optimize(
        objective,
        n_trials=max(int(settings["optuna_trials"]), 1),
        timeout=settings.get("optuna_timeout_seconds"),
    )

    if best_model is None or best_params is None or best_metrics is None:
        raise RuntimeError("Optuna did not produce a best Mamba model.")

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

    metrics_df = pd.DataFrame(rows).sort_values("f1", ascending=False)
    metrics_df.to_csv(run_dir / "metrics-table.csv", index=False)
    write_json(run_dir / "metrics-table.json", {"rows": metrics_df.to_dict(orient="records")})


def run_unraveled_v02(settings: dict[str, Any]) -> Path:
    repo_root = resolve_repo_root()
    merged = dict(DEFAULTS)
    merged.update(settings)

    if bool(merged["include_cover_up"]):
        raise ValueError("Praxisv02 currently benchmarks the 5 stable Unraveled stages and excludes Cover up.")

    run_dir = resolve_path(repo_root, merged["output_dir"]) / merged["run_name"]
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": merged,
        "environment": detect_environment(),
    }
    write_json(run_dir / "metadata.json", metadata)

    set_random_seed(int(merged["random_seed"]))
    device = choose_device(bool(merged["force_cpu"]))
    print(f"Praxisv02 device: {device}")

    gml = load_gml_module(repo_root)
    df, cache_metadata, cache_path, cache_metadata_path = load_or_build_cache(merged, repo_root)
    write_json(
        run_dir / "cache-summary.json",
        {
            "cache_path": cache_path,
            "cache_metadata_path": cache_metadata_path,
            "rows": int(len(df)),
            "stage_counts": cache_metadata.get("stage_counts", {}),
        },
    )

    train_df, val_df, test_df, feature_cols, preprocess_summary = prepare_features_and_splits(
        df=df,
        settings=merged,
        gml=gml,
        run_dir=run_dir,
    )

    results: dict[str, Any] = {}

    for model_name in GRAPH_MODEL_NAMES:
        print(f"\n{'=' * 80}")
        print(f"Praxisv02 graph model: {model_name}")
        print(f"{'=' * 80}")

        train_graphs = build_graphs_for_frame(
            df=train_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(merged["flows_per_graph"]),
            min_graph_size=int(merged["min_graph_size"]),
            graph_k=int(merged["graph_k"]),
            stgcn_temporal_k=int(merged["stgcn_temporal_k"]),
            gml=gml,
        )
        val_graphs = build_graphs_for_frame(
            df=val_df,
            feature_cols=feature_cols,
            model_name=model_name,
            flows_per_graph=int(merged["flows_per_graph"]),
            min_graph_size=int(merged["min_graph_size"]),
            graph_k=int(merged["graph_k"]),
            stgcn_temporal_k=int(merged["stgcn_temporal_k"]),
            gml=gml,
        )
        test_graphs = build_graphs_for_frame(
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
                hidden_dim=96,
                epochs=int(merged["dgi_pretrain_epochs"]),
                verbose=True,
            )

        best_model, best_params, val_metrics, history = optimize_graph_model(
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
        test_metrics = evaluate_graph_model(best_model, test_loader, device)
        results[model_name] = {
            "best_params": best_params,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "history": history,
            "graph_counts": {
                "train": len(train_graphs),
                "val": len(val_graphs),
                "test": len(test_graphs),
            },
        }
        write_json(run_dir / f"{model_name.lower().replace('-', '_')}_results.json", results[model_name])

    print(f"\n{'=' * 80}")
    print("Praxisv02 tabular model: MLP")
    print(f"{'=' * 80}")
    mlp_model, best_params, val_metrics, history = optimize_mlp_model(
        train_df=train_df,
        val_df=val_df,
        feature_cols=feature_cols,
        settings=merged,
        device=device,
    )
    test_x, test_y = build_row_arrays(test_df, feature_cols)
    test_loader = DataLoader(
        RowDataset(test_x, test_y),
        batch_size=int(merged["tabular_batch_size"]),
        shuffle=False,
    )
    test_metrics = evaluate_row_model(mlp_model, test_loader, device)
    results["MLP"] = {
        "best_params": best_params,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "history": history,
        "row_counts": {
            "train": int(len(train_df)),
            "val": int(len(val_df)),
            "test": int(len(test_df)),
        },
    }
    write_json(run_dir / "mlp_results.json", results["MLP"])

    print(f"\n{'=' * 80}")
    print("Praxisv02 sequence model: Mamba")
    print(f"{'=' * 80}")

    train_chunks = build_sequence_chunks(
        train_df,
        feature_cols=feature_cols,
        sequence_length=int(merged["sequence_length"]),
        min_sequence_length=int(merged["min_sequence_length"]),
    )
    val_chunks = build_sequence_chunks(
        val_df,
        feature_cols=feature_cols,
        sequence_length=int(merged["sequence_length"]),
        min_sequence_length=int(merged["min_sequence_length"]),
    )
    test_chunks = build_sequence_chunks(
        test_df,
        feature_cols=feature_cols,
        sequence_length=int(merged["sequence_length"]),
        min_sequence_length=int(merged["min_sequence_length"]),
    )

    if not train_chunks or not val_chunks or not test_chunks:
        raise RuntimeError("Mamba sequence chunking produced an empty split.")

    mamba_model, best_params, val_metrics, history = optimize_mamba_model(
        train_chunks=train_chunks,
        val_chunks=val_chunks,
        feature_cols=feature_cols,
        settings=merged,
        device=device,
    )
    test_loader = DataLoader(
        SequenceChunkDataset(test_chunks),
        batch_size=int(merged["sequence_batch_size"]),
        shuffle=False,
        collate_fn=collate_sequence_chunks,
    )
    test_metrics = evaluate_sequence_model(mamba_model, test_loader, device)
    results["Mamba"] = {
        "best_params": best_params,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "history": history,
        "sequence_counts": {
            "train": len(train_chunks),
            "val": len(val_chunks),
            "test": len(test_chunks),
        },
    }
    write_json(run_dir / "mamba_results.json", results["Mamba"])

    save_metrics_table(run_dir, results)

    summary = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": merged["pipeline"],
        "run_name": merged["run_name"],
        "device": str(device),
        "cache_path": cache_path,
        "feature_count": preprocess_summary["feature_count"],
        "results": results,
    }
    write_json(run_dir / "results-summary.json", summary)
    return run_dir
