from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


def read_jsonl(path: Path, limit: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for idx, line in enumerate(handle):
            if limit is not None and idx >= limit:
                break
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def window_counts(frame: pd.DataFrame, seconds: float) -> dict[str, Any]:
    timestamps = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    span = int(seconds * 1_000_000_000)
    buckets = ((timestamps - timestamps.min()) // span).astype("int64")
    counts = buckets.value_counts().sort_index()
    return {
        "seconds": seconds,
        "window_count": int(counts.shape[0]),
        "min_edges": int(counts.min()),
        "median_edges": float(counts.median()),
        "max_edges": int(counts.max()),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets TGN Temporal Gate",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Temporal Integrity",
        "",
        f"- Edges: `{summary['edge_count']}`",
        f"- Timestamp missing: `{summary['timestamp_missing']}`",
        f"- Record-order monotonic: `{summary['record_order_monotonic']}`",
        f"- Sorted-order monotonic: `{summary['sorted_order_monotonic']}`",
        f"- Span seconds: `{summary['span_seconds']:.3f}`",
        f"- Duplicate timestamp rate: `{summary['duplicate_timestamp_rate']:.4f}`",
        "",
        "## Candidate Windows",
        "",
        "| Window seconds | Count | Min edges | Median edges | Max edges |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in summary["window_counts"]:
        lines.append(
            f"| `{row['seconds']}` | `{row['window_count']}` | `{row['min_edges']}` | `{row['median_edges']:.1f}` | `{row['max_edges']}` |"
        )
    lines.extend(
        [
            "",
            "## Chronological Split",
            "",
            "| Split | Rows | Timestamp min | Timestamp max |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in summary["chronological_split"]:
        lines.append(
            f"| `{row['split']}` | `{row['rows']}` | `{row['timestamp_min']}` | `{row['timestamp_max']}` |"
        )
    lines.extend(["", "## Recommendation", "", summary["recommendation"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir", type=Path, default=Path("tmp") / "cadets_edge_sample"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "cadets-tgn-temporal-gate-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "continuous_time_tgn_apt_provenance"
        / "CADETS_TGN_TEMPORAL_GATE_20260509.md",
    )
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    frame = pd.DataFrame(read_jsonl(args.input_dir / "edges.jsonl", args.limit))
    timestamps = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    sorted_frame = frame.assign(_timestamp=timestamps).sort_values(
        ["_timestamp", "sequence", "record_index"]
    )
    sorted_timestamps = sorted_frame["_timestamp"]
    n = len(sorted_frame)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    splits = {
        "train": sorted_frame.iloc[:train_end],
        "val": sorted_frame.iloc[train_end:val_end],
        "test": sorted_frame.iloc[val_end:],
    }
    split_rows = []
    for name, split in splits.items():
        split_rows.append(
            {
                "split": name,
                "rows": int(len(split)),
                "timestamp_min": int(split["_timestamp"].min()),
                "timestamp_max": int(split["_timestamp"].max()),
            }
        )
    pass_gate = (
        int(timestamps.isna().sum()) == 0
        and bool(sorted_timestamps.is_monotonic_increasing)
        and n >= 50000
        and split_rows[0]["timestamp_max"] <= split_rows[1]["timestamp_min"]
        and split_rows[1]["timestamp_max"] <= split_rows[2]["timestamp_min"]
    )
    summary: dict[str, Any] = {
        "decision": (
            "PASS - TGN TEMPORAL SCAFFOLD READY"
            if pass_gate
            else "BLOCKED - TEMPORAL INTEGRITY ISSUE"
        ),
        "edge_count": int(n),
        "timestamp_missing": int(timestamps.isna().sum()),
        "record_order_monotonic": bool(timestamps.dropna().is_monotonic_increasing),
        "sorted_order_monotonic": bool(sorted_timestamps.is_monotonic_increasing),
        "timestamp_min": int(timestamps.min()),
        "timestamp_max": int(timestamps.max()),
        "span_seconds": float((timestamps.max() - timestamps.min()) / 1_000_000_000),
        "duplicate_timestamp_rate": float(timestamps.duplicated().mean()),
        "window_counts": [
            window_counts(frame, seconds) for seconds in [0.1, 0.5, 1.0, 5.0, 10.0]
        ],
        "chronological_split": split_rows,
        "recommendation": (
            "Proceed to a tiny continuous-time edge prediction or next-event-type pilot after sorting by timestamp. Do not use record order as time order."
            if pass_gate
            else "Repair timestamps or split construction before TGN work."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
