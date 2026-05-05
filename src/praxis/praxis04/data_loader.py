from __future__ import annotations

import hashlib
import json
import re
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from sklearn.preprocessing import LabelEncoder, StandardScaler

from praxis.praxis04.stage_mapper import map_attack_series


LABEL_CANDIDATES = ("Label", "label", "Attack", "attack", "Class", "class")
NEGATIVE_BAD_COLUMNS = (
    "Init_Win_bytes_forward",
    "Init_Win_bytes_backward",
    "Init Fwd Win Byts",
    "Init Bwd Win Byts",
)


@dataclass(frozen=True)
class SplitFrames:
    train: pd.DataFrame
    val: pd.DataFrame
    test: pd.DataFrame
    summary: dict


@dataclass(frozen=True)
class MatrixSplit:
    x_train: np.ndarray
    y_train: np.ndarray
    stage_train: np.ndarray
    x_val: np.ndarray
    y_val: np.ndarray
    stage_val: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    stage_test: np.ndarray
    label_names: list[str]
    stage_names: list[str]
    feature_names: list[str]
    summary: dict


def csv_manifest(data_dir: str | Path) -> list[dict[str, str | int]]:
    root = Path(data_dir)
    rows = []
    for path in sorted(root.rglob("*.csv")):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        rows.append(
            {
                "path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    return rows


def write_csv_manifest(data_dir: str | Path, output_path: str | Path | None = None) -> Path:
    root = Path(data_dir)
    output = Path(output_path) if output_path else root / "manifest.json"
    payload = {"data_dir": str(root), "files": csv_manifest(root)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output


def discover_label_column(columns: Iterable[str]) -> str:
    normalized = {column.strip(): column for column in columns}
    for candidate in LABEL_CANDIDATES:
        if candidate in normalized:
            return normalized[candidate]
    raise ValueError(f"No label column found. Tried: {', '.join(LABEL_CANDIDATES)}")


def infer_day_from_path(path: Path) -> str:
    match = re.search(r"(\d{2})[-_](\d{2})[-_](\d{4})", path.name)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return path.stem


def load_cicids2018_csvs(
    data_dir: str | Path,
    sample_rows_per_file: int | None = None,
    chunksize: int = 200_000,
    sample_seed: int = 42,
    sample_strategy: str = "head",
) -> pd.DataFrame:
    if sample_strategy not in {"head", "uniform"}:
        raise ValueError("sample_strategy must be 'head' or 'uniform'.")
    frames = []
    feature_columns: list[str] | None = None
    rows_by_file: dict[str, int] = {}
    dropped_by_file: dict[str, int] = {}
    sampled_by_file: dict[str, int] = {}
    for path in sorted(Path(data_dir).rglob("*.csv")):
        read_rows = 0
        dropped_rows = 0
        sample_limit = int(sample_rows_per_file) if sample_rows_per_file else None
        sampled_frames = []
        sampled_priorities = []
        file_seed = int(sample_seed) ^ zlib.crc32(str(path.name).encode("utf-8"))
        rng = np.random.default_rng(file_seed)
        if sample_limit and sample_strategy == "head":
            iterator = pd.read_csv(path, chunksize=min(chunksize, sample_limit), low_memory=False)
        else:
            iterator = pd.read_csv(path, chunksize=chunksize, low_memory=False)
        for chunk in iterator:
            if sample_limit and sample_strategy == "head" and read_rows >= sample_limit:
                break
            if sample_limit and sample_strategy == "head":
                chunk = chunk.head(sample_limit - read_rows)
            read_rows += len(chunk)
            chunk.columns = [str(column).strip() for column in chunk.columns]
            label_column = discover_label_column(chunk.columns)
            if feature_columns is None:
                feature_columns = infer_numeric_columns(chunk, label_column)
            compact, dropped = compact_numeric_chunk(chunk, feature_columns, label_column, path)
            dropped_rows += dropped
            if sample_limit and sample_strategy == "uniform":
                priorities = rng.random(len(compact), dtype=np.float64)
                sampled_frames, sampled_priorities = keep_lowest_priority_sample(
                    sampled_frames,
                    sampled_priorities,
                    compact,
                    priorities,
                    sample_limit,
                )
            else:
                frames.append(compact)
        if sample_limit and sample_strategy == "uniform":
            sampled = concat_sampled_frames(sampled_frames, sampled_priorities)
            frames.append(sampled)
            sampled_by_file[path.name] = len(sampled)
        else:
            sampled_by_file[path.name] = max(0, read_rows - dropped_rows)
        rows_by_file[path.name] = read_rows
        dropped_by_file[path.name] = dropped_rows
    if not frames:
        raise FileNotFoundError(f"No CSV files found under {data_dir}")
    frame = pd.concat(frames, ignore_index=True, copy=False)
    frame.attrs["load_summary"] = {
        "rows_read_by_file": rows_by_file,
        "rows_dropped_by_file": dropped_by_file,
        "rows_sampled_by_file": sampled_by_file,
        "sample_rows_per_file": sample_rows_per_file,
        "sample_seed": sample_seed,
        "sampling_strategy": sample_strategy if sample_rows_per_file else "full",
        "feature_columns": feature_columns or [],
    }
    return frame


def keep_lowest_priority_sample(
    sampled_frames: list[pd.DataFrame],
    sampled_priorities: list[np.ndarray],
    compact: pd.DataFrame,
    priorities: np.ndarray,
    sample_limit: int,
) -> tuple[list[pd.DataFrame], list[np.ndarray]]:
    if len(compact) == 0:
        return sampled_frames, sampled_priorities
    sampled_frames.append(compact.reset_index(drop=True))
    sampled_priorities.append(priorities)
    total = sum(len(frame) for frame in sampled_frames)
    if total <= sample_limit:
        return sampled_frames, sampled_priorities

    combined = pd.concat(sampled_frames, ignore_index=True, copy=False)
    combined_priority = np.concatenate(sampled_priorities)
    keep_idx = np.argpartition(combined_priority, sample_limit - 1)[:sample_limit]
    keep_idx = keep_idx[np.argsort(combined_priority[keep_idx], kind="mergesort")]
    return [combined.iloc[keep_idx].reset_index(drop=True)], [combined_priority[keep_idx]]


def concat_sampled_frames(sampled_frames: list[pd.DataFrame], sampled_priorities: list[np.ndarray]) -> pd.DataFrame:
    if not sampled_frames:
        return pd.DataFrame()
    combined = pd.concat(sampled_frames, ignore_index=True, copy=False)
    priority = np.concatenate(sampled_priorities)
    order = np.argsort(priority, kind="mergesort")
    return combined.iloc[order].reset_index(drop=True)


def infer_numeric_columns(chunk: pd.DataFrame, label_column: str) -> list[str]:
    excluded = {
        label_column,
        "Timestamp",
        "Flow ID",
        "Src IP",
        "Dst IP",
        "Source IP",
        "Destination IP",
        "SimillarHTTP",
        "source_file",
        "attack_day",
    }
    columns = []
    for column in chunk.columns:
        if column in excluded:
            continue
        numeric = pd.to_numeric(chunk[column], errors="coerce")
        if numeric.notna().any():
            columns.append(column)
    return columns


def compact_numeric_chunk(
    chunk: pd.DataFrame,
    feature_columns: list[str],
    label_column: str,
    path: Path,
) -> tuple[pd.DataFrame, int]:
    numeric = chunk[feature_columns].apply(pd.to_numeric, errors="coerce")
    values = numeric.to_numpy(dtype=np.float32, copy=True)
    finite_mask = np.isfinite(values).all(axis=1)
    for column in NEGATIVE_BAD_COLUMNS:
        if column in feature_columns:
            column_idx = feature_columns.index(column)
            finite_mask = finite_mask & (values[:, column_idx] >= 0)

    compact = pd.DataFrame(values[finite_mask], columns=feature_columns)
    labels = chunk.loc[finite_mask, label_column].astype(str).str.strip().reset_index(drop=True)
    compact["attack_label"] = labels
    compact["kill_chain_stage"] = map_attack_series(labels)
    compact["source_file"] = path.name
    compact["attack_day"] = infer_day_from_path(path)
    return compact, int((~finite_mask).sum())


def clean_cicids2018(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    if "load_summary" in frame.attrs:
        summary = frame.attrs["load_summary"]
        summary.update(
            {
                "rows_before": int(sum(summary.get("rows_read_by_file", {}).values())),
                "rows_after": len(frame),
                "rows_dropped": int(sum(summary.get("rows_dropped_by_file", {}).values())),
                "chunked_numeric_loader": True,
            }
        )
        return frame, summary

    before = len(frame)
    cleaned = frame.copy()
    cleaned = cleaned.replace([np.inf, -np.inf], np.nan)

    bad_mask = cleaned.isna().any(axis=1)
    for column in NEGATIVE_BAD_COLUMNS:
        if column in cleaned.columns:
            bad_mask = bad_mask | (pd.to_numeric(cleaned[column], errors="coerce") < 0)

    cleaned = cleaned.loc[~bad_mask].reset_index(drop=True)
    summary = {
        "rows_before": before,
        "rows_after": len(cleaned),
        "rows_dropped": int(before - len(cleaned)),
    }
    return cleaned, summary


def add_stage_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if "attack_label" in frame.columns and "kill_chain_stage" in frame.columns:
        return frame
    label_column = discover_label_column(frame.columns)
    enriched = frame.copy()
    enriched["attack_label"] = enriched[label_column].astype(str).str.strip()
    enriched["kill_chain_stage"] = map_attack_series(enriched["attack_label"])
    return enriched


def temporal_day_split(
    frame: pd.DataFrame,
    val_fraction_of_train_days: float = 0.2,
    holdout_day_pattern: str = "02-03-2018",
    min_train_rows_per_label: int = 0,
    min_val_rows_per_label: int = 0,
    support_fraction_per_label: float = 0.0,
    split_seed: int = 42,
) -> SplitFrames:
    if "attack_day" not in frame.columns:
        raise ValueError("Expected attack_day column before temporal split.")

    days = sorted(frame["attack_day"].dropna().unique())
    holdout_days = [day for day in days if holdout_day_pattern in day]
    if holdout_days:
        test_days = holdout_days
    else:
        test_days = days[-max(1, int(round(len(days) * 0.2))) :]

    remaining_days = [day for day in days if day not in set(test_days)]
    if len(remaining_days) > 1 and val_fraction_of_train_days > 0:
        val_count = max(1, int(round(len(remaining_days) * val_fraction_of_train_days)))
    else:
        val_count = 0
    val_days = remaining_days[-val_count:] if val_count else []
    train_days = [day for day in remaining_days if day not in set(val_days)]

    train = frame[frame["attack_day"].isin(train_days)].copy()
    val = frame[frame["attack_day"].isin(val_days)].copy()
    test = frame[frame["attack_day"].isin(test_days)].copy()
    support_moves = []
    if min_train_rows_per_label > 0 or min_val_rows_per_label > 0 or support_fraction_per_label > 0:
        train, val, test, support_moves = apply_label_support_floor(
            train,
            val,
            test,
            min_train_rows_per_label=min_train_rows_per_label,
            min_val_rows_per_label=min_val_rows_per_label,
            support_fraction_per_label=support_fraction_per_label,
            seed=split_seed,
        )

    split = SplitFrames(
        train=train.reset_index(drop=True),
        val=val.reset_index(drop=True),
        test=test.reset_index(drop=True),
        summary={
            "train_days": train_days,
            "val_days": val_days,
            "test_days": test_days,
            "train_rows": int(len(train)),
            "val_rows": int(len(val)),
            "test_rows": int(len(test)),
            "support_floor_moves": support_moves,
        },
    )
    return split


def apply_label_support_floor(
    train: pd.DataFrame,
    val: pd.DataFrame,
    test: pd.DataFrame,
    min_train_rows_per_label: int,
    min_val_rows_per_label: int,
    support_fraction_per_label: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict[str, int | str]]]:
    if "attack_label" not in train.columns or "attack_label" not in val.columns or "attack_label" not in test.columns:
        return train, val, test, []
    rng = np.random.default_rng(seed)
    train_counts = train["attack_label"].astype(str).value_counts().to_dict()
    val_counts = val["attack_label"].astype(str).value_counts().to_dict()
    moves = []
    train_move_indices = []
    val_move_indices = []
    for label in sorted(test["attack_label"].astype(str).unique()):
        candidate_indices = test.index[test["attack_label"].astype(str) == label].to_numpy()
        if len(candidate_indices) == 0:
            continue
        current = int(train_counts.get(label, 0))
        current_val = int(val_counts.get(label, 0))
        min_needed = max(0, int(min_train_rows_per_label) - current)
        fraction_needed = int(np.ceil(len(candidate_indices) * float(support_fraction_per_label)))
        train_move_count = min(len(candidate_indices), max(min_needed, fraction_needed))
        remaining_after_train = max(0, len(candidate_indices) - train_move_count)
        val_move_count = min(remaining_after_train, max(0, int(min_val_rows_per_label) - current_val))
        move_count = train_move_count + val_move_count
        if move_count <= 0:
            continue
        chosen = rng.choice(candidate_indices, size=move_count, replace=False)
        train_chosen = chosen[:train_move_count]
        val_chosen = chosen[train_move_count:]
        train_move_indices.extend(train_chosen.tolist())
        val_move_indices.extend(val_chosen.tolist())
        moves.append(
            {
                "attack_label": label,
                "moved_train_rows": int(train_move_count),
                "moved_val_rows": int(val_move_count),
                "train_rows_before": current,
                "val_rows_before": current_val,
                "test_rows_before": int(len(candidate_indices)),
            }
        )
    all_move_indices = train_move_indices + val_move_indices
    if not all_move_indices:
        return train, val, test, moves
    train_moved = test.loc[train_move_indices].copy() if train_move_indices else test.iloc[0:0].copy()
    val_moved = test.loc[val_move_indices].copy() if val_move_indices else test.iloc[0:0].copy()
    remaining_test = test.drop(index=all_move_indices)
    return (
        pd.concat([train, train_moved], ignore_index=True, copy=False),
        pd.concat([val, val_moved], ignore_index=True, copy=False),
        remaining_test,
        moves,
    )


def load_preprocessed_split(
    data_dir: str | Path,
    sample_rows_per_file: int | None = None,
    chunksize: int = 200_000,
    sample_seed: int = 42,
    sample_strategy: str = "head",
    holdout_day_pattern: str = "02-03-2018",
    val_fraction_of_train_days: float = 0.2,
    min_train_rows_per_label: int = 0,
    min_val_rows_per_label: int = 0,
    support_fraction_per_label: float = 0.0,
) -> SplitFrames:
    raw = load_cicids2018_csvs(
        data_dir,
        sample_rows_per_file=sample_rows_per_file,
        chunksize=chunksize,
        sample_seed=sample_seed,
        sample_strategy=sample_strategy,
    )
    cleaned, clean_summary = clean_cicids2018(raw)
    enriched = add_stage_columns(cleaned)
    split = temporal_day_split(
        enriched,
        val_fraction_of_train_days=val_fraction_of_train_days,
        holdout_day_pattern=holdout_day_pattern,
        min_train_rows_per_label=min_train_rows_per_label,
        min_val_rows_per_label=min_val_rows_per_label,
        support_fraction_per_label=support_fraction_per_label,
        split_seed=sample_seed,
    )
    split.summary["cleaning"] = clean_summary
    split.summary["stage_counts"] = enriched["kill_chain_stage"].value_counts().to_dict()
    return split


def numeric_feature_columns(frame: pd.DataFrame) -> list[str]:
    excluded = {
        "Label",
        "label",
        "Attack",
        "attack",
        "Class",
        "class",
        "source_file",
        "attack_day",
        "attack_label",
        "kill_chain_stage",
    }
    columns = []
    for column in frame.columns:
        if column in excluded:
            continue
        numeric = pd.to_numeric(frame[column], errors="coerce")
        if numeric.notna().any():
            columns.append(column)
    return columns


def split_to_matrices(split: SplitFrames) -> MatrixSplit:
    feature_names = numeric_feature_columns(split.train)
    if not feature_names:
        raise ValueError("No numeric feature columns found.")

    label_encoder = LabelEncoder()
    stage_encoder = LabelEncoder()
    all_labels = pd.concat([split.train["attack_label"], split.val["attack_label"], split.test["attack_label"]], ignore_index=True)
    all_stages = pd.concat([split.train["kill_chain_stage"], split.val["kill_chain_stage"], split.test["kill_chain_stage"]], ignore_index=True)
    label_encoder.fit(all_labels.astype(str))
    stage_encoder.fit(all_stages.astype(str))

    scaler = StandardScaler()

    def frame_to_x(frame: pd.DataFrame, fit: bool = False) -> np.ndarray:
        numeric = frame[feature_names].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        values = numeric.to_numpy(dtype=np.float32)
        return scaler.fit_transform(values).astype(np.float32) if fit else scaler.transform(values).astype(np.float32)

    x_train = frame_to_x(split.train, fit=True)
    x_val = frame_to_x(split.val) if len(split.val) else np.empty((0, x_train.shape[1]), dtype=np.float32)
    x_test = frame_to_x(split.test)

    return MatrixSplit(
        x_train=x_train,
        y_train=label_encoder.transform(split.train["attack_label"].astype(str)),
        stage_train=stage_encoder.transform(split.train["kill_chain_stage"].astype(str)),
        x_val=x_val,
        y_val=label_encoder.transform(split.val["attack_label"].astype(str)) if len(split.val) else np.empty(0, dtype=int),
        stage_val=stage_encoder.transform(split.val["kill_chain_stage"].astype(str)) if len(split.val) else np.empty(0, dtype=int),
        x_test=x_test,
        y_test=label_encoder.transform(split.test["attack_label"].astype(str)),
        stage_test=stage_encoder.transform(split.test["kill_chain_stage"].astype(str)),
        label_names=[str(item) for item in label_encoder.classes_],
        stage_names=[str(item) for item in stage_encoder.classes_],
        feature_names=feature_names,
        summary=split.summary,
    )
