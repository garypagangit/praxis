"""Offline scored-record replay. Current release accepts software fixtures only.

Input scores and eligibility decisions are fixed upstream. This module cannot
authenticate their provenance or establish independence from a group ID.
Real-data replay remains disabled until a versioned G0/G1 release is reviewed.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from calibration import apply_certificate, calibrate


FIXTURE_SCOPE = "SOFTWARE_FIXTURE_NOT_SOC_EVIDENCE"


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def validate_input(document):
    if not isinstance(document, dict) or document.get("scope") != FIXTURE_SCOPE:
        raise ValueError("Real-data replay is unreleased: resolve G0 and register G1-G5 first")
    for field in ("scorer_contract", "predicate_contract"):
        if not isinstance(document.get(field), dict) or not document[field]:
            raise ValueError(f"Missing explicit frozen {field}")
        canonical_hash(document[field])
    rows = document.get("records")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Nonempty records are required")
    ids, groups = set(), {"calibration": set(), "test": set()}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every record must be an object")
        for key in ("record_id", "group_id"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"Missing {key}")
        if row["record_id"] in ids:
            raise ValueError("Duplicate record ID")
        ids.add(row["record_id"])
        role = row.get("role")
        if not isinstance(role, str) or role not in groups:
            raise ValueError("Replay roles must be calibration or test")
        groups[role].add(row["group_id"])
        for key in ("attack", "eligible"):
            if type(row.get(key)) is not bool:
                raise ValueError(f"{key} must be boolean")
        score = row.get("benignness")
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ValueError("Scores must be finite numbers")
        try:
            finite = math.isfinite(score)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("Scores must be finite numbers")
    if groups["calibration"] & groups["test"]:
        raise ValueError("A group crosses calibration and test roles")
    calibration = [r for r in rows if r["role"] == "calibration"]
    test = [r for r in rows if r["role"] == "test"]
    if not calibration or not test or not any(r["attack"] for r in calibration):
        raise ValueError("Calibration attacks and a nonempty test split are required")
    if {r["attack"] for r in test} != {False, True}:
        raise ValueError("Test requires both attack and non-attack examples")
    return calibration, test


def metrics(mask, test):
    attacks = np.array([r["attack"] for r in test], dtype=bool)
    positives, negatives = int(attacks.sum()), int((~attacks).sum())
    suppressed_attacks = int((mask & attacks).sum())
    suppressed_benign = int((mask & ~attacks).sum())
    return {
        "test_attack_count": positives, "test_non_attack_count": negatives,
        "suppressed_attack_count": suppressed_attacks,
        "suppressed_non_attack_count": suppressed_benign,
        "empirical_attack_suppression_fraction": suppressed_attacks/positives,
        "empirical_non_attack_suppression_fraction": suppressed_benign/negatives,
        "empirical_total_alert_suppression_fraction": float(mask.mean()),
        "population_risk_validation": "NOT_ESTABLISHED_BY_THIS_FINITE_FIXTURE_TEST",
    }


def evaluate(document, alpha=.01, delta=.05):
    calibration, test = validate_input(document)
    attack_rows = [r for r in calibration if r["attack"]]
    attack_scores = np.array([r["benignness"] for r in attack_rows])
    attack_eligible = np.array([r["eligible"] for r in attack_rows])
    scores = np.array([r["benignness"] for r in test])
    eligible = np.array([r["eligible"] for r in test])
    binding = {"scope": FIXTURE_SCOPE, "input_canonical_sha256": canonical_hash(document),
               "scorer_contract_sha256": canonical_hash(document["scorer_contract"]),
               "predicate_contract_sha256": canonical_hash(document["predicate_contract"])}
    plain = calibrate(attack_scores, alpha=alpha, delta=delta, metadata=binding)
    gated = calibrate(attack_scores, attack_eligible, alpha=alpha, delta=delta, metadata=binding)
    # Published marginal class-conditional recipe, expressed in benignness
    # orientation. This is a formula comparator, not reproduction of its paper.
    # A strict threshold is conservative under ties. It has a different
    # guarantee from a PAC tolerance bound at the same nominal alpha.
    marginal_k = math.floor(alpha * (len(attack_scores) + 1))
    marginal_threshold = (math.inf if marginal_k == 0 else
                          float(np.sort(attack_scores)[len(attack_scores)-marginal_k]))
    masks = {
        "keep_all": np.zeros(len(test), dtype=bool),
        "marginal_order_statistic_formula_only": scores > marginal_threshold,
        "pac_score_only": apply_certificate(plain, scores),
        "pac_score_and_predicates": apply_certificate(gated, scores, eligible),
    }
    decisions = [{"record_id": row["record_id"], "group_id": row["group_id"],
                  "attack": row["attack"], "eligible": row["eligible"],
                  **{name: bool(mask[i]) for name, mask in masks.items()}}
                 for i, row in enumerate(test)]
    result = {
        "scope": FIXTURE_SCOPE, "status": "SOFTWARE_REPLAY_COMPLETE_NO_EFFICACY_CLAIM",
        "binding": binding, "alpha": alpha, "delta_per_pac_arm": delta,
        "simultaneous_certification": False,
        "calibration_records": len(calibration), "calibration_attack_records": len(attack_rows),
        "certificates": {"pac_score_only": plain.to_dict(),
                         "pac_score_and_predicates": gated.to_dict()},
        "marginal_comparator": {"k": marginal_k,
                                "threshold": None if marginal_k == 0 else marginal_threshold,
                                "keep_all": marginal_k == 0,
                                "reference": "https://doi.org/10.3390/electronics15184084",
                                "claim": "FORMULA_ONLY_NOT_PAPER_REPRODUCTION_OR_PAC_GUARANTEE"},
        "metrics": {name: metrics(mask, test) for name, mask in masks.items()},
        "limitations": ["Artificial examples do not establish cybersecurity performance",
                        "No arm is selected from these evaluation outcomes",
                        "Input hashes bind bytes, not the truth of upstream provenance",
                        "Distinct group IDs do not prove independent attacks",
                        "No confidence interval is computed from potentially correlated alert rows"],
    }
    return result, decisions


def run(source, output):
    document = json.loads(source.read_text(encoding="utf-8"))
    result, decisions = evaluate(document)
    if output.exists():
        raise ValueError("Output exists; preserve previous attempts")
    output.mkdir(parents=True)
    result["created_utc"] = datetime.now(timezone.utc).isoformat()
    result["input_file_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    result["code_sha256"] = {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                             for name in ("replay.py", "calibration.py")}
    with (output/"DECISIONS.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(decisions[0]))
        writer.writeheader()
        writer.writerows(decisions)
    result["decisions_sha256"] = hashlib.sha256((output/"DECISIONS.csv").read_bytes()).hexdigest()
    (output/"RESULTS.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "calibration_records": result["calibration_records"],
                      "test_records": len(decisions), "real_alerts_scored": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.input, args.output)
