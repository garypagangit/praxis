"""Synthetic software-qualification records. Never scientific APT evidence."""
from pathlib import Path
import hashlib
import json
import math
import random

SCOPE = "SYNTHETIC_SMOKE_NOT_SCIENTIFIC_EVIDENCE"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def make_fixture(output):
    root = Path(output)
    root.mkdir(parents=True, exist_ok=False)
    rng = random.Random(20260919)
    rows, edges = [], []
    for si, split in enumerate(("train", "gate_train", "calibration", "development", "confirmation")):
        for gi in range(5):
            group = f"synthetic-{split}-{gi}"
            history = []
            for j in range(24):
                label = j % 3
                when = 1789776000.0 + si * 864000 + gi * 86400 + j * 10
                row = {"id": f"{group}-{j}", "group_id": group, "split": split, "synthetic": True,
                       "host_id": f"synthetic-host-{si}-{gi}", "time": when,
                       "features": [label + rng.gauss(0, .7), math.sin(j), rng.random(), j / 24],
                       "label": label}
                rows.append(row)
                for lag in (2, 5, 8):
                    if len(history) >= lag:
                        edges.append({"source": history[-lag]["id"], "target": row["id"],
                                      "relation": "session" if lag == 2 else "host",
                                      "available_at": when})
                history.append(row)
    confirmation = {r["id"] for r in rows if r["split"] == "confirmation"}
    paths = {}
    for name, values in {
        "development_rows.jsonl": [r for r in rows if r["id"] not in confirmation],
        "development_edges.jsonl": [e for e in edges if e["target"] not in confirmation],
        "confirmation_rows.jsonl": [r for r in rows if r["id"] in confirmation],
        "confirmation_edges.jsonl": [e for e in edges if e["target"] in confirmation],
    }.items():
        path = root / name
        with path.open("x", encoding="utf-8") as stream:
            for value in values:
                stream.write(json.dumps(value, sort_keys=True) + "\n")
        paths[name] = {"sha256": digest(path), "records": len(values)}
    (root / "FIXTURE_MANIFEST.json").write_text(json.dumps({"scope": SCOPE, "seed": 20260919,
        "real_telemetry": False, "files": paths}, indent=2) + "\n", encoding="utf-8")
    return root
