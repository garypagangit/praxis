from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from fastavro import reader


def normalize_uuid(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex().lower()
    text = str(value).strip().strip("{}").lower().replace("-", "")
    return re.sub(r"[^0-9a-f]", "", text)


def clean_value(value: Any) -> str:
    text = str(value or "UNKNOWN").strip() or "UNKNOWN"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:96]


def numeric_suffix(path: Path) -> tuple[str, int]:
    match = re.search(r"\.bin\.(\d+)\.gz$", path.name)
    return (path.name.rsplit(".bin.", 1)[0], int(match.group(1)) if match else -1)


def load_node_labels(paths: list[Path]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.reader(handle):
                if not row:
                    continue
                node_uuid = normalize_uuid(row[0])
                if node_uuid:
                    labels[node_uuid] = path.stem
    return labels


class WindowAccumulator:
    def __init__(self, window_id: int) -> None:
        self.window_id = window_id
        self.rows = 0
        self.start_ns: int | None = None
        self.end_ns: int | None = None
        self.source_files: set[str] = set()
        self.subjects: set[str] = set()
        self.objects: set[str] = set()
        self.execs: set[str] = set()
        self.event_types: set[str] = set()
        self.event_counter: Counter[str] = Counter()
        self.exec_counter: Counter[str] = Counter()
        self.malicious_node_events = 0
        self.malicious_nodes: set[str] = set()
        self.node_labels: set[str] = set()

    def add(self, row: dict[str, Any], source_file: str, node_labels: dict[str, str]) -> None:
        datum_type = str(row.get("datum_type") or "UNKNOWN")
        exec_name = str(row.get("exec") or "UNKNOWN")
        timestamp = int(row.get("timestamp_nanos") or 0)
        subject_uuid = normalize_uuid(row.get("subject_uuid"))
        object_uuid = normalize_uuid(row.get("object_uuid"))
        object2_uuid = normalize_uuid(row.get("object2_uuid"))

        self.rows += 1
        self.start_ns = timestamp if self.start_ns is None else min(self.start_ns, timestamp)
        self.end_ns = timestamp if self.end_ns is None else max(self.end_ns, timestamp)
        self.source_files.add(source_file)
        if subject_uuid:
            self.subjects.add(subject_uuid)
        if object_uuid:
            self.objects.add(object_uuid)
        if object2_uuid:
            self.objects.add(object2_uuid)
        self.execs.add(exec_name)
        self.event_types.add(datum_type)
        self.event_counter[datum_type] += 1
        self.exec_counter[exec_name] += 1

        hit = False
        for node_uuid in (subject_uuid, object_uuid, object2_uuid):
            label = node_labels.get(node_uuid)
            if label:
                hit = True
                self.malicious_nodes.add(node_uuid)
                self.node_labels.add(label)
        if hit:
            self.malicious_node_events += 1

    def to_metadata(self) -> dict[str, Any]:
        start_ns = self.start_ns or 0
        end_ns = self.end_ns or start_ns
        labels = ";".join(sorted(self.node_labels))
        return {
            "window_id": self.window_id,
            "rows": self.rows,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "span_seconds": (end_ns - start_ns) / 1e9,
            "source_files": len(self.source_files),
            "distinct_subjects": len(self.subjects),
            "distinct_objects": len(self.objects),
            "distinct_execs": len(self.execs),
            "distinct_event_types": len(self.event_types),
            "primary_label": "attack_node_touch" if labels else "benign_or_unlabeled",
            "labels": labels,
            "label_overlap_ns": 0.0,
            "malicious_node_events": self.malicious_node_events,
            "malicious_node_count": len(self.malicious_nodes),
            "node_labels": labels,
        }


def event_from_record(record: dict[str, Any]) -> dict[str, Any] | None:
    if str(record.get("type")) != "RECORD_EVENT":
        return None
    datum = record.get("datum") or {}
    props = datum.get("properties") or {}
    timestamp = datum.get("timestampNanos")
    if timestamp is None:
        return None
    return {
        "datum_type": datum.get("type") or "UNKNOWN",
        "timestamp_nanos": timestamp,
        "subject_uuid": datum.get("subject"),
        "object_uuid": datum.get("predicateObject"),
        "object2_uuid": datum.get("predicateObject2"),
        "exec": props.get("exec") or "UNKNOWN",
    }


def flush_window(
    acc: WindowAccumulator,
    windows: list[dict[str, Any]],
    event_totals: Counter[str],
    exec_totals: Counter[str],
) -> None:
    if acc.rows == 0:
        return
    row = acc.to_metadata()
    row["_event_counter"] = dict(acc.event_counter)
    row["_exec_counter"] = dict(acc.exec_counter)
    windows.append(row)
    event_totals.update(acc.event_counter)
    exec_totals.update(acc.exec_counter)


def write_outputs(
    out_dir: Path,
    windows: list[dict[str, Any]],
    event_vocab: list[str],
    exec_vocab: list[str],
    manifest: dict[str, Any],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    metadata_columns = [
        "window_id",
        "rows",
        "start_ns",
        "end_ns",
        "span_seconds",
        "source_files",
        "distinct_subjects",
        "distinct_objects",
        "distinct_execs",
        "distinct_event_types",
        "primary_label",
        "labels",
        "label_overlap_ns",
        "malicious_node_events",
        "malicious_node_count",
        "node_labels",
    ]
    event_columns = [f"event__{clean_value(value)}" for value in event_vocab]
    exec_columns = [f"exec__{clean_value(value)}" for value in exec_vocab]
    with (out_dir / "windows.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metadata_columns)
        writer.writeheader()
        for window in windows:
            writer.writerow({column: window.get(column, "") for column in metadata_columns})
    with (out_dir / "window_features.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=metadata_columns + event_columns + exec_columns)
        writer.writeheader()
        for window in windows:
            row = {column: window.get(column, "") for column in metadata_columns}
            total = max(int(window["rows"]), 1)
            event_counter = Counter(window["_event_counter"])
            exec_counter = Counter(window["_exec_counter"])
            for raw, column in zip(event_vocab, event_columns):
                row[column] = event_counter.get(raw, 0) / total
            for raw, column in zip(exec_vocab, exec_columns):
                row[column] = exec_counter.get(raw, 0) / total
            writer.writerow(row)
    with (out_dir / "labels_template.csv").open("w", encoding="utf-8", newline="") as handle:
        handle.write("start_ns,end_ns,label\n,,attack_stage_or_anomaly_name\n")
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(out_dir / "report.md", manifest)


def render_report(path: Path, manifest: dict[str, Any]) -> None:
    class_counts = manifest["class_counts"]
    lines = [
        "# Full Cadets Provenance Window Factory",
        "",
        "Generated: 2026-05-11",
        "",
        "## Decision",
        "",
        f"Status: **{manifest['decision']}**.",
        "",
        manifest["rationale"],
        "",
        "## Corpus Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Source files | {manifest['source_file_count']} |",
        f"| Edge rows | {manifest['edge_rows']} |",
        f"| Windows | {manifest['window_count']} |",
        f"| Timestamp span seconds | {manifest['span_seconds']:.3f} |",
        f"| Node-label rows | {manifest['node_label_count']} |",
        f"| Event vocabulary size | {len(manifest['event_vocab'])} |",
        f"| Exec vocabulary size | {len(manifest['exec_vocab'])} |",
        "",
        "## Class Support",
        "",
        "| Class | Windows |",
        "|---|---:|",
        f"| benign_or_unlabeled | {class_counts.get('benign_or_unlabeled', 0)} |",
        f"| attack_node_touch | {class_counts.get('attack_node_touch', 0)} |",
        "",
        "## Honest Limitation",
        "",
        "PIDSMaker labels are node-level labels. They identify windows touching known attack nodes, not full stage labels or complete benign/attack interval annotations.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--node-labels", type=Path, nargs="*", default=[])
    parser.add_argument("--events-per-window", type=int, default=50000)
    parser.add_argument("--top-event-k", type=int, default=32)
    parser.add_argument("--top-exec-k", type=int, default=32)
    parser.add_argument("--max-files", type=int, default=None)
    args = parser.parse_args()

    files = sorted(args.input_dir.glob("*.gz"), key=numeric_suffix)
    if args.max_files is not None:
        files = files[: args.max_files]
    if not files:
        raise FileNotFoundError(f"No .gz files found under {args.input_dir}")
    node_labels = load_node_labels(args.node_labels)

    windows: list[dict[str, Any]] = []
    event_totals: Counter[str] = Counter()
    exec_totals: Counter[str] = Counter()
    acc = WindowAccumulator(window_id=0)
    edge_rows = 0
    start_ns: int | None = None
    end_ns: int | None = None
    file_summaries: list[dict[str, Any]] = []

    for file_index, path in enumerate(files, start=1):
        file_events = 0
        print(f"FILE_START {file_index}/{len(files)} {path.name}", flush=True)
        with gzip.open(path, "rb") as handle:
            for record in reader(handle):
                event = event_from_record(record)
                if event is None:
                    continue
                timestamp = int(event["timestamp_nanos"])
                start_ns = timestamp if start_ns is None else min(start_ns, timestamp)
                end_ns = timestamp if end_ns is None else max(end_ns, timestamp)
                acc.add(event, path.name, node_labels)
                edge_rows += 1
                file_events += 1
                if acc.rows >= args.events_per_window:
                    flush_window(acc, windows, event_totals, exec_totals)
                    acc = WindowAccumulator(window_id=acc.window_id + 1)
        file_summaries.append(
            {"file": path.name, "file_index": file_index, "event_rows": file_events}
        )
        print(
            f"FILE_DONE {file_index}/{len(files)} {path.name} event_rows={file_events} total_edges={edge_rows}",
            flush=True,
        )
    flush_window(acc, windows, event_totals, exec_totals)

    event_vocab = [name for name, _ in event_totals.most_common(args.top_event_k)]
    exec_vocab = [name for name, _ in exec_totals.most_common(args.top_exec_k)]
    class_counts = Counter(window["primary_label"] for window in windows)
    min_class_count = min(class_counts.values()) if len(class_counts) >= 2 else 0
    decision = (
        "WINDOWS READY - DETECTOR ZOO CAN RUN"
        if min_class_count >= 5
        else "WINDOWS READY - DETECTOR CLAIM STILL BLOCKED"
    )
    rationale = (
        "The full-stream window table has enough class support for a detector-zoo gate."
        if min_class_count >= 5
        else "The full-stream window table was built, but class support is still too weak for an honest detector claim."
    )
    manifest = {
        "decision": decision,
        "rationale": rationale,
        "input_dir": str(args.input_dir),
        "source_files": [str(path) for path in files],
        "source_file_count": len(files),
        "edge_rows": edge_rows,
        "window_count": len(windows),
        "events_per_window": args.events_per_window,
        "node_label_count": len(node_labels),
        "class_counts": dict(class_counts),
        "span_seconds": ((end_ns or 0) - (start_ns or 0)) / 1e9,
        "event_vocab": event_vocab,
        "exec_vocab": exec_vocab,
        "file_summaries": file_summaries,
        "artifacts": {
            "windows": str(args.out_dir / "windows.csv"),
            "features": str(args.out_dir / "window_features.csv"),
            "manifest": str(args.out_dir / "manifest.json"),
            "report": str(args.out_dir / "report.md"),
        },
    }
    write_outputs(args.out_dir, windows, event_vocab, exec_vocab, manifest)
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
