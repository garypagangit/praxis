from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter
from pathlib import Path
from typing import Any

from fastavro import reader


def bytes_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.hex()
    text = str(value)
    if text.startswith("b'") or text.startswith('b"'):
        return text
    return text


def clean(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def convert_file(
    path: Path, max_records: int | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    record_types: Counter[str] = Counter()
    event_types: Counter[str] = Counter()

    with gzip.open(path, "rb") as handle:
        for idx, record in enumerate(reader(handle)):
            if max_records is not None and idx >= max_records:
                break
            record_type = str(record.get("type"))
            datum = record.get("datum") or {}
            datum_type = datum.get("type")
            record_types[record_type] += 1
            event_types[str(datum_type)] += 1

            base = {
                "source_file": path.name,
                "record_index": idx,
                "record_type": record_type,
                "datum_type": datum_type,
                "uuid": bytes_id(datum.get("uuid")),
                "host_id": bytes_id(record.get("hostId")),
                "session_number": record.get("sessionNumber"),
                "source": record.get("source"),
                "sequence": datum.get("sequence"),
                "timestamp_nanos": datum.get("timestampNanos"),
            }

            if record_type == "RECORD_EVENT":
                edges.append(
                    {
                        **base,
                        "subject_uuid": bytes_id(datum.get("subject")),
                        "object_uuid": bytes_id(datum.get("predicateObject")),
                        "object2_uuid": bytes_id(datum.get("predicateObject2")),
                        "object_path": datum.get("predicateObjectPath"),
                        "object2_path": datum.get("predicateObject2Path"),
                        "event_names": datum.get("names") or [],
                        "size": datum.get("size"),
                        "thread_id": datum.get("threadId"),
                        "properties": clean(datum.get("properties") or {}),
                    }
                )
            else:
                entities.append(
                    {
                        **base,
                        "properties": clean(datum.get("properties") or {}),
                        "raw_keys": sorted(str(key) for key in datum.keys()),
                    }
                )

    summary = {
        "source_file": str(path),
        "records_seen": sum(record_types.values()),
        "edges_emitted": len(edges),
        "entities_emitted": len(entities),
        "record_type_counts": dict(record_types.most_common()),
        "datum_type_counts": dict(event_types.most_common(30)),
    }
    return edges, entities, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--max-files", type=int, default=1)
    parser.add_argument("--max-records-per-file", type=int, default=100000)
    args = parser.parse_args()

    files = sorted(args.input_dir.glob("*.gz"))[: args.max_files]
    if not files:
        raise FileNotFoundError(f"No .gz files found under {args.input_dir}")

    all_edges: list[dict[str, Any]] = []
    all_entities: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    for path in files:
        edges, entities, summary = convert_file(path, args.max_records_per_file)
        all_edges.extend(edges)
        all_entities.extend(entities)
        file_summaries.append(summary)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_dir / "edges.jsonl", all_edges)
    write_jsonl(args.out_dir / "entities.jsonl", all_entities)
    summary = {
        "status": "converted",
        "input_dir": str(args.input_dir),
        "files_converted": [str(path) for path in files],
        "edges_emitted": len(all_edges),
        "entities_emitted": len(all_entities),
        "file_summaries": file_summaries,
        "artifacts": {
            "edges": str(args.out_dir / "edges.jsonl"),
            "entities": str(args.out_dir / "entities.jsonl"),
            "summary": str(args.out_dir / "summary.json"),
        },
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
