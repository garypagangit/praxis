from __future__ import annotations

import argparse
import gzip
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from praxis.provenance.windows import normalize_uuid


def iter_input_paths(paths: list[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_dir():
            yield from sorted(
                item
                for item in path.rglob("*")
                if item.is_file()
                and item.suffix.lower() in {".json", ".jsonl", ".gz"}
            )
        else:
            yield path


def open_text(path: Path):
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_json_records(path: Path) -> Iterable[dict[str, Any]]:
    with open_text(path) as handle:
        first_non_ws = ""
        while True:
            char = handle.read(1)
            if not char:
                return
            if not char.isspace():
                first_non_ws = char
                break
        handle.seek(0)

        if first_non_ws == "[":
            payload = json.load(handle)
            if not isinstance(payload, list):
                raise ValueError(f"Expected JSON array in {path}")
            for item in payload:
                if isinstance(item, dict):
                    yield item
            return

        for line in handle:
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if isinstance(item, dict):
                yield item


def normalize_optc_event(row: dict[str, Any], source_file: Path, record_index: int) -> dict[str, Any] | None:
    timestamp_ms = row.get("timestamp_ms", row.get("timestamp"))
    try:
        timestamp_nanos = int(float(timestamp_ms) * 1_000_000)
    except (TypeError, ValueError):
        return None

    properties = row.get("properties") or {}
    object_type = str(row.get("object") or "UNKNOWN")
    action = str(row.get("action") or "UNKNOWN")
    event_name = f"{object_type}_{action}"
    actor_uuid = normalize_uuid(row.get("actorID"))
    object_uuid = normalize_uuid(row.get("objectID"))
    event_uuid = normalize_uuid(row.get("id"))
    exec_name = (
        properties.get("image_path")
        or properties.get("process_image_path")
        or properties.get("parent_image_path")
        or properties.get("command_line")
        or row.get("principal")
        or "UNKNOWN"
    )

    return {
        "timestamp_nanos": timestamp_nanos,
        "sequence": record_index,
        "record_index": record_index,
        "datum_type": event_name,
        "event_names": [event_name],
        "source_file": str(source_file),
        "subject_uuid": actor_uuid or "UNKNOWN",
        "object_uuid": object_uuid or "UNKNOWN",
        "object2_uuid": event_uuid or "UNKNOWN",
        "properties": {
            "exec": str(exec_name),
            "hostname": str(row.get("hostname") or "UNKNOWN").lower(),
            "principal": str(row.get("principal") or ""),
            "pid": row.get("pid"),
            "ppid": row.get("ppid"),
            "tid": row.get("tid"),
            "object": object_type,
            "action": action,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert OpTC eCAR JSON/JSONL records to normalized provenance edge JSONL."
    )
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--host-filter",
        action="append",
        default=None,
        help="Optional hostname filter. Can be repeated.",
    )
    args = parser.parse_args()

    host_filter = {item.lower() for item in args.host_filter or []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    seen = 0
    files = 0
    with args.output.open("w", encoding="utf-8") as out:
        for path in iter_input_paths(args.inputs):
            files += 1
            for record_index, row in enumerate(iter_json_records(path)):
                seen += 1
                if args.limit is not None and written >= args.limit:
                    break
                if host_filter:
                    hostname = str(row.get("hostname") or "").lower()
                    if hostname not in host_filter:
                        continue
                normalized = normalize_optc_event(row, path, record_index)
                if normalized is None:
                    continue
                out.write(json.dumps(normalized, sort_keys=True) + "\n")
                written += 1
            if args.limit is not None and written >= args.limit:
                break

    print(
        json.dumps(
            {
                "input_files": files,
                "records_seen": seen,
                "edges_written": written,
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
