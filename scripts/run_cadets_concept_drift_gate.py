from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def read_edges(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                row = json.loads(line)
                props = row.get("properties") or {}
                rows.append(
                    {
                        "timestamp_nanos": row.get("timestamp_nanos"),
                        "sequence": row.get("sequence"),
                        "record_index": row.get("record_index"),
                        "datum_type": row.get("datum_type") or "UNKNOWN",
                        "exec": props.get("exec") or "UNKNOWN",
                        "source_file": row.get("source_file") or "UNKNOWN",
                        "subject_uuid": row.get("subject_uuid") or "UNKNOWN",
                        "object_uuid": row.get("object_uuid") or "UNKNOWN",
                    }
                )
    frame = pd.DataFrame(rows)
    frame["timestamp_nanos"] = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    frame = frame.dropna(subset=["timestamp_nanos"]).sort_values(
        ["timestamp_nanos", "sequence", "record_index"]
    )
    return frame.reset_index(drop=True)


def distribution(values: pd.Series, vocabulary: list[str]) -> np.ndarray:
    counts = Counter(values.astype(str))
    arr = np.array([counts.get(item, 0) for item in vocabulary], dtype=np.float64)
    if arr.sum() == 0:
        return np.ones(len(vocabulary), dtype=np.float64) / max(len(vocabulary), 1)
    return arr / arr.sum()


def js_divergence(p: np.ndarray, q: np.ndarray) -> float:
    eps = 1e-12
    p = np.clip(p, eps, 1.0)
    q = np.clip(q, eps, 1.0)
    p = p / p.sum()
    q = q / q.sum()
    m = 0.5 * (p + q)
    return float(
        0.5 * np.sum(p * np.log2(p / m)) + 0.5 * np.sum(q * np.log2(q / m))
    )


def window_summary(frame: pd.DataFrame, window_count: int) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = frame.copy()
    frame["window"] = pd.qcut(
        np.arange(len(frame)), q=window_count, labels=False, duplicates="drop"
    )
    event_vocab = sorted(frame["datum_type"].astype(str).unique())
    exec_vocab = [name for name, _ in Counter(frame["exec"].astype(str)).most_common(30)]
    windows = []
    for window_id, group in frame.groupby("window", sort=True):
        start_ns = int(group["timestamp_nanos"].min())
        end_ns = int(group["timestamp_nanos"].max())
        windows.append(
            {
                "window": int(window_id),
                "rows": int(len(group)),
                "start_ns": start_ns,
                "end_ns": end_ns,
                "span_seconds": (end_ns - start_ns) / 1e9,
                "top_events": Counter(group["datum_type"].astype(str)).most_common(5),
                "top_execs": Counter(group["exec"].astype(str)).most_common(5),
            }
        )

    event_distributions = [
        distribution(group["datum_type"], event_vocab)
        for _, group in frame.groupby("window", sort=True)
    ]
    exec_distributions = [
        distribution(group["exec"], exec_vocab)
        for _, group in frame.groupby("window", sort=True)
    ]
    adjacent_event_js = [
        js_divergence(event_distributions[idx], event_distributions[idx + 1])
        for idx in range(len(event_distributions) - 1)
    ]
    adjacent_exec_js = [
        js_divergence(exec_distributions[idx], exec_distributions[idx + 1])
        for idx in range(len(exec_distributions) - 1)
    ]
    drift = {
        "event_vocab_size": len(event_vocab),
        "exec_vocab_size_top30": len(exec_vocab),
        "adjacent_event_js": adjacent_event_js,
        "adjacent_exec_js_top30": adjacent_exec_js,
        "first_last_event_js": js_divergence(event_distributions[0], event_distributions[-1]),
        "first_last_exec_js_top30": js_divergence(exec_distributions[0], exec_distributions[-1]),
    }
    return pd.DataFrame(windows), drift


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets Concept Drift Gate",
        "",
        "Generated: 2026-05-10",
        "",
        "## Decision",
        "",
        f"Gate result: `{summary['decision']}`",
        "",
        summary["rationale"],
        "",
        "## Corpus",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Edge rows | {summary['rows']} |",
        f"| Source files | {summary['source_files']} |",
        f"| Timestamp span seconds | {summary['span_seconds']:.3f} |",
        f"| Event types | {summary['event_types']} |",
        f"| Exec values | {summary['exec_values']} |",
        "",
        "## Drift Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Adjacent event JS max | {summary['drift']['adjacent_event_js_max']:.4f} |",
        f"| Adjacent exec JS max | {summary['drift']['adjacent_exec_js_max']:.4f} |",
        f"| First-last event JS | {summary['drift']['first_last_event_js']:.4f} |",
        f"| First-last exec JS | {summary['drift']['first_last_exec_js']:.4f} |",
        "",
        "## Chronological Windows",
        "",
        "| Window | Rows | Span seconds | Top events | Top execs |",
        "|---:|---:|---:|---|---|",
    ]
    for row in summary["windows"]:
        top_events = ", ".join(f"{name}:{count}" for name, count in row["top_events"])
        top_execs = ", ".join(f"{name}:{count}" for name, count in row["top_execs"])
        lines.append(
            f"| {row['window']} | {row['rows']} | {row['span_seconds']:.3f} | "
            f"{top_events} | {top_execs} |"
        )

    lines.extend(
        [
            "",
            "## Next Logical Step",
            "",
            "Use this only as a parser/windowing smoke test. A publishable provenance concept-drift experiment needs longer chronological host streams, attack labels or anomaly windows, and at least one detector family. This sample is too short to support a drift claim by itself.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--edges",
        type=Path,
        default=Path("tmp/cadets_edge_sample/edges.jsonl"),
    )
    parser.add_argument("--windows", type=int, default=5)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/cadets-concept-drift-gate-20260510"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path(
            "reports/concept_drift_provenance_detectors/CADETS_DRIFT_GATE_20260510.md"
        ),
    )
    args = parser.parse_args()

    frame = read_edges(args.edges)
    windows, drift = window_summary(frame, args.windows)
    span_seconds = (
        float(frame["timestamp_nanos"].max() - frame["timestamp_nanos"].min()) / 1e9
    )
    source_files = int(frame["source_file"].nunique())
    enough_temporal_scope = span_seconds >= 3600 and source_files >= 3
    decision = (
        "PROCEED - TEMPORAL DRIFT DATA READY"
        if enough_temporal_scope
        else "PIPELINE READY - DRIFT DATA INSUFFICIENT"
    )
    rationale = (
        "The edge table has enough chronological scope for a first detector drift pilot."
        if enough_temporal_scope
        else "The Cadets parser and chronological windowing work, but this local sample spans only a short interval and should not be treated as a real concept-drift benchmark."
    )
    adjacent_event_js = drift["adjacent_event_js"]
    adjacent_exec_js = drift["adjacent_exec_js_top30"]
    summary = {
        "decision": decision,
        "rationale": rationale,
        "rows": int(len(frame)),
        "source_files": source_files,
        "span_seconds": span_seconds,
        "event_types": int(frame["datum_type"].nunique()),
        "exec_values": int(frame["exec"].nunique()),
        "drift": {
            "adjacent_event_js": adjacent_event_js,
            "adjacent_exec_js_top30": adjacent_exec_js,
            "adjacent_event_js_max": max(adjacent_event_js) if adjacent_event_js else math.nan,
            "adjacent_exec_js_max": max(adjacent_exec_js) if adjacent_exec_js else math.nan,
            "first_last_event_js": drift["first_last_event_js"],
            "first_last_exec_js": drift["first_last_exec_js_top30"],
        },
        "windows": windows.to_dict("records"),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    windows.to_csv(args.out_dir / "windows.csv", index=False)
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), "decision": decision}, indent=2))


if __name__ == "__main__":
    main()
