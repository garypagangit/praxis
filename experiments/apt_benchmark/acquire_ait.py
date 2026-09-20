"""Acquire bounded, byte-preserved AIT-LDS source/label pairs via public ZIP ranges.

No archive scripts are executed. Whole-archive publisher checksums are recorded,
not claimed verified: selected members are checked against ZIP CRC32 and hashed.
The resulting source lines keep the author's original one-based numbering.
This is acquisition/qualification code, not a label adjudicator or model runner.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import threading
import time
import zlib

import requests


RECORD = 19483937
SCENARIOS = ("santos", "fox", "wardbeck", "russellmitchell", "shaw", "wheeler", "wilson", "harrison")
META_URL = f"https://zenodo.org/api/records/{RECORD}"


class RangeReader:
    """Strict bounded HTTP range reader shared across independent scenario jobs."""

    def __init__(self, budget: int):
        self.budget = budget
        self.transferred = 0
        self.lock = threading.Lock()
        self.last_request = 0.0

    def get(self, url: str, size: int, start: int, end: int) -> bytes:
        if not 0 <= start <= end < size:
            raise ValueError("Invalid range")
        length = end - start + 1
        expected = f"bytes {start}-{end}/{size}"
        error = "range request failed"
        for attempt in range(4):
            with self.lock:
                delay = 1.1 - (time.monotonic() - self.last_request)
                if delay > 0:
                    time.sleep(delay)
                self.last_request = time.monotonic()
                if self.transferred + length > self.budget:
                    raise ValueError("Transfer budget exhausted")
                self.transferred += length
            retry_delay = 2 * (attempt + 1)
            with requests.get(url, headers={"Range": f"bytes={start}-{end}", "Cache-Control": "no-cache"},
                              stream=True, timeout=(20, 60)) as response:
                if response.status_code == 206 and response.headers.get("Content-Range") == expected:
                    data = response.raw.read(length + 1)
                    if len(data) == length:
                        return data
                    error = "Range length mismatch"
                else:
                    error = f"Range response {response.status_code}, {response.headers.get('Content-Range')}; expected {expected}"
                    if response.status_code == 429:
                        try:
                            retry_delay = max(60, int(response.headers.get("Retry-After", "60")))
                        except ValueError:
                            retry_delay = 60
            if attempt < 3:
                # Short chunks keep any individual pause bounded.
                while retry_delay > 0:
                    time.sleep(min(30, retry_delay))
                    retry_delay -= 30
        raise ValueError(error)


def central_directory(reader: RangeReader, url: str, size: int) -> tuple[list[dict], dict]:
    start = max(0, size - 65557)
    tail = reader.get(url, size, start, size - 1)
    marker = tail.rfind(b"PK\x05\x06")
    if marker < 0 or marker + 22 > len(tail):
        raise ValueError("Missing ZIP end record")
    eocd = struct.unpack_from("<4s4H2LH", tail, marker)
    _, disk, cd_disk, entries_disk, count, length, offset, comment = eocd
    if disk or cd_disk or entries_disk != count or marker + 22 + comment != len(tail):
        raise ValueError("Unsupported split ZIP or invalid end record")
    if count == 65535 or offset == 0xFFFFFFFF or length > 8 * 1024 * 1024:
        raise ValueError("Unsupported ZIP64 or oversized directory")
    raw = reader.get(url, size, offset, offset + length - 1)
    entries = []
    pos = 0
    while pos < len(raw):
        v = struct.unpack_from("<4s6H3L5H2L", raw, pos)
        if v[0] != b"PK\x01\x02":
            raise ValueError("Invalid central directory entry")
        name_len, extra_len, comment_len = v[10:13]
        name = raw[pos + 46:pos + 46 + name_len].decode("utf-8")
        entries.append({"name": name, "flags": v[3], "method": v[4], "crc32": v[7],
                        "compressed_bytes": v[8], "bytes": v[9], "local_header_offset": v[16]})
        pos += 46 + name_len + extra_len + comment_len
    if pos != length or len(entries) != count or len({e["name"] for e in entries}) != count:
        raise ValueError("Central directory count or name mismatch")
    return entries, {"offset": offset, "bytes": length, "sha256": hashlib.sha256(raw).hexdigest()}


def fetch_member(reader: RangeReader, url: str, size: int, entry: dict, root: Path) -> dict:
    name = entry["name"]
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name:
        raise ValueError("Unsafe ZIP member name")
    dest = (root / name).resolve()
    if root.resolve() not in dest.parents:
        raise ValueError("Member escapes output root")
    if entry["flags"] & 1 or entry["method"] not in (0, 8):
        raise ValueError("Encrypted or unsupported member")
    if entry["bytes"] > 128 * 1024 * 1024 or entry["compressed_bytes"] > 32 * 1024 * 1024:
        raise ValueError("Member exceeds bounded qualification size")
    offset = entry["local_header_offset"]
    header = reader.get(url, size, offset, offset + 29)
    v = struct.unpack("<4s5H3L2H", header)
    if v[0] != b"PK\x03\x04" or v[3] != entry["method"] or v[2] != entry["flags"]:
        raise ValueError("Local header mismatch")
    name_len, extra_len = v[-2:]
    payload_len = name_len + extra_len + entry["compressed_bytes"]
    payload = reader.get(url, size, offset + 30, offset + 30 + payload_len - 1)
    if payload[:name_len].decode("utf-8") != name:
        raise ValueError("Local member name mismatch")
    compressed = payload[name_len + extra_len:]
    if entry["method"] == 8:
        decoder = zlib.decompressobj(-15)
        data = decoder.decompress(compressed, entry["bytes"] + 1)
        if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise ValueError("Invalid or oversized compressed stream")
    else:
        data = compressed
    if len(data) != entry["bytes"] or zlib.crc32(data) & 0xFFFFFFFF != entry["crc32"]:
        raise ValueError("Member length or CRC mismatch")
    sha = hashlib.sha256(data).hexdigest()
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() != sha:
        raise ValueError("Refusing to replace a different existing source member")
    if not dest.exists():
        dest.write_bytes(data)
    return {**entry, "sha256": sha, "crc32_verified": True,
            "download_byte_ranges": [[offset, offset + 29], [offset + 30, offset + 29 + payload_len]],
            "local_relative_path": name}


def selected_pairs(entries: list[dict]) -> tuple[list[dict], list[str]]:
    by_name = {e["name"]: e for e in entries}
    label_names = sorted(e["name"] for e in entries
                         if e["name"].startswith("labels/intranet_server/logs/")
                         and not e["name"].endswith("/")
                         and ("/audit/" in e["name"] or "/apache2/" in e["name"]
                              or e["name"].rsplit("/", 1)[-1].startswith("auth.log")))
    if not label_names:
        raise ValueError("No requested source/label pairs")
    pairs = []
    names = []
    for label in label_names:
        source = label.replace("labels/", "gather/", 1)
        if source not in by_name:
            raise ValueError("Missing exact source for label file")
        pairs.append({"labels": label, "source": source})
        names.extend([label, source])
    metadata = [n for n in by_name if n in ("dataset.yml", "dataset.yaml")
                or (n.startswith("gather/attacker_") and n.endswith("/logs/attacks.log"))]
    if not any(n.startswith("dataset.") for n in metadata):
        raise ValueError("Simulation interval metadata absent")
    if not any(n.endswith("/attacks.log") for n in metadata):
        raise ValueError("Attacker chronology absent")
    return pairs, sorted(set(names + metadata))


def acquire_scenario(scenario: str, metadata: dict, reader: RangeReader, output: Path) -> dict:
    item = next(f for f in metadata["files"] if f["key"] == scenario + "_no-pcaps.zip")
    url = f"https://zenodo.org/records/{RECORD}/files/{item['key']}?download=1"
    entries, cd = central_directory(reader, url, item["size"])
    by_name = {e["name"]: e for e in entries}
    pairs, names = selected_pairs(entries)
    root = output / scenario
    root.mkdir(parents=True, exist_ok=True)
    (root / "CENTRAL_DIRECTORY.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    prior_path = root / "ACQUISITION.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8")) if prior_path.exists() else {}
    cached = {m["name"]: m for m in prior.get("members", [])}
    binding_ok = (prior.get("record") == RECORD and prior.get("source_url") == url
                  and prior.get("publisher_archive_checksum") == item["checksum"])
    members = []
    for name in names:
        old = cached.get(name)
        path = root / name
        if (binding_ok and old and old.get("crc32_verified") and path.is_file()
                and all(old.get(k) == by_name[name][k] for k in
                        ("bytes", "crc32", "local_header_offset", "compressed_bytes"))
                and hashlib.sha256(path.read_bytes()).hexdigest() == old["sha256"]):
            members.append({**old, "reused_verified_member": True})
        else:
            members.append(fetch_member(reader, url, item["size"], by_name[name], root))
    for pair in pairs:
        source_lines = (root / pair["source"]).read_bytes().splitlines()
        labels = [json.loads(line) for line in (root / pair["labels"]).read_text(encoding="utf-8").splitlines()]
        line_ids = set()
        for label in labels:
            n = label.get("line")
            if type(n) is not int or not 1 <= n <= len(source_lines) or n in line_ids:
                raise ValueError("Invalid or duplicate one-based label line")
            if not isinstance(label.get("labels"), list) or not all(isinstance(v, str) for v in label["labels"]):
                raise ValueError("Invalid label list")
            line_ids.add(n)
        pair.update(source_lines=len(source_lines), author_labeled_lines=len(labels))
    receipt = {"scenario": scenario, "record": RECORD, "source_url": url,
               "archive_bytes": item["size"], "publisher_archive_checksum": item["checksum"],
               "whole_archive_checksum_verified": False, "central_directory": cd,
               "members": members, "pairs": pairs,
               "empty_label_files_in_scope": sum(by_name[p["labels"]]["bytes"] == 0 for p in pairs),
               "classification_status": "NOT_SCORED; absent label is not independently adjudicated benign"}
    (root / "ACQUISITION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"scenario": scenario, "members": len(members), "pairs": len(pairs),
                      "source_lines": sum(p["source_lines"] for p in pairs)}), flush=True)
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-transfer-mib", type=int, default=200)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    args = parser.parse_args()
    if args.max_transfer_mib <= 0 or len(set(args.scenarios)) != len(args.scenarios):
        raise ValueError("Invalid transfer budget or duplicate scenarios")
    response = requests.get(META_URL, timeout=30)
    response.raise_for_status()
    metadata = response.json()
    if metadata["id"] != RECORD or metadata["metadata"]["license"]["id"] != "cc-by-nc-sa-4.0":
        raise ValueError("Pinned record or license changed")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "ZENODO_METADATA.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    reader = RangeReader(args.max_transfer_mib * 1024 * 1024)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda s: acquire_scenario(s, metadata, reader, args.output), args.scenarios))
    receipt = {"created_utc": datetime.now(timezone.utc).isoformat(), "record": RECORD,
               "license": "CC-BY-NC-SA-4.0", "requested_range_bytes": reader.transferred,
               "scenarios": results, "models_run": False,
               "limits": "Eight variants of a shared emulation; no real actor attribution or independent campaign claim."}
    (args.output / "ACQUISITION.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"complete": True, "scenarios": len(results), "range_bytes": reader.transferred}), flush=True)


if __name__ == "__main__":
    main()
