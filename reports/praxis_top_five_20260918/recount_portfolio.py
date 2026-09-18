"""Read-only recount of selected archived portfolio evidence; no model calls.

The PX011 metadata comparator is a September 18 post hoc diagnostic. It does
not alter the historical primary outcome or supply independent confirmation.
"""
from pathlib import Path
import csv
import hashlib
import json
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MANIFEST = json.loads((OUT / "EVIDENCE_SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
SNAPSHOTS = {x["original_path"]: x for x in MANIFEST["files"]}


def artifact(rel):
    snap = SNAPSHOTS.get(str(rel).replace("\\", "/"))
    path = OUT / snap["snapshot_path"] if snap else ROOT / rel
    if snap:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == snap["sha256"], str(path)
    return path


def read(rel):
    return json.loads(artifact(rel).read_text(encoding="utf-8-sig"))


def main():
    for entry in MANIFEST["files"]:
        artifact(entry["original_path"])
    sources = [
        "reports/cti_external_validation_20260918/RESULTS.json",
        "reports/cti_external_validation_20260918/DECISION.md",
        "reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_SUMMARY_20260624.json",
        "reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/summary.json",
        "reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/scored_identifiers_sanitized.csv",
        "reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json",
        "reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl",
        "cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py",
        "reports/refusal_direction_quantization/e1_e4_20260831/closeout_r3/PX055_R3_INDEPENDENT_ADJUDICATION.json",
        "reports/praxis_top_three_decision_20260915/04_PX055_DISPOSITION.md",
        "reports/tta_streaming_apt/px001_r2_unsw_independent_20260731/aws_full_retry1/px001_r2_unsw_independent_20260731/preregistered_adjudication.json",
        "reports/px057_novelty_review_20260918/EXPERIMENT_AUDIT.md",
        "reports/praxis_paper_008_20260914/PORTFOLIO_REVIEW.md",
        "reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md",
    ]
    falsecite = read(sources[2])
    f = {k: v["split_metrics"]["strict_holdout"] for k, v in falsecite["conditions"].items()}
    assert f["base_model"]["fn_fabricated_accepted"] == 6
    for arm in ("citation_aware_verifier", "metadata_evidence"):
        assert f[arm]["fn_fabricated_accepted"] == 0
        assert f[arm]["tn_valid"] == 8
    registry = read(sources[3])
    with artifact(sources[4]).open(encoding="utf-8-sig", newline="") as fh:
        registry_rows = list(csv.DictReader(fh))
    actions = Counter(x["gate_action"] for x in registry_rows)
    statuses = Counter(x["status"] for x in registry_rows)
    escapes = sum(x["status"] == "nonexistent" and x["gate_action"] == "allow" for x in registry_rows)
    assert len(registry_rows) == registry["extractions"] == 1282
    assert actions["block"] == statuses["nonexistent"] == registry["deterministic_gate_blocks"] == 232
    assert actions["review"] == registry["ambiguous_verifications"] == 116
    assert escapes == registry["known_missing_escapes"] == 0
    hallu = read(sources[5])
    rows = [json.loads(line) for line in artifact(sources[6]).read_text(encoding="utf-8").splitlines()]
    conf = Counter(f'{r["label"]}|{r["verifier_prediction"]}' for r in rows)
    primary_correct = sum(r["label"] == r["verifier_prediction"] for r in rows)
    identity_correct = sum(("supported" if r["source_id_match"] else "hallucinated") == r["label"] for r in rows)
    # Same metadata threshold as the archived verifier, without content gating.
    metadata_correct = sum(("supported" if r["source_id_match"] and r["year_match"] and r["title_similarity"] >= .90 else "hallucinated") == r["label"] for r in rows)
    assert len(rows) == 500 and primary_correct == 452
    assert primary_correct / len(rows) == hallu["verifier_metrics"]["accuracy"]
    assert identity_correct == 488 and metadata_correct == 500
    quant = read(sources[8])
    assert quant["completeness"]["fully_eligible_cells"] == 9
    assert quant["e1"]["h1"] is True
    assert quant["e2"]["minimum_directional_ratio"] == .975
    tta = read(sources[10])
    assert tta["passed"] == 0 and tta["total"] == 6
    cti = read(sources[0])
    assert cti["n"] == 1247 and cti["fresh_outputs"] == 4988
    assert cti["status"] == "EXTERNAL_TRANSPORT_CRITERIA_NOT_MET"
    cti_all = cti["metrics"]["all"]["arms"]
    assert [cti_all["always_vanilla"]["models"][m]["correct"] for m in ("llama", "qwen")] == [1079, 1086]
    assert [cti_all["evidence_utility"]["models"][m]["correct"] for m in ("llama", "qwen")] == [1075, 1088]
    code_recount = json.loads((OUT / "evidence/code_review/INDEPENDENT_RECOUNT.json").read_text(encoding="utf-8-sig"))
    code_models = json.loads((OUT / "evidence/code_review/MODEL_RESULTS.json").read_text(encoding="utf-8-sig"))
    code_h1 = next(x for x in code_recount["primary"] if x["hypothesis"] == "H1" and x["reviewer"].startswith("qwen."))
    assert (code_h1["left_accepts"], code_h1["right_accepts"], code_h1["tasks"]) == (12, 4, 101)
    assert code_h1["holm4_adjusted_p"] == .015625
    code_primary = next(x for x in code_models["primary_hypotheses"] if x["hypothesis"] == "H1" and x["reviewer"].startswith("qwen."))
    assert abs(code_primary["difference"] - 8 / 101) < 1e-15
    assert code_primary["holm4_adjusted_p"] == code_h1["holm4_adjusted_p"]
    result = {
        "audit_date": "2026-09-18",
        "status": "PASS_SAVED_ARTIFACT_RECOUNT",
        "scope": "Independent arithmetic and receipt inspection; no fresh inference, human judgment, exhaustive literature review, or academic approval.",
        "recommended_order": [
            {"rank": 1, "title": "Reliable review of AI code changes", "internal_id": "Final-008", "evidence_kind": "completed_positive_risk_finding_defense_failed"},
            {"rank": 2, "title": "Checking whether security evidence applies", "internal_id": "CTI", "evidence_kind": "bounded_positive_evidence_effect_external_checker_failed"},
            {"rank": 3, "title": "Verifying software references before trusting them", "internal_id": "PX-004", "evidence_kind": "small_bounded_working_guard"},
            {"rank": 4, "title": "Checking model and dataset references before use", "internal_id": "PX-056", "evidence_kind": "positive_live_pilot_incomplete_validation"},
            {"rank": 5, "title": "Checking what model compression preserves", "internal_id": "PX-055", "evidence_kind": "positive_geometry_replication_reserve_novelty_hold"},
        ],
        "code_disclosure": {"independently_recounted_source": code_h1, "primary_ci95": code_primary["ci95"], "defense_status": "BOTH_PRIMARY_HYBRID_RECOMMENDATION_GATES_FAILED"},
        "cti_external": {"status": cti["status"], "n": cti["n"], "fresh_outputs": cti["fresh_outputs"], "baseline_correct": [1079, 1086], "candidate_correct": [1075, 1088], "model_order": ["llama", "qwen"], "useful_signal": cti["useful_signal"], "added_value": cti["added_value"]},
        "falsecite_strict_holdout": {
            "n": 15, "fabricated": 7, "valid": 8,
            "base_fabricated_accepted": 6, "guard_fabricated_accepted": 0,
            "metadata_prompt_fabricated_accepted": 0,
            "guard_valid_accepted": 8, "metadata_prompt_valid_accepted": 8,
        },
        "registry_pilot": {
            "outputs": registry["outputs"], "identifier_occurrences": len(registry_rows),
            "actions": dict(actions), "statuses": dict(statuses), "known_missing_escapes": escapes,
            "physical_registry_missing": registry["physical_registry_nonexistent"],
            "physical_registry_verified": registry["physical_registry_verified_denominator"],
            "package_missing": registry["package_nonexistent"],
            "package_verified": registry["package_verified_denominator"],
            "null_control_extractions": registry["null_control_extractions"],
        },
        "source_locked_citations": {
            "n_pairs": len(rows), "n_generations": hallu["generations"],
            "archived_confusion": dict(conf), "archived_correct": primary_correct,
            "posthoc_identity_only_correct": identity_correct,
            "posthoc_metadata_only_correct": metadata_correct,
            "posthoc_rule": "supported iff source_id_match and year_match and title_similarity >= 0.90; otherwise hallucinated",
            "interpretation": "The obvious metadata-only comparator exceeds the archived verifier on the constructed source-swapping labels. This retrospective diagnostic does not change the original primary PASS and does not independently validate a new method.",
        },
        "quantization_geometry": {
            "complete_cells": quant["completeness"]["fully_eligible_cells"],
            "max_principal_angle_degrees": quant["e1"]["max_principal_angle_degrees"],
            "minimum_directional_ratio": quant["e2"]["minimum_directional_ratio"],
            "status": "BOUNDED_GEOMETRY_POSITIVE_RESTORATION_UNPROVEN_NOVELTY_HOLD",
        },
        "tta_external": tta,
        "source_manifest": [{"path": x, "snapshot_path": SNAPSHOTS[x]["snapshot_path"], "sha256": hashlib.sha256(artifact(x).read_bytes()).hexdigest()} for x in sources],
    }
    external_base = Path("C:/w/px_final_20260917/final_praxis/final_three_20260917")
    result["completed_paper_sources"] = []
    for rel in ("01_cti/PAPER.md", "01_cti/slide_summary.json", "02_008/PAPER.md", "02_008/slide_summary.json", "03_010/PAPER.md"):
        path = artifact(str(external_base / rel))
        if path.exists():
            result["completed_paper_sources"].append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    (OUT / "EVIDENCE_AUDIT.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "source_files": len(sources), "px011_metadata_only_correct": metadata_correct}))


if __name__ == "__main__":
    main()
