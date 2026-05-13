from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

EXPECTED_COLUMNS = ["LogEvent", "Activity", "Stage", "DefenderResponse", "Signature"]


def sniff_file(path: Path, max_rows: int) -> dict:
    counts = {
        "rows_seen": 0,
        "activity": Counter(),
        "stage": Counter(),
        "defender_response": Counter(),
        "signature": Counter(),
    }
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        for row in reader:
            counts["rows_seen"] += 1
            counts["activity"][row.get("Activity", "")] += 1
            counts["stage"][row.get("Stage", "")] += 1
            counts["defender_response"][row.get("DefenderResponse", "")] += 1
            counts["signature"][row.get("Signature", "")] += 1
            if counts["rows_seen"] >= max_rows:
                break
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "columns": columns,
        "columns_match_expected": columns == EXPECTED_COLUMNS,
        "rows_seen": counts["rows_seen"],
        "activity": dict(counts["activity"].most_common(20)),
        "stage": dict(counts["stage"].most_common(20)),
        "defender_response": dict(counts["defender_response"].most_common(20)),
        "signature": dict(counts["signature"].most_common(20)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inventory Unraveled host logs as a proxy input gate for contrastive SSL."
    )
    parser.add_argument("--input-root", required=True, help="Host-log root directory.")
    parser.add_argument(
        "--out-dir", required=True, help="Directory for gate artifacts."
    )
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--max-rows-per-file", type=int, default=5000)
    args = parser.parse_args()

    root = Path(args.input_root)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(path for path in root.rglob("*") if path.is_file())
    selected = files[: args.max_files]
    summaries = [sniff_file(path, args.max_rows_per_file) for path in selected]

    by_family: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "bytes": 0})
    stage_total: Counter[str] = Counter()
    activity_total: Counter[str] = Counter()
    columns_ok = 0
    rows_seen = 0
    for summary in summaries:
        family = Path(summary["path"]).parent.name
        by_family[family]["files"] += 1
        by_family[family]["bytes"] += int(summary["bytes"])
        rows_seen += int(summary["rows_seen"])
        if summary["columns_match_expected"]:
            columns_ok += 1
        stage_total.update(summary["stage"])
        activity_total.update(summary["activity"])

    result = {
        "input_root": str(root),
        "files_total": len(files),
        "files_sampled": len(selected),
        "bytes_sampled": sum(int(summary["bytes"]) for summary in summaries),
        "rows_seen": rows_seen,
        "families": dict(sorted(by_family.items())),
        "columns_match_expected_files": columns_ok,
        "stage_counts_sample": dict(stage_total.most_common(30)),
        "activity_counts_sample": dict(activity_total.most_common(30)),
        "gate_decision": {
            "unraveled_host_log_proxy": "pass",
            "darpa_tc_or_optc_provenance_graphs": "blocked",
            "blocker": "AWS currently holds metadata/repos for DARPA TC and OpTC, not the full event/provenance graph data.",
            "praxis_candidate": "not_yet",
        },
        "file_summaries": summaries,
    }

    (out_dir / "contrastive_ssl_input_gate_summary.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    report = [
        "# Contrastive SSL - Input Gate",
        "",
        f"Input root: `{root}`",
        "",
        "## Result",
        "",
        f"- Files available locally: `{len(files)}`",
        f"- Files sampled: `{len(selected)}`",
        f"- Rows sampled: `{rows_seen}`",
        f"- Sampled bytes: `{result['bytes_sampled']}`",
        f"- Expected CSV schema files: `{columns_ok}/{len(selected)}`",
        "- Unraveled host-log proxy: `PASS`",
        "- DARPA TC / OpTC provenance graph data: `BLOCKED`",
        "",
        "## Sample Stage Counts",
        "",
        "| Stage | Count |",
        "|---|---:|",
    ]
    for stage, count in stage_total.most_common(12):
        report.append(f"| {stage or '<blank>'} | {count} |")
    report.extend(
        [
            "",
            "## Decision",
            "",
            "The local/S3 Unraveled host logs can support a proxy experiment based on temporal event sequences "
            "or derived co-occurrence graphs. They are not a substitute for DARPA TC or OpTC provenance graphs "
            "because they do not directly provide typed process/file/socket edge records.",
            "",
            "Recommended next move: keep the full GraphCL/BGRL provenance-graph claim blocked until a DARPA TC "
            "or OpTC subset is mirrored. In the meantime, build a small proxy graph constructor from Unraveled "
            "host-log events only if we need a low-cost representation-learning spike.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(result["gate_decision"], indent=2))


if __name__ == "__main__":
    main()
