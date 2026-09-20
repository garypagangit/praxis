"""Acquire the authors' public cAPTure reduced packet tables, with receipts.

Raw data stays outside Git. The public artifact has no verified separate data
license at qualification time; this tool does not redistribute its contents.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time

import requests


FILES = {
    "train_set_reduced.csv": "1jZ0GEn_XGvTzmB2j-60xRNxM4fCo8bbN",
    "test_set_reduced.csv": "1-RmfzjghlzUdL0zjGxjfubWXK-umxC_M",
}


def acquire(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    for name, file_id in FILES.items():
        target = root / name
        receipt_path = root / (name + ".receipt.json")
        if target.exists() and receipt_path.exists():
            receipt = json.loads(receipt_path.read_text())
            with target.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
            if digest != receipt["sha256"]:
                raise ValueError(f"Existing file checksum mismatch: {name}")
            print(f"Verified existing {name}: {target.stat().st_size} bytes", flush=True)
            continue
        started = time.monotonic()
        url = "https://drive.usercontent.google.com/download"
        params = {"id": file_id, "export": "download", "confirm": "t"}
        with requests.get(url, params=params, stream=True, timeout=(30, 180)) as response:
            response.raise_for_status()
            if "text/html" in response.headers.get("content-type", ""):
                raise ValueError("Download returned HTML, not the public dataset")
            total = int(response.headers.get("content-length", 0))
            partial = target.with_suffix(target.suffix + ".partial")
            digest = hashlib.sha256()
            count = 0
            last_report = time.monotonic()
            with partial.open("wb") as handle:
                for chunk in response.iter_content(4 * 1024 * 1024):
                    handle.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                    if time.monotonic() - last_report >= 20:
                        print(f"{name}: {count:,}/{total:,} bytes", flush=True)
                        last_report = time.monotonic()
            if total and count != total:
                raise ValueError(f"Incomplete download: {count} / {total}")
            with partial.open("rb") as handle:
                if b"phase_name,sequence_id,label,timestamp" not in handle.readline():
                    raise ValueError("Unexpected cAPTure reduced table schema")
            partial.replace(target)
            receipt = {
                "dataset": "cAPTure", "file": name, "drive_id": file_id,
                "source_url": response.url, "bytes": count,
                "sha256": digest.hexdigest(), "author_checksum_available": False,
                "acquired_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "paper_doi": "10.1016/j.comnet.2026.112570",
                "data_license": "not verified; do not redistribute raw data",
            }
            receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    acquire(parser.parse_args().output)
