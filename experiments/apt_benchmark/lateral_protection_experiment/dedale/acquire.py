"""Bounded author-artifact acquisition; never downloads PCAPs or runs models.

ZIP members are read through validated HTTP byte ranges. A cumulative ledger
limits response-body bytes, including repeat requests, rather than archive size.
Member CRC is checked by zipfile and the acquired member receives a SHA-256.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


class Budget:
    def __init__(self, root: Path, limit: int = 2_000_000_000):
        self.path = root / "DOWNLOAD_BUDGET.json"
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {
            "limit_bytes": limit,
            "used_bytes": 1_000_000,
            "initial_metadata_and_probe_allowance_bytes": 1_000_000,
            "requests": [],
        }
        if self.state["limit_bytes"] != limit:
            raise ValueError("Do not silently change the existing download budget")

    def save(self):
        self.path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def reserve(self, size: int):
        if self.state["used_bytes"] + size > self.state["limit_bytes"]:
            raise ValueError("Initial cumulative 2GB download cap would be exceeded")

    def account(self, record: dict):
        self.state["used_bytes"] += record["bytes"]
        self.state["requests"].append(record)
        self.save()


class HTTPRanges(io.RawIOBase):
    def __init__(self, file_id: int, size: int, budget: Budget):
        self.url = f"https://entrepot.recherche.data.gouv.fr/api/access/datafile/{file_id}"
        self.size, self.pos, self.budget = size, 0, budget
        self.cache_start, self.cache = 0, b""

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, offset, whence=0):
        pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if pos < 0 or pos > self.size:
            raise ValueError("Seek outside author-declared archive")
        self.pos = pos
        return pos

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.pos
        size = min(size, self.size - self.pos)
        if not size:
            return b""
        if self.cache_start <= self.pos and self.pos + size <= self.cache_start + len(self.cache):
            offset = self.pos - self.cache_start
            self.pos += size
            return self.cache[offset:offset + size]
        self.budget.reserve(size)
        start = self.pos
        req = Request(self.url, headers={"Range": f"bytes={start}-{start + size - 1}",
                                        "Accept-Encoding": "identity"})
        with urlopen(req, timeout=60) as response:
            expected = f"bytes {start}-{start + size - 1}/{self.size}"
            if response.status != 206 or response.headers.get("Content-Range") != expected:
                raise ValueError("Server did not honor the exact byte range; refused full archive")
            # Charge the whole requested range before reading: a failed transfer
            # cannot make a retry undercount the cumulative download upper bound.
            record = {"source_url": self.url, "start": start, "bytes": size,
                      "charge_is_upper_bound": True,
                      "utc": datetime.now(timezone.utc).isoformat()}
            self.budget.account(record)
            data = response.read(size)
        if len(data) != size:
            raise IOError("Incomplete byte range; acquisition refused")
        record.update(sha256=hashlib.sha256(data).hexdigest(), received_bytes=len(data))
        self.budget.save()
        self.pos += size
        return data


def run(args):
    args.output.mkdir(parents=True, exist_ok=True)
    metadata_bytes = args.metadata.read_bytes()
    metadata = json.loads(metadata_bytes)["data"]["latestVersion"]
    matches = [f for f in metadata["files"] if f["dataFile"]["id"] == args.file_id]
    if len(matches) != 1:
        raise ValueError("File ID not in pinned public metadata")
    entry = matches[0]
    file = entry["dataFile"]
    if entry.get("restricted") or not file["filename"].startswith(("cicflowmeter_", "zeek_")):
        raise ValueError("Only unrestricted precomputed flow archives are allowed")
    budget = Budget(args.output)
    archive = HTTPRanges(args.file_id, file["filesize"], budget)
    with zipfile.ZipFile(archive) as zipped:
        members = [{"name": z.filename, "compressed_bytes": z.compress_size,
                    "uncompressed_bytes": z.file_size, "crc32": f"{z.CRC:08x}",
                    "header_offset": z.header_offset, "compression_type": z.compress_type}
                   for z in zipped.infolist()]
        receipt = {"archive": file["filename"], "file_id": file["id"],
                   "archive_bytes": file["filesize"], "author_checksum": file["checksum"],
                   "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
                   "dataset_version": f"{metadata['versionNumber']}.{metadata['versionMinorNumber']}",
                   "whole_archive_checksum_verified": False, "members": members}
        (args.output / f"INDEX_{file['id']}.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        if not args.member:
            print(json.dumps({"archive": file["filename"], "member_count": len(members),
                              "first_members": members[:40], "cumulative_download_bytes": budget.state['used_bytes']}))
            return
        member = zipped.getinfo(args.member)
        if member.is_dir() or not member.filename.lower().endswith((".csv", ".log", ".json", ".gz")):
            raise ValueError("Only explicitly selected flow-table/log members may be acquired")
        if member.file_size > args.max_uncompressed_bytes:
            raise ValueError("Member exceeds declared uncompressed limit")
        budget.reserve(member.compress_size + 100_000)
        # Flatten names so untrusted paths cannot escape the private output folder.
        name = f"{file['id']}_" + re.sub(r"[^A-Za-z0-9_.-]", "_", member.filename)
        target = args.output / "members" / name
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            raise FileExistsError("Refusing to overwrite an acquired member")
        partial = target.with_suffix(target.suffix + ".partial")
        digest = hashlib.sha256()
        count = 0
        with zipped.open(member) as source, partial.open("xb") as destination:
            # One bounded compressed-member request avoids hundreds of small
            # remote seeks. Subsequent zipfile reads use this in-memory cache.
            compressed_start = archive.tell()
            compressed = archive.read(member.compress_size)
            archive.cache_start, archive.cache = compressed_start, compressed
            archive.seek(compressed_start)
            while block := source.read(8 * 1024 * 1024):
                count += len(block)
                if count > args.max_uncompressed_bytes:
                    raise ValueError("Uncompressed member cap exceeded")
                destination.write(block)
                digest.update(block)
        if count != member.file_size:
            raise IOError("Uncompressed member length mismatch")
        partial.rename(target)
        record = {"source_url": archive.url, "archive": file["filename"], "member": member.filename,
                  "bytes": count, "sha256": digest.hexdigest(), "crc32_verified": f"{member.CRC:08x}",
                  "whole_archive_checksum_verified": False,
                  "dataset_version": receipt["dataset_version"],
                  "metadata_sha256": receipt["metadata_sha256"],
                  "acquired_utc": datetime.now(timezone.utc).isoformat(),
                  "cumulative_download_bytes": budget.state["used_bytes"]}
        target.with_suffix(target.suffix + ".receipt.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        print(json.dumps({"saved_member": target.name, **record}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--file-id", type=int, required=True)
    parser.add_argument("--member")
    parser.add_argument("--max-uncompressed-bytes", type=int, default=3_000_000_000)
    run(parser.parse_args())
