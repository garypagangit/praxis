"""Freeze locally reviewed protocol/code/data before the first live model outcome."""
from __future__ import annotations
from .common import ROOT, file_hash, load_json, now, write_json


if __name__ == "__main__":
    target = ROOT / "FROZEN_PROTOCOL.json"
    if target.exists(): raise SystemExit("Refusing to replace frozen protocol; use a dated pre-result amendment and a new freeze identity.")
    paths = sorted(ROOT.glob("harness/*.py")) + sorted(ROOT.glob("configs/*.json"))
    paths += [ROOT / "PREREGISTRATION_v1.md", ROOT / "002_AMENDMENT_PRE_RESULT_20260908.md", ROOT / "NOVELTY_REVIEW.md", ROOT / "artifacts/fixtures/FIXTURE_GATE.json", ROOT / "artifacts/fixtures/fixtures.json"]
    if load_json(ROOT / "artifacts/fixtures/FIXTURE_GATE.json")["status"] != "PASS": raise SystemExit("Fixture gate must PASS")
    files = {path.relative_to(ROOT).as_posix(): file_hash(path) for path in paths}
    for name in ("model_adapter.py", "inference_server.py"):
        files["../shared/" + name] = file_hash(ROOT.parent / "shared" / name)
    write_json(target, {"experiment_id": "Final-Praxis-002", "frozen_at": now(), "scientific_outputs_seen": False,
                        "files": files}, exclusive=True)
    print(file_hash(target))
