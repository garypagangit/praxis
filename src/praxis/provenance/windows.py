from __future__ import annotations

import json
import re
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class WindowConfig:
    """Configuration for deterministic provenance window construction."""

    mode: str = "event_count"
    events_per_window: int = 5000
    seconds_per_window: float = 300.0
    top_event_k: int = 32
    top_exec_k: int = 32
    min_rows: int = 1


def _safe_feature_name(prefix: str, value: Any) -> str:
    text = str(value or "UNKNOWN").strip() or "UNKNOWN"
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return f"{prefix}__{text[:96]}"


def normalize_uuid(value: Any) -> str:
    """Normalize UUID strings to the 32-char hex form used by converted edges."""

    text = str(value or "").strip().strip("{}").lower()
    text = text.replace("-", "")
    return re.sub(r"[^0-9a-f]", "", text)


def _jsonl_rows(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_edges_jsonl(path: Path, limit: int | None = None) -> pd.DataFrame:
    """Read normalized provenance edges emitted by the DARPA Cadets converter."""

    rows: list[dict[str, Any]] = []
    for row in _jsonl_rows(path, limit=limit):
        properties = row.get("properties") or {}
        event_names = row.get("event_names") or []
        rows.append(
            {
                "timestamp_nanos": row.get("timestamp_nanos"),
                "sequence": row.get("sequence"),
                "record_index": row.get("record_index"),
                "datum_type": str(row.get("datum_type") or "UNKNOWN"),
                "exec": str(properties.get("exec") or "UNKNOWN"),
                "source_file": str(row.get("source_file") or "UNKNOWN"),
                "subject_uuid": str(row.get("subject_uuid") or "UNKNOWN"),
                "object_uuid": str(row.get("object_uuid") or "UNKNOWN"),
                "object2_uuid": str(row.get("object2_uuid") or "UNKNOWN"),
                "event_name": str(event_names[0]) if event_names else "UNKNOWN",
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    frame["timestamp_nanos"] = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    frame["sequence"] = pd.to_numeric(frame["sequence"], errors="coerce").fillna(-1)
    frame["record_index"] = (
        pd.to_numeric(frame["record_index"], errors="coerce").fillna(-1).astype(int)
    )
    frame = frame.dropna(subset=["timestamp_nanos"])
    frame = frame.sort_values(["timestamp_nanos", "sequence", "record_index"])
    return frame.reset_index(drop=True)


def load_label_spans(path: Path | None) -> pd.DataFrame:
    """Load optional interval labels with start_ns, end_ns, and label columns."""

    if path is None:
        return pd.DataFrame(columns=["start_ns", "end_ns", "label"])
    if path.suffix.lower() == ".csv":
        labels = pd.read_csv(path)
    elif path.suffix.lower() == ".jsonl":
        labels = pd.DataFrame(_jsonl_rows(path))
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        labels = pd.DataFrame(payload if isinstance(payload, list) else payload.get("labels", []))

    rename = {
        "start": "start_ns",
        "end": "end_ns",
        "start_timestamp_nanos": "start_ns",
        "end_timestamp_nanos": "end_ns",
        "name": "label",
    }
    labels = labels.rename(columns=rename)
    required = {"start_ns", "end_ns", "label"}
    missing = required.difference(labels.columns)
    if missing:
        raise ValueError(f"Label file is missing required columns: {sorted(missing)}")
    labels = labels[["start_ns", "end_ns", "label"]].copy()
    labels["start_ns"] = pd.to_numeric(labels["start_ns"], errors="coerce")
    labels["end_ns"] = pd.to_numeric(labels["end_ns"], errors="coerce")
    labels["label"] = labels["label"].astype(str)
    labels = labels.dropna(subset=["start_ns", "end_ns", "label"])
    labels = labels[labels["end_ns"] >= labels["start_ns"]]
    return labels.sort_values(["start_ns", "end_ns", "label"]).reset_index(drop=True)


def load_node_labels(paths: list[Path] | None) -> pd.DataFrame:
    """Load PIDSMaker-style node ground-truth CSVs.

    The local PIDSMaker files are headerless CSV rows shaped roughly as:
    UUID, descriptor, graph_node_id. We keep the UUID and source file and use the
    file stem as the label unless a later dataset provides richer labels.
    """

    if not paths:
        return pd.DataFrame(columns=["node_uuid", "label", "source_file", "raw_id"])
    rows: list[dict[str, Any]] = []
    for path in paths:
        with path.open("r", encoding="utf-8", newline="") as handle:
            for raw in csv.reader(handle):
                if not raw:
                    continue
                node_uuid = normalize_uuid(raw[0])
                if not node_uuid:
                    continue
                rows.append(
                    {
                        "node_uuid": node_uuid,
                        "label": path.stem,
                        "source_file": str(path),
                        "raw_id": raw[2] if len(raw) > 2 else "",
                    }
                )
    labels = pd.DataFrame(rows)
    if labels.empty:
        return pd.DataFrame(columns=["node_uuid", "label", "source_file", "raw_id"])
    return labels.drop_duplicates(["node_uuid", "label"]).reset_index(drop=True)


def _assign_window_ids(frame: pd.DataFrame, config: WindowConfig) -> pd.Series:
    if config.mode == "event_count":
        if config.events_per_window <= 0:
            raise ValueError("events_per_window must be positive")
        return pd.Series(np.arange(len(frame)) // config.events_per_window, index=frame.index)
    if config.mode == "time":
        if config.seconds_per_window <= 0:
            raise ValueError("seconds_per_window must be positive")
        start = float(frame["timestamp_nanos"].min())
        width = config.seconds_per_window * 1e9
        return ((frame["timestamp_nanos"] - start) // width).astype(int)
    raise ValueError(f"Unknown window mode: {config.mode}")


def _select_vocab(frame: pd.DataFrame, column: str, top_k: int) -> list[str]:
    return [
        str(value)
        for value in frame[column].astype(str).value_counts().head(top_k).index.tolist()
    ]


def _label_window(start_ns: float, end_ns: float, labels: pd.DataFrame) -> dict[str, Any]:
    if labels.empty:
        return {"primary_label": "unlabeled", "labels": "", "label_overlap_ns": 0.0}
    overlaps: list[tuple[str, float]] = []
    for row in labels.itertuples(index=False):
        overlap = max(0.0, min(end_ns, float(row.end_ns)) - max(start_ns, float(row.start_ns)))
        if overlap > 0:
            overlaps.append((str(row.label), overlap))
    if not overlaps:
        return {"primary_label": "benign_or_unlabeled", "labels": "", "label_overlap_ns": 0.0}
    by_label: dict[str, float] = {}
    for label, overlap in overlaps:
        by_label[label] = by_label.get(label, 0.0) + overlap
    primary = max(by_label.items(), key=lambda item: (item[1], item[0]))
    return {
        "primary_label": primary[0],
        "labels": ";".join(sorted(by_label)),
        "label_overlap_ns": float(primary[1]),
    }


def _node_label_window(group: pd.DataFrame, node_labels: pd.DataFrame) -> dict[str, Any]:
    if node_labels.empty:
        return {
            "malicious_node_events": 0,
            "malicious_node_count": 0,
            "node_labels": "",
        }
    node_to_label = dict(zip(node_labels["node_uuid"], node_labels["label"]))
    touched_labels: set[str] = set()
    touched_nodes: set[str] = set()
    event_count = 0
    for row in group[["subject_uuid", "object_uuid", "object2_uuid"]].itertuples(index=False):
        row_hit = False
        for value in row:
            normalized = normalize_uuid(value)
            label = node_to_label.get(normalized)
            if label:
                touched_labels.add(str(label))
                touched_nodes.add(normalized)
                row_hit = True
        if row_hit:
            event_count += 1
    return {
        "malicious_node_events": int(event_count),
        "malicious_node_count": int(len(touched_nodes)),
        "node_labels": ";".join(sorted(touched_labels)),
    }


def build_window_tables(
    edges: pd.DataFrame,
    config: WindowConfig,
    labels: pd.DataFrame | None = None,
    node_labels: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    """Build window metadata and fixed-width feature tables from edge rows."""

    if edges.empty:
        raise ValueError("No provenance edges were loaded.")
    labels = labels if labels is not None else pd.DataFrame()
    node_labels = node_labels if node_labels is not None else pd.DataFrame()
    frame = edges.copy()
    frame["window_id"] = _assign_window_ids(frame, config)
    event_vocab = _select_vocab(frame, "datum_type", config.top_event_k)
    exec_vocab = _select_vocab(frame, "exec", config.top_exec_k)
    event_features = [_safe_feature_name("event", value) for value in event_vocab]
    exec_features = [_safe_feature_name("exec", value) for value in exec_vocab]

    metadata_rows: list[dict[str, Any]] = []
    feature_rows: list[dict[str, Any]] = []
    for window_id, group in frame.groupby("window_id", sort=True):
        if len(group) < config.min_rows:
            continue
        start_ns = float(group["timestamp_nanos"].min())
        end_ns = float(group["timestamp_nanos"].max())
        label_info = _label_window(start_ns, end_ns, labels)
        node_label_info = _node_label_window(group, node_labels)
        combined_labels = sorted(
            label
            for label in set(
                (label_info.get("labels") or "").split(";")
                + (node_label_info.get("node_labels") or "").split(";")
            )
            if label
        )
        if label_info["primary_label"] in {"unlabeled", "benign_or_unlabeled"}:
            primary_label = "attack_node_touch" if combined_labels else label_info["primary_label"]
        else:
            primary_label = label_info["primary_label"]
        metadata = {
            "window_id": int(window_id),
            "rows": int(len(group)),
            "start_ns": int(start_ns),
            "end_ns": int(end_ns),
            "span_seconds": float((end_ns - start_ns) / 1e9),
            "source_files": int(group["source_file"].nunique()),
            "distinct_subjects": int(group["subject_uuid"].nunique()),
            "distinct_objects": int(group["object_uuid"].nunique()),
            "distinct_execs": int(group["exec"].nunique()),
            "distinct_event_types": int(group["datum_type"].nunique()),
            **label_info,
            **node_label_info,
            "primary_label": primary_label,
            "labels": ";".join(combined_labels),
        }
        features = dict(metadata)
        event_dist = group["datum_type"].astype(str).value_counts(normalize=True)
        exec_dist = group["exec"].astype(str).value_counts(normalize=True)
        for raw, column in zip(event_vocab, event_features):
            features[column] = float(event_dist.get(raw, 0.0))
        for raw, column in zip(exec_vocab, exec_features):
            features[column] = float(exec_dist.get(raw, 0.0))
        metadata_rows.append(metadata)
        feature_rows.append(features)

    windows = pd.DataFrame(metadata_rows)
    features = pd.DataFrame(feature_rows)
    summary = {
        "config": asdict(config),
        "edge_rows": int(len(edges)),
        "window_count": int(len(windows)),
        "labeled_window_count": int((windows["labels"].astype(str) != "").sum())
        if not windows.empty
        else 0,
        "node_label_count": int(len(node_labels)),
        "node_labeled_window_count": int((windows["malicious_node_events"] > 0).sum())
        if not windows.empty and "malicious_node_events" in windows
        else 0,
        "source_files": int(edges["source_file"].nunique()),
        "span_seconds": float(
            (edges["timestamp_nanos"].max() - edges["timestamp_nanos"].min()) / 1e9
        ),
        "event_vocab": event_vocab,
        "exec_vocab": exec_vocab,
    }
    return windows, features, summary


def write_window_artifacts(
    edges_path: Path,
    out_dir: Path,
    config: WindowConfig,
    labels_path: Path | None = None,
    node_label_paths: list[Path] | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build and persist reusable provenance window artifacts."""

    edges = read_edges_jsonl(edges_path, limit=limit)
    labels = load_label_spans(labels_path)
    node_labels = load_node_labels(node_label_paths)
    windows, features, summary = build_window_tables(
        edges, config, labels=labels, node_labels=node_labels
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    windows_path = out_dir / "windows.csv"
    features_path = out_dir / "window_features.csv"
    manifest_path = out_dir / "manifest.json"
    labels_template_path = out_dir / "labels_template.csv"
    windows.to_csv(windows_path, index=False)
    features.to_csv(features_path, index=False)
    if not labels_template_path.exists():
        pd.DataFrame(
            [
                {
                    "start_ns": "",
                    "end_ns": "",
                    "label": "attack_stage_or_anomaly_name",
                }
            ]
        ).to_csv(labels_template_path, index=False)
    manifest = {
        **summary,
        "inputs": {
            "edges": str(edges_path),
            "labels": str(labels_path) if labels_path else None,
            "node_labels": [str(path) for path in node_label_paths or []],
        },
        "artifacts": {
            "windows": str(windows_path),
            "features": str(features_path),
            "labels_template": str(labels_template_path),
            "manifest": str(manifest_path),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
