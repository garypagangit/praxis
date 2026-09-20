"""Supplemental fixed-model check on additional covered AIT source files.

These negatives mean author-rule nonmatch, not independently adjudicated normal.
Use explicit source clocks within archived preprocessing epochs only. No fitting,
threshold selection, model selection, inference of missing time zones or updates
to the original pilot are performed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer
from threadpoolctl import threadpool_limits

from .ait_adapter import HASH_DIMENSIONS, normalized_text, source_timestamp
from .contracts import sha256_file, write_json
from .models import resolve_threshold, score_binary


def score(expansion, private_pilot, output):
    if output.exists():
        raise ValueError("Choose a new supplemental output; existing results are immutable")
    pilot = json.loads((private_pilot / "results.json").read_text())
    protocol = json.loads((private_pilot / "frozen_protocol.json").read_text())
    qualified = json.loads((private_pilot / "qualification.json").read_text())
    old_files = {(r["scenario"], "gather/" + r["source"]) for r in qualified["files"]}
    texts, groups, inventory, excluded = [], [], [], Counter()
    receipts = {}
    for scenario in protocol["splits"]["test"]:
        receipt_path = expansion / scenario / "ACQUISITION.json"
        receipt = json.loads(receipt_path.read_text())
        if (not receipt["complete"] or receipt["record"] != 19483937
                or receipt["label_basis"] != "AUTHOR_RULE_NONMATCH_FROM_COVERED_FILE"):
            raise ValueError("Unqualified background acquisition")
        receipts[scenario] = sha256_file(receipt_path)
        start, end = (receipt["observation_epoch"][k] for k in ("start", "end"))
        for member in receipt["members"]:
            if (scenario, member["name"]) in old_files:
                raise ValueError("Supplement must not duplicate an original pilot source file")
            if (member["annotation_file_present"] or not member["ingestion_completed_proof"]
                    or member["label_basis"] != receipt["label_basis"]):
                raise ValueError("Unknown coverage or unexpected annotation")
            path = expansion / scenario / member["local_relative_path"]
            if not member["crc32_verified"] or sha256_file(path) != member["sha256"]:
                raise ValueError("Background source bytes changed")
            accepted = 0
            with path.open(encoding="utf-8", errors="strict") as handle:
                for raw in handle:
                    at = source_timestamp(raw, member["source_type"])
                    if at is None:
                        excluded["no_explicit_source_clock"] += 1
                        continue
                    if not start <= at < end:
                        excluded["outside_archived_observation_epochs"] += 1
                        continue
                    texts.append(normalized_text(raw, member["source_type"]))
                    groups.append(scenario)
                    accepted += 1
            inventory.append({"scenario": scenario, "source": member["name"],
                              "source_sha256": member["sha256"], "eligible_rows": accepted})
    if not texts:
        raise ValueError("No eligible background records")
    X = HashingVectorizer(n_features=HASH_DIMENSIONS, alternate_sign=False,
                         ngram_range=(1, 2), norm="l2", dtype=np.float32).transform(texts).toarray()
    group_array = np.array(groups)
    result = {"status": "SUPPLEMENTAL_DEVELOPMENT_CHECK_NO_REFIT", "n_rows": len(texts),
              "label_basis": "AUTHOR_RULE_NONMATCH_FROM_COVERED_FILE",
              "source_receipt_sha256": receipts, "excluded": dict(excluded),
              "file_inventory": inventory, "models": {},
              "not_measured": ["True operational false-positive rate", "Host-hour alarm rate",
                               "Recall, F1 or ROC-AUC from this single-class supplement"],
              "scope": "Extra source files from the same two test runs; explicit source times and archived observation epochs. Shared generating environment; not independent external validation."}
    for name, entry in pilot["models"].items():
        model_path = private_pilot / (name + ".joblib")
        model = joblib.load(model_path)
        scores = score_binary(model, X)
        decisions = scores > resolve_threshold(entry["calibration"])
        per_run = {}
        for group in sorted(set(groups)):
            mask = group_array == group
            per_run[group] = {"n_rows": int(mask.sum()), "flagged_rows": int(decisions[mask].sum()),
                              "rule_nonmatch_flag_rate": float(decisions[mask].mean())}
        result["models"][name] = {"model_sha256": sha256_file(model_path),
                                 "threshold_from_original_calibration": entry["calibration"],
                                 "flagged_rows": int(decisions.sum()),
                                 "rule_nonmatch_flag_rate": float(decisions.mean()),
                                 "per_run": per_run}
    write_json(output, result)
    print(json.dumps({"rows": result["n_rows"], "excluded": result["excluded"],
                      "models": {n: {k: r[k] for k in ["flagged_rows", "rule_nonmatch_flag_rate"]}
                                 for n, r in result["models"].items()}}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expansion", type=Path, required=True)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with threadpool_limits(limits=2):
        score(args.expansion, args.pilot, args.output)
