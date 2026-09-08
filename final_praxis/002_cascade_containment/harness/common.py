from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARMS = ("A0", "A1", "A2", "A3")
FAMILIES = ("E1", "E2", "E3", "E4", "E5", "E6")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value, exclusive=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_object(text):
    """Only a JSON object, optionally in one outer JSON fence; no repair/retry."""
    value = text.strip()
    if value.startswith("```") and value.endswith("```"):
        lines = value.splitlines()
        if lines[0].strip().lower() not in ("```", "```json"):
            raise ValueError("unsupported output fence")
        value = "\n".join(lines[1:-1])
    obj = json.loads(value)
    if not isinstance(obj, dict):
        raise ValueError("expected JSON object")
    return obj
