from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def iso_from_ns(value: int) -> str:
    return datetime.fromtimestamp(value / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def day_folder(timestamp_ns: int) -> str:
    dt = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=timezone.utc)
    folder_by_date = {
        "2019-09-23": "23Sep19-red",
        "2019-09-24": "24Sep19",
        "2019-09-25": "25Sept",
    }
    return folder_by_date.get(dt.strftime("%Y-%m-%d"), dt.strftime("%d%b%y"))


def normalize_host(value: Any) -> str:
    text = "" if value is None or pd.isna(value) else str(value).strip().lower()
    if "." in text:
        text = text.split(".", 1)[0]
    return text


def build_attack_intervals(
    seeds: pd.DataFrame,
    pre_minutes: float,
    post_minutes: float,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    pre_ns = int(pre_minutes * 60 * 1_000_000_000)
    post_ns = int(post_minutes * 60 * 1_000_000_000)
    for row in seeds.itertuples(index=False):
        center = int(row.timestamp_ns)
        host = normalize_host(row.hosts)
        stage = str(row.stage_label)
        start_ns = max(0, center - pre_ns)
        end_ns = center + post_ns
        rows.append(
            {
                "start_ns": start_ns,
                "end_ns": end_ns,
                "label": "attack",
                "stage_label": stage,
                "host": host,
                "event_index": int(row.event_index),
                "center_timestamp_ns": center,
                "center_timestamp_utc": iso_from_ns(center),
                "interval_start_utc": iso_from_ns(start_ns),
                "interval_end_utc": iso_from_ns(end_ns),
                "day": int(row.day),
                "day_title": str(row.day_title),
                "description": str(row.description),
            }
        )
    return pd.DataFrame(rows).sort_values(["start_ns", "host", "stage_label"]).reset_index(drop=True)


def build_targets(seeds: pd.DataFrame, top_hosts: int) -> pd.DataFrame:
    frame = seeds.copy()
    frame["host"] = frame["hosts"].map(normalize_host)
    grouped = (
        frame.groupby(["day", "day_title", "host"], dropna=False)
        .agg(
            seed_events=("event_index", "count"),
            first_ns=("timestamp_ns", "min"),
            last_ns=("timestamp_ns", "max"),
            stages=("stage_label", lambda values: ";".join(sorted(set(map(str, values))))),
        )
        .reset_index()
        .sort_values(["seed_events", "day", "host"], ascending=[False, True, True])
        .head(top_hosts)
    )
    grouped["first_utc"] = grouped["first_ns"].map(lambda value: iso_from_ns(int(value)))
    grouped["last_utc"] = grouped["last_ns"].map(lambda value: iso_from_ns(int(value)))
    grouped["suggested_ecar_folder"] = grouped["first_ns"].map(
        lambda value: f"external/datasets/optc/ecar/evaluation/{day_folder(int(value))}"
    )
    grouped["host_filter"] = grouped["host"]
    return grouped[
        [
            "day",
            "day_title",
            "host",
            "seed_events",
            "first_utc",
            "last_utc",
            "stages",
            "suggested_ecar_folder",
            "host_filter",
        ]
    ].reset_index(drop=True)


def overlap_ns(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def closest_attack_gap_ns(start_ns: float, end_ns: float, attacks: pd.DataFrame) -> float:
    if attacks.empty:
        return float("inf")
    gaps = []
    for attack in attacks.itertuples(index=False):
        if overlap_ns(start_ns, end_ns, float(attack.start_ns), float(attack.end_ns)) > 0:
            return 0.0
        gaps.append(min(abs(start_ns - float(attack.end_ns)), abs(float(attack.start_ns) - end_ns)))
    return float(min(gaps)) if gaps else float("inf")


def label_windows(windows_path: Path, attacks: pd.DataFrame, gray_minutes: float) -> pd.DataFrame:
    windows = pd.read_csv(windows_path)
    gray_ns = gray_minutes * 60 * 1_000_000_000
    rows: list[dict[str, Any]] = []
    for row in windows.itertuples(index=False):
        start_ns = float(row.start_ns)
        end_ns = float(row.end_ns)
        attack_overlap = 0.0
        stages: set[str] = set()
        hosts: set[str] = set()
        for attack in attacks.itertuples(index=False):
            overlap = overlap_ns(start_ns, end_ns, float(attack.start_ns), float(attack.end_ns))
            if overlap > 0:
                attack_overlap += overlap
                stages.add(str(attack.stage_label))
                hosts.add(str(attack.host))
        if attack_overlap > 0:
            label = "attack"
        elif closest_attack_gap_ns(start_ns, end_ns, attacks) >= gray_ns:
            label = "background"
        else:
            label = "gray_buffer"
        rows.append(
            {
                "window_id": int(row.window_id),
                "start_ns": int(start_ns),
                "end_ns": int(end_ns),
                "label": label,
                "attack_overlap_seconds": attack_overlap / 1_000_000_000,
                "attack_stages": ";".join(sorted(stages)),
                "attack_hosts": ";".join(sorted(hosts)),
            }
        )
    return pd.DataFrame(rows)


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# OpTC Label Acquisition Plan",
        "",
        "Generated: 2026-05-14",
        "",
        "Status: **label path concrete; eCAR shard still required**",
        "",
        "## How We Get Labels",
        "",
        "1. Use the public OpTC red-team ground-truth PDF as the attack seed source.",
        "2. Expand each timestamped red-team event into a padded attack interval.",
        "3. Download the matching OpTC eCAR host/day shard from the public release.",
        "4. Convert eCAR JSON to normalized provenance edges.",
        "5. Build chronological windows and attach attack intervals.",
        "6. Treat windows outside attack intervals and outside the gray buffer as background only for a red-team-window detection claim.",
        "",
        "This produces an honest binary target: `attack-window` vs `background/no-red-team-overlap`. It does not produce perfect event-level malicious labels.",
        "",
        "## Source Anchors",
        "",
        "- Official release: `https://github.com/FiveDirections/OpTC-data`",
        "- Data location from official release: Google Drive folder linked in the OpTC README.",
        "- Dataset structure note: COMIDDS documents `eCar/benign`, `eCar/evaluation`, and `eCar/short`, and notes that the ground truth file is needed for manual labels.",
        "- Optional later upgrade: use published third-party OpTC label projects only after auditing compatibility with this window schema.",
        "",
        "## Generated Artifacts",
        "",
        f"- Attack intervals: `{summary['attack_intervals_path']}`",
        f"- Target host/day shortlist: `{summary['targets_path']}`",
        f"- Optional window labels: `{summary.get('window_labels_path') or 'not generated; pass --windows after eCAR windowing'}`",
        "",
        "## Seed Summary",
        "",
        f"- Timestamped seed events: `{summary['seed_events']}`",
        f"- Attack interval padding: `-{summary['pre_minutes']} / +{summary['post_minutes']}` minutes",
        f"- Unique seed hosts: `{summary['unique_hosts']}`",
        f"- Covered days: `{summary['covered_days']}`",
        "",
        "## First Download Target",
        "",
        "| Day | Host | Seed events | eCAR folder | Host filter |",
        "|---:|---|---:|---|---|",
    ]
    for item in summary["targets"]:
        lines.append(
            f"| `{item['day']}` | `{item['host']}` | `{item['seed_events']}` | `{item['suggested_ecar_folder']}` | `{item['host_filter']}` |"
        )
    lines.extend(
        [
            "",
            "## Window Label Gate",
            "",
            "| Check | Required |",
            "|---|---:|",
            "| Attack windows | `>=20` |",
            "| Background windows | `>=20` |",
            "| Gray-buffer windows | reported/excluded from supervised training |",
            "| Split support | train/validation/test each include the claimed positive class |",
            "",
            "## Targeted Download Command",
            "",
            "Install `gdown` into the diagnostic environment once if needed, then download only the target host/day folder:",
            "",
            "```powershell",
            ".\\.venv-diag\\Scripts\\python.exe -m pip install gdown",
            ".\\.venv-diag\\Scripts\\python.exe .\\scripts\\download_optc_target_ecar.py --host sysclient0501 --day 2",
            "```",
            "",
            "## Run Command After Download",
            "",
            "```powershell",
            "powershell -ExecutionPolicy Bypass -File .\\scripts\\build_optc_window_gate.ps1 `",
            "  -Inputs external\\datasets\\optc\\ecar\\evaluation\\24Sep19 `",
            "  -Labels runs\\optc-label-acquisition-20260514\\optc_attack_intervals.csv `",
            "  -HostFilter sysclient0501 `",
            "  -OutRoot runs\\optc-window-gate-20260514 `",
            "  -Limit 200000 `",
            "  -EventsPerWindow 5000",
            "```",
            "",
            "Then rerun this script with `--windows runs\\optc-window-gate-20260514\\windows.csv` to count `attack`, `background`, and `gray_buffer` support.",
            "",
            "## Claim Guard",
            "",
            "Do not call this event-level malicious labeling. The defensible claim is window-level red-team interval overlap against background windows from the same OpTC release.",
        ]
    )
    if "window_support" in summary:
        lines.extend(
            [
                "",
                "## Current Window Support",
                "",
                "| Label | Windows |",
                "|---|---:|",
            ]
        )
        for label, count in summary["window_support"].items():
            lines.append(f"| `{label}` | `{count}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed-csv",
        type=Path,
        default=Path("reports/provenance_architecture/optc_ground_truth_seed_events_20260513.csv"),
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs/optc-label-acquisition-20260514"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/OPTC_LABEL_ACQUISITION_PLAN_20260514.md"),
    )
    parser.add_argument("--pre-minutes", type=float, default=15.0)
    parser.add_argument("--post-minutes", type=float, default=15.0)
    parser.add_argument("--gray-minutes", type=float, default=30.0)
    parser.add_argument("--top-hosts", type=int, default=5)
    parser.add_argument("--windows", type=Path, default=None)
    args = parser.parse_args()

    seeds = pd.read_csv(args.seed_csv)
    attacks = build_attack_intervals(seeds, args.pre_minutes, args.post_minutes)
    targets = build_targets(seeds, args.top_hosts)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    attack_path = args.out_dir / "optc_attack_intervals.csv"
    targets_path = args.out_dir / "optc_target_host_days.csv"
    attacks.to_csv(attack_path, index=False)
    targets.to_csv(targets_path, index=False)

    summary: dict[str, Any] = {
        "seed_csv": str(args.seed_csv),
        "seed_events": int(len(seeds)),
        "unique_hosts": int(seeds["hosts"].map(normalize_host).nunique()),
        "covered_days": int(seeds["day"].nunique()),
        "pre_minutes": float(args.pre_minutes),
        "post_minutes": float(args.post_minutes),
        "gray_minutes": float(args.gray_minutes),
        "attack_intervals_path": str(attack_path),
        "targets_path": str(targets_path),
        "targets": targets.to_dict("records"),
    }
    if args.windows:
        labels = label_windows(args.windows, attacks, args.gray_minutes)
        window_labels_path = args.out_dir / "optc_window_labels.csv"
        labels.to_csv(window_labels_path, index=False)
        summary["window_labels_path"] = str(window_labels_path)
        summary["window_support"] = {
            str(k): int(v) for k, v in labels["label"].value_counts().sort_index().items()
        }
    summary_path = args.out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(args.report, summary)
    print(json.dumps({"report": str(args.report), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
