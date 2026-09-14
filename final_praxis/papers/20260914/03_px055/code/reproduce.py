"""Recompute PX055 scientific metrics from packaged captures; no model or cloud calls.

The historical independent adjudicator supplies the numerical implementation.
This wrapper substitutes a portable ID manifest for private XSTest text and
does not repeat cloud/stop-state attestation. Its scope is explicitly narrower
than the archived independent adjudication, whose scientific fields it checks.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_manifest(root):
    manifest = json.loads((root / "FILE_MANIFEST.json").read_text(encoding="utf-8"))
    for row in manifest["files"]:
        path = (root / row["path"]).resolve()
        if root.resolve() not in path.parents:
            raise ValueError("Manifest path leaves package")
        if not path.is_file() or path.stat().st_size != row["bytes"] or sha(path) != row["sha256"]:
            raise ValueError("Manifest mismatch: " + row["path"])
    return len(manifest["files"])


def compare(actual, expected, path="result", counts=None):
    """Compare every computed field, including all nested per-layer results."""
    if counts is None:
        counts = {"checked": 0, "failures": []}
    if isinstance(actual, dict):
        for key, value in actual.items():
            if key not in expected:
                counts["failures"].append(path + "." + key + ": missing reference")
            else:
                compare(value, expected[key], path + "." + key, counts)
    elif isinstance(actual, (list, tuple)):
        counts["checked"] += 1
        if len(actual) != len(expected):
            counts["failures"].append(path + ": length mismatch")
        else:
            for i, value in enumerate(actual):
                compare(value, expected[i], f"{path}[{i}]", counts)
    else:
        counts["checked"] += 1
        if isinstance(actual, (float, np.floating)):
            ok = math.isfinite(float(actual)) and math.isfinite(float(expected)) and math.isclose(float(actual), float(expected), rel_tol=1e-9, abs_tol=1e-9)
        else:
            ok = actual == expected
        if not ok:
            counts["failures"].append(path + ": value mismatch")
    return counts


def load_core():
    path = ROOT / "evidence/source/adjudicate_px055_e1_e4_r3.py"
    spec = importlib.util.spec_from_file_location("px055_historical_adjudicator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def execute(output, xstest_source=None):
    started = time.monotonic()
    checked_files = check_manifest(ROOT)
    reference = json.loads((ROOT / "evidence/reference/PX055_R3_INDEPENDENT_ADJUDICATION.json").read_text(encoding="utf-8"))
    raw_hash_count = 0
    suffixes = {"geometry_npz_sha256": "geometry.npz", "metadata_sha256": "metadata.json", "behavior_sha256": "behavior.json", "e4_sha256": "e4.json"}
    for model, cells in reference["artifact_sha256"].items():
        for condition, hashes in cells.items():
            for field, expected in hashes.items():
                assert sha(ROOT / f"evidence/raw/cells/{model}__{condition}.{suffixes[field]}") == expected
                raw_hash_count += 1
    assert raw_hash_count == 33
    core = load_core()
    config_path = ROOT / "evidence/source/px055_e1_e4_frozen_20260831.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert sha(config_path) == core.EXPECTED_CONFIG_SHA256
    models = tuple(core.ModelSpec(r["family"], r["id"], r["revision"], core.R3_ATTENTION_IMPLEMENTATIONS[r["family"]]) for r in config["models"])
    conditions = tuple(r["id"] for r in config["conditions"])
    assert tuple(m.key for m in models) == ("qwen", "llama", "gemma")
    assert conditions == ("fp16", "bnb_int8", "bnb_nf4")
    # Historical amendment SHA is lineage metadata here, not a fresh byte claim.
    protocol = core.Protocol(config, sha(config_path), core.EXPECTED_R3_AMENDMENT_SHA256, models, conditions)
    safe = core.load_safe_corpus(protocol, ROOT / "evidence/source/safe_prompt_source.py")
    manifest = json.loads((ROOT / "evidence/source/XSTEST_ID_MANIFEST.json").read_text(encoding="utf-8"))
    rows = tuple(manifest["rows"])
    assert manifest["source_sha256"] == config["e3"]["dataset"]["sha256"]
    assert len(rows) == len({r["public_prompt_id"] for r in rows}) == 450
    assert sum(r["label"] == "safe" for r in rows) == 250
    assert sum(r["label"] == "unsafe" for r in rows) == 200
    corpus = core.XSTestCorpus(rows, {r["public_prompt_id"]: r for r in rows}, manifest["source_sha256"])
    if xstest_source:
        checked_source = core.load_xstest_corpus(protocol, xstest_source)
        assert checked_source.rows == corpus.rows
    raw = ROOT / "evidence/raw"
    analyses, behaviors, projected = [], {}, {}
    for model in models:
        print("Recomputing " + model.key, flush=True)
        geometry = {c: core.load_geometry_cell(raw, protocol, safe, model, c) for c in conditions}
        behaviors[model.key] = {c: core.load_behavior_cell(raw, protocol, corpus, model, c) for c in conditions}
        assert all(core.artifact_metadata_equal(behaviors[model.key]["fp16"], behaviors[model.key][c]) for c in conditions)
        analysis = core.analyze_model_geometry(protocol, model, geometry)
        assert analysis["paired_rows"] == 116
        analyses.append(analysis)
        e4 = {c: core.load_e4_cell(raw, protocol, safe, geometry[c], model, c) for c in config["e4"]["conditions"]}
        for cell in e4.values():
            assert cell.payload["intervention_layer"] == min(analysis["effective_layers"])
            assert cell.payload["readout_layer"] == max(analysis["effective_layers"])
        projected[model.key] = core.e4_bootstrap_model(protocol, e4["fp16"], e4["bnb_nf4"])
    first = behaviors[models[0].key]["fp16"]
    assert all(core.artifact_metadata_equal(first, b["fp16"]) for b in behaviors.values())
    e1 = core.adjudicate_e1(protocol, analyses)
    e2 = core.adjudicate_e2(protocol, analyses)
    status = "H3_RANK_SPREADING_BOUNDED" if e1["h3"] else "H1_PRECISION_INVARIANT_BOUNDED" if e1["h1"] and e2["clean"] else "BOUNDED_MIXED_OR_NULL"
    measured = core.json_safe({"status": status, "models": analyses, "e1": e1, "e2": e2,
        "e3": core.adjudicate_e3(protocol, analyses, behaviors, True),
        "e4": {"models": projected, "positive_model_count": sum(r["positive"] for r in projected.values()), "supports_original_h4": False},
        "behavior": {m: {c: b.metrics for c, b in cells.items()} for m, cells in behaviors.items()}})
    comparison = compare(measured, reference)
    output.mkdir(parents=True, exist_ok=True)
    (output / "RECOMPUTED_RESULTS.json").write_text(json.dumps(measured, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    receipt = {"schema": "px055-portable-scientific-reproduction-v1", "pass": not comparison["failures"],
        "file_manifest_sha256": sha(ROOT / "FILE_MANIFEST.json"), "files_verified": checked_files,
        "historical_raw_artifact_hashes_verified": raw_hash_count,
        "python": platform.python_version(), "numpy": np.__version__, "reproducer_sha256": sha(__file__),
        "historical_adjudicator_sha256": sha(ROOT / "evidence/source/adjudicate_px055_e1_e4_r3.py"),
        "numerical_tolerance": {"relative": 1e-9, "absolute": 1e-9}, "comparisons": comparison,
        "scientific_status": status, "model_precision_cells": 9, "safe_rows_per_cell": 116,
        "behavior_rows": sum(len(b.payload["rows"]) for cells in behaviors.values() for b in cells.values()),
        "e1_cells": e1["effective_cell_count"], "e2_ratios": e2["directed_ratio_count"],
        "e4_rows": sum(len(json.loads(p.read_text())["rows"]) for p in (raw / "cells").glob("*.e4.json")),
        "xstest_original_source_bytes_verified_this_run": bool(xstest_source),
        "recomputed_results_sha256": sha(output / "RECOMPUTED_RESULTS.json"),
        "seconds": time.monotonic() - started,
        "scope": "Numerical reproduction using the historical independent analysis implementation and original raw captures. Not an additional independent implementation, inference rerun, or cloud/terminal-state re-attestation. Behavior flags are recounted; decoded completions are unavailable for semantic relabeling. The redacted amendment is not claimed byte-identical to its original."}
    (output / "REPRODUCTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["pass", "scientific_status", "files_verified", "comparisons", "seconds"]}))
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "reproduced")
    parser.add_argument("--xstest-source", type=Path, help="Optional independently obtained original CSV; read/hash/parse only, never copied to outputs")
    args = parser.parse_args()
    raise SystemExit(execute(args.output, args.xstest_source))
