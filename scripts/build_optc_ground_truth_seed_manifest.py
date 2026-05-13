from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime, timezone
from pathlib import Path


DAY_HEADER_RE = re.compile(r'Day\s+(?P<day>\d+)\s+-\s+"(?P<title>[^"]+)"')
EVENT_RE = re.compile(
    r"^(?P<date>09/\d{2}/19)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+--\s+(?P<text>.*)$"
)
HOST_RE = re.compile(r"\b(?:sysclient\d{4}|dc1(?:\.systemia\.com)?)\b", re.IGNORECASE)


STAGE_RULES = [
    ("reconnaissance", re.compile(r"\b(scan|sweep|enumerat|find domain|domain controller|process listing|ipconfig|ps\b|winenum|trusted documents)\b", re.I)),
    ("credential_access", re.compile(r"\b(mimikatz|password|credential|hash|lsadump|gpp sysvol)\b", re.I)),
    ("privilege_escalation", re.compile(r"\b(bypassuac|privilege escalation|elevat|fodhelper|eventvwr)\b", re.I)),
    ("persistence", re.compile(r"\b(persist|registry|wmi subscription|debug registry)\b", re.I)),
    ("lateral_movement", re.compile(r"\b(pivot|invoke_wmi|wmi|spread|rdp)\b", re.I)),
    ("command_and_control", re.compile(r"\b(agent|check-in|listener|powershell empire|c2|callback)\b", re.I)),
    ("collection", re.compile(r"\b(screenshot|downloaded file|collect|data collection|search files)\b", re.I)),
    ("execution", re.compile(r"\b(ran|executed|opened|download runme|launcher|script)\b", re.I)),
]


def extract_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise SystemExit(
            "pypdf is required for PDF extraction. Install with: "
            "python -m pip install pypdf"
        ) from exc

    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def normalize_host(host: str) -> str:
    host = host.strip().lower()
    if host == "dc1.systemia.com":
        return "dc1"
    return host


def infer_stage(text: str) -> str:
    for stage, pattern in STAGE_RULES:
        if pattern.search(text):
            return stage
    return "attack_activity"


def parse_events(text: str) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    current_day = ""
    current_day_title = ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        day_match = DAY_HEADER_RE.search(line)
        if day_match:
            current_day = day_match.group("day")
            current_day_title = day_match.group("title")
            continue

        event_match = EVENT_RE.match(line)
        if event_match:
            if current is not None:
                events.append(current)
            current = {
                "date": event_match.group("date"),
                "time": event_match.group("time"),
                "description": event_match.group("text").strip(),
                "day": current_day,
                "day_title": current_day_title,
            }
            continue

        if current is not None:
            current["description"] = (current["description"] + " " + line).strip()

    if current is not None:
        events.append(current)
    return events


def enrich_events(events: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for idx, event in enumerate(events):
        dt = datetime.strptime(
            f"{event['date']} {event['time']}", "%m/%d/%y %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        description = event["description"]
        hosts = sorted({normalize_host(item) for item in HOST_RE.findall(description)})
        stage = infer_stage(description)
        rows.append(
            {
                "event_index": str(idx),
                "timestamp_utc": dt.isoformat().replace("+00:00", "Z"),
                "timestamp_ms": str(int(dt.timestamp() * 1000)),
                "timestamp_ns": str(int(dt.timestamp() * 1_000_000_000)),
                "day": event["day"],
                "day_title": event["day_title"],
                "stage_label": stage,
                "hosts": ";".join(hosts),
                "description": description,
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "event_index",
        "timestamp_utc",
        "timestamp_ms",
        "timestamp_ns",
        "day",
        "day_title",
        "stage_label",
        "hosts",
        "description",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: list[dict[str, str]], source_pdf: Path, output_csv: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stages: dict[str, int] = {}
    hosts: set[str] = set()
    days: dict[str, int] = {}
    for row in rows:
        stages[row["stage_label"]] = stages.get(row["stage_label"], 0) + 1
        days[row["day_title"]] = days.get(row["day_title"], 0) + 1
        hosts.update(host for host in row["hosts"].split(";") if host)

    first_ts = rows[0]["timestamp_utc"] if rows else "n/a"
    last_ts = rows[-1]["timestamp_utc"] if rows else "n/a"

    lines = [
        "# OpTC Ground-Truth Seed Manifest",
        "",
        "Generated: 2026-05-13",
        "",
        "Status: **seed manifest extracted; interval labels still require event-window attachment**",
        "",
        "## Source",
        "",
        f"- Ground truth PDF: `{source_pdf}`",
        f"- Parsed seed CSV: `{output_csv}`",
        "",
        "## Extraction Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Timestamped red-team events | `{len(rows)}` |",
        f"| Unique host mentions | `{len(hosts)}` |",
        f"| First timestamp | `{first_ts}` |",
        f"| Last timestamp | `{last_ts}` |",
        "",
        "## Day Counts",
        "",
        "| Day title | Events |",
        "|---|---:|",
    ]
    for day, count in sorted(days.items()):
        lines.append(f"| {day or 'unknown'} | `{count}` |")

    lines.extend(["", "## Heuristic Stage Counts", "", "| Stage | Events |", "|---|---:|"])
    for stage, count in sorted(stages.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {stage} | `{count}` |")

    lines.extend(
        [
            "",
            "## Decision",
            "",
            "This clears the first feasibility check for the OpTC label path: the public ground-truth document contains timestamped red-team activity that can seed an interval manifest.",
            "",
            "This is not yet a detector-ready label table. The next step is to map OpTC eCAR host events into the provenance window factory and attach windows around these seed timestamps. The heuristic stage labels are for triage only and must be audited before any stage-specific claim.",
            "",
            "## Next Gate",
            "",
            "1. Select one day and 3-5 hosts from the seed manifest.",
            "2. Download only the matching OpTC eCAR shard(s).",
            "3. Convert eCAR rows to the provenance window schema.",
            "4. Attach +/- interval windows around red-team timestamps and confirmed benign intervals outside red-team activity.",
            "5. Require >=20 benign and >=20 attack windows before detector training.",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pdf",
        type=Path,
        default=Path("external/datasets/optc/OpTCRedTeamGroundTruth.pdf"),
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=Path("runs/optc-ground-truth-seed-20260513/optc_ground_truth_seed_events.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/provenance_architecture/OPTC_GROUND_TRUTH_SEED_MANIFEST_20260513.md"),
    )
    args = parser.parse_args()

    text = extract_pdf_text(args.pdf)
    rows = enrich_events(parse_events(text))
    write_csv(args.out_csv, rows)
    write_report(args.report, rows, args.pdf, args.out_csv)
    print({"events": len(rows), "csv": str(args.out_csv), "report": str(args.report)})


if __name__ == "__main__":
    main()
