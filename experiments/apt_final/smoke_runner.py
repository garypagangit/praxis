"""Run E1-E4 on explicit synthetic fixtures, never as APT efficacy evidence."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time


def run(output, config_path):
    import torch
    import engine
    from fixtures import make_fixture, SCOPE
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config.get("scope") != SCOPE:
        raise ValueError("Smoke requires the explicitly synthetic configuration")
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    fixture = make_fixture(root / "fixture")
    rows, edges = fixture / "development_rows.jsonl", fixture / "development_edges.jsonl"
    torch.set_num_threads(2)
    start = time.perf_counter()
    first = engine.run_e1(config, rows, edges, root / "E1", smoke=True)
    if any(r["changed_fraction"] < config.get("min_rewired_fraction", .5)
           for r in first["rewiring"].values()):
        raise ValueError("Synthetic qualification did not exercise a sufficiently changed graph control")
    engine.run_e2(config, root / "E1", rows, edges, root / "E2", smoke=True)
    engine.run_e3(config, root / "E2", root / "E3", smoke=True)
    engine.run_e4(config, root / "E1", root / "E3/POLICY_FREEZE.json",
                  fixture / "confirmation_rows.jsonl", fixture / "confirmation_edges.jsonl",
                  root / "E4", smoke=True)
    stages = {}
    for stage in ("E1", "E2", "E3", "E4"):
        path = root / stage / "RESULTS.json"
        result = json.loads(path.read_text(encoding="utf-8"))
        stages[stage] = {"result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                         "status": result.get("status"), "scope": result.get("scope"),
                         "stage": result.get("stage")}
    receipt = {"status": "SOFTWARE_PIPELINE_COMPLETED", "scope": SCOPE,
               "completed_utc": datetime.now(timezone.utc).isoformat(),
               "wall_seconds": time.perf_counter() - start,
               "config_sha256": hashlib.sha256(Path(config_path).read_bytes()).hexdigest(),
               "fixture_manifest_sha256": hashlib.sha256((fixture / "FIXTURE_MANIFEST.json").read_bytes()).hexdigest(),
               "stages": stages, "rewired_fractions": {k: v["changed_fraction"] for k, v in first["rewiring"].items()},
               "scientific_accuracy_claim": False,
               "real_telemetry_used": False, "cloud_calls": 0,
               "source_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(Path(__file__).parent.glob("*.py"))},
               "limits": ["Synthetic software qualification only.",
                          "Real-data modeling remains gated by completed E0 normalization and evidence review.",
                          "No end-to-end operational compute or transfer claim."]}
    with (root / "SMOKE_SUMMARY.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    return receipt
