"""Acquire the small public ProvICS subset and qualify actual bytes before fitting.

This deliberately does not download the large provenance/PCAP files, use stored
HF credentials, solve access challenges, infer successful attacks from stage
names, or turn absent measurements into classification results.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import pandas as pd
import requests

REPOSITORY = "trucyberlab/multimodal-ICS-provenance"
FILES = [
    "README.md",
    "benign48h/physical_state.csv",
    "attack22h/physical_state.csv",
    *[f"attack22h/ground_truth/c{i}_ground_truth.csv" for i in range(1, 5)],
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def outcome_status(description: str) -> str:
    """Only screen explicit annotation flags; do not certify successful execution."""
    text = str(description).lower()
    if "skipped" in text:
        return "explicitly_skipped"
    if "failed" in text or "aborted" in text:
        return "contains_failure_or_abort_requires_review"
    return "execution_described_outcome_unverified"


def download_one(root: Path, relative: str, revision: str) -> dict:
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://huggingface.co/datasets/{REPOSITORY}/resolve/{revision}/{relative}"
    receipt = {"file": relative, "source_url": url, "revision_requested": revision}
    if destination.is_file():
        receipt.update(status="existing_bytes", bytes=destination.stat().st_size,
                       sha256=sha256(destination))
        return receipt
    temporary = destination.with_suffix(destination.suffix + ".part")
    started = time.monotonic()
    try:
        with requests.get(url, stream=True, timeout=(6, 20)) as response:
            receipt["http_status"] = response.status_code
            response.raise_for_status()
            receipt["resolved_revision_header"] = response.headers.get("X-Repo-Commit")
            # Prevent an unexpected large-file redirect from consuming resources.
            if int(response.headers.get("Content-Length", "0")) > 100_000_000:
                raise ValueError("Unexpected file size above 100 MB subset cap")
            size = 0
            with temporary.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    if time.monotonic() - started > 120:
                        raise TimeoutError("Per-file elapsed-time cap exceeded")
                    size += len(chunk)
                    if size > 100_000_000:
                        raise ValueError("Per-file size cap exceeded")
                    stream.write(chunk)
            # Detect a successful HTTP response that actually contains an error page.
            prefix = temporary.read_bytes()[:200].lower()
            if b"<html" in prefix or b"<!doctype html" in prefix:
                raise ValueError("HTML response is not the requested raw data")
            temporary.replace(destination)
            receipt.update(status="downloaded", bytes=size, sha256=sha256(destination))
    except Exception as exc:
        receipt.update(status="unavailable", error_type=type(exc).__name__)
        # Only our exact partial file can be removed; no recursive deletion.
        if temporary.is_file() and temporary.resolve().is_relative_to(root.resolve()):
            temporary.unlink()
    receipt["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return receipt


def inspect_signal(path: Path) -> tuple[dict, pd.DatetimeIndex | None]:
    table = pd.read_csv(path)
    report = {"rows": len(table), "columns": list(table.columns),
              "numeric_columns": list(table.select_dtypes("number").columns),
              "null_counts": {str(k): int(v) for k, v in table.isna().sum().items()}}
    candidates = [c for c in table if str(c).lower() in
                  {"time", "timestamp", "_time", "datetime", "date_time"}]
    if len(candidates) != 1:
        report["clock_status"] = "manual_schema_review_required"
        return report, None
    column = candidates[0]
    # Numeric clock units must be supplied by source documentation, not guessed.
    if pd.api.types.is_numeric_dtype(table[column]):
        report["clock_status"] = "numeric_clock_units_require_review"
        return report, None
    timestamps = pd.DatetimeIndex(pd.to_datetime(table[column], utc=True, errors="coerce"))
    valid = timestamps.dropna()
    report.update(clock_status="parsed_utc", timestamp_column=column,
                  invalid_timestamps=int(timestamps.isna().sum()),
                  duplicate_timestamps=int(valid.duplicated().sum()),
                  monotonic=valid.is_monotonic_increasing,
                  first_timestamp=str(valid.min()), last_timestamp=str(valid.max()))
    return report, valid


def qualify(root: Path, receipts: list[dict]) -> dict:
    report = {"usable_for_new_validation": False, "model_fits": 0,
              "source": REPOSITORY, "signal_files": {}, "annotation_files": {},
              "scope": "ICS physical-signal development; not enterprise exfiltration",
              "independent_acquisition_sessions_claimed_by_source": 1,
              "successful_attack_count_verified": None}
    successful = {r["file"] for r in receipts if r["status"] in {"existing_bytes", "downloaded"}}
    required = set(FILES)
    missing = sorted(required - successful)
    report["missing_files"] = missing
    attack_times = None
    for relative in ["benign48h/physical_state.csv", "attack22h/physical_state.csv"]:
        if relative in successful:
            try:
                details, times = inspect_signal(root / relative)
                report["signal_files"][relative] = details
                if relative.startswith("attack"):
                    attack_times = times
            except Exception as exc:
                report["signal_files"][relative] = {"schema_error": type(exc).__name__}
    annotated = []
    for relative in FILES[3:]:
        if relative not in successful:
            continue
        try:
            table = pd.read_csv(root / relative)
            required_columns = {"start", "end", "campaign", "sub_phase", "tactic", "description"}
            if not required_columns.issubset(table.columns):
                raise ValueError("Ground truth schema differs from source preview")
            counts = table.description.map(outcome_status).value_counts().to_dict()
            report["annotation_files"][relative] = {"rows": len(table), "outcome_screen_counts": counts}
            for row in table.to_dict("records"):
                start = pd.to_datetime(row["start"], utc=True)
                end = pd.to_datetime(row["end"], utc=True)
                annotated.append({"campaign": row["campaign"], "sub_phase": row["sub_phase"],
                                  "tactic": None if pd.isna(row["tactic"]) else row["tactic"],
                                  "duration_seconds": (end - start).total_seconds(),
                                  "outcome_screen": outcome_status(row["description"]),
                                  "physical_rows_in_interval": None if attack_times is None else
                                  int(((attack_times >= start) & (attack_times < end)).sum())})
        except Exception as exc:
            report["annotation_files"][relative] = {"schema_error": type(exc).__name__}
    report["annotation_intervals"] = annotated
    report["campaign_scripts_observed"] = len({r["campaign"] for r in annotated})
    report["gate"] = "acquisition_incomplete" if missing else "manual_outcome_and_clock_qualification_required"
    report["interpretation"] = (
        "Physical measurements alone do not establish cross-host movement, acquisition costs, "
        "log arrival times, or completed exfiltration. Source phase names are not execution receipts. "
        "Campaign scripts in one recording do not establish independent repeated campaigns."
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--revision", default="main")
    args = parser.parse_args()
    args.data_root.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        receipts = list(executor.map(lambda f: download_one(args.data_root, f, args.revision), FILES))
    payload = {"attempt_utc": datetime.now(timezone.utc).isoformat(), "files": receipts,
               "data_credentials_used": False, "raw_files_committed": False}
    (args.report_dir / "provics_acquisition.json").write_text(json.dumps(payload, indent=2), encoding="utf8")
    report = qualify(args.data_root, receipts)
    (args.report_dir / "provics_qualification.json").write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps({"gate": report["gate"], "downloaded_or_existing_files":
                      sum(r["status"] != "unavailable" for r in receipts),
                      "model_fits": 0}, indent=2))


if __name__ == "__main__":
    main()
