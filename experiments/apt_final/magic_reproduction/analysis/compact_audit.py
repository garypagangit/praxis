"""Verify the separate exact-compression runtime chain, then original evidence.

This post-hoc auditor never changes the frozen original or compact runtime files.
The extra receipt is excluded from the original worker's earlier inventory only
after its registrations, source hashes, substitution, exit, and result hash pass.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

import numpy as np

from . import audit as original

COMPACT = original.HERE.parent / "magic_compact"
COMPACT_FILES = {"experiments/apt_final/magic_compact/" + name for name in
                 ("PROTOCOL.md", "scoring.py", "worker.py", "provenance.py", "launch.py", "run_cloud.sh")}
SUBSTITUTIONS = {
    "experiments.apt_final.magic_reproduction.worker.ExactFullReferenceKNN":
        "experiments.apt_final.magic_compact.scoring.ExactFullReferenceKNN",
    "experiments.apt_final.magic_reproduction.qualification.ExactFullReferenceKNN":
        "experiments.apt_final.magic_compact.scoring.ExactFullReferenceKNN"}
RECEIPT = "COMPACT_RUNTIME_RECEIPT.json"


def verify_chain(output_dir, registration, compact_registration, bundle=None):
    old, amended = original.read(registration), original.read(compact_registration)
    require = original.require
    require(amended["status"] == "FROZEN_EXACT_MULTIPLICITY_RUNTIME"
            and set(amended["code_hashes"]) == COMPACT_FILES, "Wrong compact registration/inventory")
    require(amended["science_changed"] is False and amended["exact_duplicate_storage_only"] is True
            and amended["checkpoint_reuse"] is False and amended["novelty_claimed"] is False,
            "Compact amendment changes scientific scope")
    require(isinstance(amended["source_commit"], str) and re.fullmatch("[0-9a-f]{40}", amended["source_commit"]),
            "Invalid compact source commit")
    for relative, sha in amended["code_hashes"].items():
        original.hashed(original.REPO, relative, sha)
    require(amended["original_registration_sha256"] == original.digest(registration)
            and amended["original_source_commit"] == old["source_commit"], "Compact original-source chain mismatch")
    output = Path(output_dir)
    receipt = original.read(original.bound(output, RECEIPT))
    require(receipt["status"] == "COMPACT_RUNTIME_RECORDED"
            and receipt["compact_registration_sha256"] == original.digest(compact_registration)
            and receipt["original_registration_sha256"] == original.digest(registration)
            and receipt["source_commit"] == amended["source_commit"]
            and receipt["original_source_commit"] == old["source_commit"], "Compact runtime receipt chain mismatch")
    require(receipt["source_original_unchanged"] is True and receipt["source_mode"] == "exact_multiplicity_runtime"
            and receipt["substitutions"] == SUBSTITUTIONS and receipt["novelty_claimed"] is False
            and receipt["checkpoint_reuse"] is False, "Compact substitution/science receipt mismatch")
    require(type(receipt["exit_code"]) is int and receipt["exit_code"] in {0, 1}, "Invalid compact exit code")
    require(isinstance(receipt["bundle_sha256"], str) and re.fullmatch("[0-9a-f]{64}", receipt["bundle_sha256"]),
            "Missing compact frozen bundle hash")
    if bundle is not None:
        require(original.digest(bundle) == receipt["bundle_sha256"], "Compact input bundle hash mismatch")
    results_path = output / "RESULTS.json"
    if results_path.is_file():
        require(receipt["results_sha256"] == original.digest(results_path), "Compact receipt/result hash mismatch")
        results = original.read(results_path)
        require(receipt["selected_datasets"] == results["selected_datasets"], "Compact dataset selection mismatch")
        require(receipt["exit_code"] == (1 if results["status"] == "FAILED_RUNTIME" else 0), "Compact exit/result mismatch")
    else:
        require(receipt["results_sha256"] is None and receipt["exit_code"] == 1, "Compact completion lacks results")
    return {"status": "VERIFIED_EXACT_MULTIPLICITY_RUNTIME_CHAIN",
            "compact_registration_sha256": original.digest(compact_registration),
            "original_registration_sha256": original.digest(registration),
            "receipt_sha256": original.digest(output / RECEIPT), "compact_source_files_checked": len(COMPACT_FILES),
            "source_original_unchanged": True, "substitutions": SUBSTITUTIONS,
            "bundle_sha256": receipt["bundle_sha256"], "input_bundle_bytes_independently_checked": bundle is not None,
            "transport_and_AWS_shutdown_verified_here": False, "exit_code": receipt["exit_code"]}


def verify_compression_timing(timing, rows, unique):
    original.require(timing["reference_rows"] == rows and timing["original_reference_rows"] == rows
                     and timing["reference_occurrences_preserved"] == rows and timing["unique_reference_rows"] == unique,
                     "Compact multiplicity/population mismatch")
    original.require(timing["reference_sampling"] is False and timing["reference_duplicates_preserved"] is True
                     and timing["integer_multiplicities_preserved"] is True and timing["search"] == "exact"
                     and timing["distance"] == "direct_float64_euclidean", "Compact distance semantics mismatch")
    original.close(timing["duplicate_fraction"], 1 - unique / rows, "duplicate fraction")
    total = original.finite(timing["construction_seconds"], "compact construction seconds")
    unique_seconds = original.finite(timing["unique_construction_seconds"], "unique construction seconds")
    original.require(unique_seconds <= total, "Unique construction exceeds total measured construction")


def audit(output_dir, data_dir, source_dir, registration, compact_registration, *, bundle=None):
    started = time.perf_counter()
    chain = verify_chain(output_dir, registration, compact_registration, bundle)
    report = original.audit(output_dir, data_dir, source_dir, registration,
                            verified_post_run_receipts={RECEIPT: chain["receipt_sha256"]})
    report["compact_chain"] = chain
    report["original_auditor_sha256"] = report["auditor_sha256"]
    report["auditor_sha256"] = original.digest(__file__)
    if report["evidence_audit_passed"]:
        output = Path(output_dir)
        config = original.read(original.HERE / "config.json")
        result = original.read(output / "RESULTS.json")
        for dataset, status in result["datasets"].items():
            case = output / dataset
            compression = {}
            for name, timings in (
                ("QUALIFICATION_TRAIN_EMBEDDINGS.npz", [original.read(case / "QUALIFICATION.json")["full_reference_sample_timing"]]
                 if (case / "QUALIFICATION.json").is_file() else []),
                ("TRAIN_EMBEDDINGS.npz", [status["normalizer_timing"], status["test_scoring_timing"]]
                 if status["evaluation_complete"] else []),
            ):
                if not timings:
                    continue
                rows = timings[0]["reference_rows"]
                bank, _, _ = original.standardize(case / name, rows, config["training"]["hidden_dim"])
                unique, counts = np.unique(bank, axis=0, return_counts=True)
                original.require(int(counts.sum()) == rows, "Independent multiplicity count mismatch")
                for timing in timings:
                    verify_compression_timing(timing, rows, len(unique))
                if name == "QUALIFICATION_TRAIN_EMBEDDINGS.npz":
                    qualification = original.read(case / "QUALIFICATION.json")
                    transfer = qualification["resource_gate"]["components_seconds_before_multiplier"]["reference_transfer"]
                    original.require(transfer + 1e-9 >= timings[0]["construction_seconds"],
                                     "Resource gate omits measured compact bank construction")
                compression[name] = {"original_rows": rows, "independently_counted_unique_rows": len(unique),
                                     "sum_integer_multiplicities": int(counts.sum()), "timing_receipts_checked": len(timings)}
                del bank, unique, counts
            report["datasets"][dataset]["compression_inventory"] = compression
    report["elapsed_seconds"] = time.perf_counter() - started
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("output-dir", "data-dir", "source-dir", "registration", "compact-registration", "audit-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--bundle", type=Path, help="Optional original input bundle for independent archive-byte binding")
    args = parser.parse_args(argv)
    destination = args.audit_output.resolve()
    for path in (args.output_dir, args.data_dir, args.source_dir):
        original.require(not destination.is_relative_to(path.resolve(strict=True)), "Audit output must be outside evidence/input trees")
    destination.mkdir(parents=True, exist_ok=False)
    try:
        report = audit(args.output_dir, args.data_dir, args.source_dir, args.registration,
                       args.compact_registration, bundle=args.bundle)
    except Exception as error:
        report = {"status": "INVALID_OR_UNVERIFIABLE_EVIDENCE", "evidence_audit_passed": False,
                  "scientific_completion": False, "negative_scientific_conclusion": False,
                  "error_type": type(error).__name__, "reason": str(error), "auditor_sha256": original.digest(__file__),
                  "checked_utc": datetime.now(timezone.utc).isoformat()}
    (destination / "AUDIT.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    summary = "# Independent compact MAGIC evidence audit\n\nStatus: **" + report["status"] + "**.\n\n"
    summary += "Scientific completion: " + str(report["scientific_completion"]) + ". A resource hold is not a negative scientific result.\n\n"
    summary += "The separate compact source chain and receipt are checked before the original independent evidence audit. Original full-reference distances and integer multiplicities are independently verified; neural training and embedding inference are not rerun. AWS closure requires its separate operational receipts.\n"
    if "reason" in report:
        summary += "\nReason: " + report["reason"] + "\n"
    (destination / "AUDIT.md").write_text(summary, encoding="utf-8")
    print(json.dumps({"status": report["status"], "scientific_completion": report["scientific_completion"]}))
    return 0 if report.get("evidence_audit_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
