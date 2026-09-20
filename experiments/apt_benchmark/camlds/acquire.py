"""Acquire raw scenarios or CRC/SHA-verified selected audit ZIP members privately.

Whole publisher archive checksums are verified only for complete downloads.
The selected-member route records, but does not verify, those archive checksums.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request

from ..acquire_ait import RangeReader, central_directory, fetch_member
from ..robustness.casino_events import _fetch_audit as fetch_large_audit_member

RECORD = "https://zenodo.org/api/records/18861762"
COMMIT = "44028d8bd40a4a1d8bbbc6ee33261d47cb433827"
REPOSITORY = "https://raw.githubusercontent.com/ait-aecid/attack-manifestations-interpretation"


def digest(path, algorithm="sha256"):
    result = hashlib.new(algorithm)
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def get(url, path):
    request = urllib.request.Request(url, headers={"User-Agent": "Praxis-dataset-qualification/1.0"})
    temporary = path.with_suffix(path.suffix + ".part")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                for block in iter(lambda: response.read(1024 * 1024), b""):
                    output.write(block)
            temporary.replace(path)
            return
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def download(entry, root):
    path = root / entry["key"]
    expected = entry["checksum"].split(":", 1)[1]
    reused = path.exists() and path.stat().st_size == entry["size"] and digest(path, "md5") == expected
    if not reused:
        if path.exists():
            raise ValueError(f"Existing artifact fails publisher checksum: {path.name}")
        get(f"https://zenodo.org/records/18861762/files/{entry['key']}?download=1", path)
    if path.stat().st_size != entry["size"] or digest(path, "md5") != expected:
        raise ValueError(f"Downloaded artifact fails publisher checksum: {path.name}")
    result = {"file": path.name, "bytes": path.stat().st_size, "publisher_md5": expected,
              "sha256": digest(path), "url": entry["links"]["self"], "reused": reused}
    print(json.dumps({"verified": path.name, "bytes": path.stat().st_size}), flush=True)
    return result


def select_members(entries):
    """Complete defender audit streams, plus attacker chronology as labels only."""
    return [entry for entry in entries if not entry["name"].endswith("/") and
            (("/logs/" in entry["name"] and "/audit/audit.log" in entry["name"]
              and "/attacker/" not in entry["name"])
             or entry["name"].endswith("/attacker/logs/attackmate.json"))]


def download_members(entry, root, reader):
    url = f"https://zenodo.org/records/18861762/files/{entry['key']}?download=1"
    entries, directory = central_directory(reader, url, entry["size"])
    chosen = select_members(entries)
    if not chosen or not any(x["name"].endswith("/attackmate.json") for x in chosen):
        raise ValueError("Missing audit streams or source chronology")
    source_root = root / "raw"
    scenario = entry["key"].removesuffix(".zip")
    receipt_path = root / (scenario + ".acquisition.json")
    prior = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
    old_by_name = {m["name"]: m for m in prior.get("members", [])}
    members = []
    for item in chosen:
        old = old_by_name.get(item["name"])
        path = source_root / item["name"]
        if old and path.is_file() and old["sha256"] == digest(path) and all(old[k] == item[k] for k in item):
            members.append(old)
        else:
            fetch = fetch_large_audit_member if item["bytes"] > 128 * 1024 * 1024 else fetch_member
            members.append(fetch(reader, url, entry["size"], item, source_root))
    result = {"file": entry["key"], "archive_bytes": entry["size"],
              "publisher_checksum": entry["checksum"], "whole_archive_checksum_verified": False,
              "url": url, "central_directory": directory, "members": members}
    receipt_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified_raw_members": scenario, "members": len(members),
                      "bytes": sum(m["bytes"] for m in members)}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--names", nargs="+")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--selected-audit-members", action="store_true")
    args = parser.parse_args()
    if bool(args.names) == args.all:
        parser.error("Choose --all or --names")
    args.output.mkdir(parents=True, exist_ok=True)
    metadata_path = args.output / "zenodo_record.json"
    if not metadata_path.exists():
        get(RECORD, metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["id"] != 18861762 or metadata["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Unexpected source record or license")
    sources = []
    for name in ["labels.json", "attack_times.csv", "README.md", "extract_attack_logs.py", "timestampExtractor.py"]:
        destination = args.output / name
        url = f"{REPOSITORY}/{COMMIT}/{name}"
        if not destination.exists():
            get(url, destination)
        sources.append({"file": name, "sha256": digest(destination), "url": url})
    entries = [entry for entry in metadata["files"] if entry["key"].startswith("scenario_")]
    if args.names:
        entries = [entry for entry in entries if entry["key"] in args.names]
        if set(args.names) != {entry["key"] for entry in entries}:
            raise ValueError("Unknown scenario name")
    entries.sort(key=lambda entry: (entry["size"], entry["key"]))
    reader = RangeReader(256 * 1024 * 1024)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        acquired = list(pool.map(lambda entry: download_members(entry, args.output, reader)
                                if args.selected_audit_members else download(entry, args.output), entries))
    selection = hashlib.sha256("|".join(entry["key"] for entry in entries).encode()).hexdigest()[:12]
    receipt = {"record": RECORD, "metadata_sha256": digest(metadata_path), "license": "CC-BY-4.0",
               "author_repository_commit": COMMIT, "sources": sources, "archives": acquired,
               "complete_raw_scenarios": not args.selected_audit_members,
               "complete_defender_audit_streams": args.selected_audit_members,
               "range_bytes_requested": reader.transferred,
               "extraction": "No files executed; ZIP members read as data"}
    receipt_path = args.output / f"ACQUISITION_{selection}.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": str(receipt_path), "archives": len(acquired)}), flush=True)


if __name__ == "__main__":
    main()
