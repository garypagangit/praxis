from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from praxis.provenance import WindowConfig, write_window_artifacts


def render_report(path: Path, manifest: dict[str, Any]) -> None:
    has_labels = manifest["labeled_window_count"] > 0
    enough_windows = manifest["window_count"] >= 10
    decision = (
        "SUPERVISED WINDOW FACTORY READY"
        if has_labels and enough_windows
        else "ARCHITECTURE READY - LABELS OR LONGER STREAMS NEEDED"
    )
    lines = [
        "# Provenance Window Factory",
        "",
        "Generated: 2026-05-11",
        "",
        "## Decision",
        "",
        f"Status: **{decision}**.",
        "",
        "This is an architecture unlock, not a scientific result. It creates reusable chronological provenance windows and fixed-width feature tables that graph SSL, TGN, drift, stage-routing, watermarking, and detector-zoo experiments can share.",
        "",
        "## Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
    ]
    for name, artifact_path in manifest["artifacts"].items():
        lines.append(f"| {name} | `{artifact_path}` |")
    lines.extend(
        [
            "",
            "## Corpus Summary",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Edge rows | {manifest['edge_rows']} |",
            f"| Windows | {manifest['window_count']} |",
            f"| Labeled windows | {manifest['labeled_window_count']} |",
            f"| Node-label rows | {manifest.get('node_label_count', 0)} |",
            f"| Node-labeled windows | {manifest.get('node_labeled_window_count', 0)} |",
            f"| Source files | {manifest['source_files']} |",
            f"| Timestamp span seconds | {manifest['span_seconds']:.3f} |",
            f"| Event vocabulary size | {len(manifest['event_vocab'])} |",
            f"| Exec vocabulary size | {len(manifest['exec_vocab'])} |",
            "",
            "## Experiments This Opens",
            "",
            "| Experiment | What this provides | Still missing for a defensible claim |",
            "|---|---|---|",
            "| Concept drift on provenance detectors | Chronological windows and drift-ready feature tables | Longer host streams plus labels/anomaly spans |",
            "| Continuous-time TGN | Sorted temporal windows and node/event vocabulary | Supervised anomaly target or self-supervised objective better than next-event type |",
            "| Contrastive SSL on provenance graphs | Shared window boundaries and feature vocabulary | Better node features and hard-negative policy |",
            "| Stage routing on provenance graphs | Common temporal windows for graph-stage prediction | Stage labels or reliable attack-window mapping |",
            "| Watermarking / MIA / adversarial robustness | Detector-zoo compatible window features | Stable detector suite and non-proxy labels |",
            "",
            "## Honest Limitation",
            "",
            "The current Cadets sample can validate plumbing, but it does not by itself prove drift, graph-stage prediction, or detector robustness. For that we need longer streams and labels.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--edges", type=Path, default=Path("tmp/cadets_edge_sample/edges.jsonl"))
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--node-labels", type=Path, nargs="*", default=None)
    parser.add_argument("--out-dir", type=Path, default=Path("runs/provenance-window-factory-20260511"))
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/PROVENANCE_WINDOW_FACTORY_20260511.md"),
    )
    parser.add_argument("--mode", choices=["event_count", "time"], default="event_count")
    parser.add_argument("--events-per-window", type=int, default=5000)
    parser.add_argument("--seconds-per-window", type=float, default=300.0)
    parser.add_argument("--top-event-k", type=int, default=32)
    parser.add_argument("--top-exec-k", type=int, default=32)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    config = WindowConfig(
        mode=args.mode,
        events_per_window=args.events_per_window,
        seconds_per_window=args.seconds_per_window,
        top_event_k=args.top_event_k,
        top_exec_k=args.top_exec_k,
    )
    manifest = write_window_artifacts(
        edges_path=args.edges,
        labels_path=args.labels,
        node_label_paths=args.node_labels,
        out_dir=args.out_dir,
        config=config,
        limit=args.limit,
    )
    render_report(args.report, manifest)
    print(json.dumps({"report": str(args.report), **manifest}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
