"""Copy a small, explicit read-only evidence selection for the portfolio report."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FINAL = Path("C:/w/px_final_20260917/final_praxis/final_three_20260917")

SELECTION = [
    ("reports/cti_external_validation_20260918/RESULTS.json", "cti/EXTERNAL_RESULTS.json"),
    ("reports/cti_external_validation_20260918/DECISION.md", "cti/EXTERNAL_DECISION.md"),
    ("reports/falsecite_code/FALSECITE_CODE_MODEL_GATE_SUMMARY_20260624.json", "software_references/MODEL_GATE.json"),
    ("reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/summary.json", "registry/PILOT_SUMMARY.json"),
    ("reports/model_registry_hallucination/gate2a_live_pilot_20260721/px056-gate2a-live-pilot-20260721-202454/scored_identifiers_sanitized.csv", "registry/scored_identifiers_sanitized.csv"),
    ("reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/summary.json", "source_locked_citations/SUMMARY.json"),
    ("reports/halluhard_source_verifier/halluhard_constrained_qwen25_7b_20260701_r2/halluhard_constrained_rows.jsonl", "source_locked_citations/rows.jsonl"),
    ("cloud_jobs/halluhard_constrained_20260701/run_halluhard_constrained_gate.py", "source_locked_citations/ORIGINAL_RUNNER.py"),
    ("reports/refusal_direction_quantization/e1_e4_20260831/closeout_r3/PX055_R3_INDEPENDENT_ADJUDICATION.json", "compression/INDEPENDENT_ADJUDICATION.json"),
    ("reports/praxis_top_three_decision_20260915/04_PX055_DISPOSITION.md", "compression/LATEST_DISPOSITION.md"),
    ("reports/tta_streaming_apt/px001_r2_unsw_independent_20260731/aws_full_retry1/px001_r2_unsw_independent_20260731/preregistered_adjudication.json", "other_candidates/TTA_EXTERNAL_ADJUDICATION.json"),
    ("reports/px057_novelty_review_20260918/EXPERIMENT_AUDIT.md", "other_candidates/STOPPING_LATEST_AUDIT.md"),
    ("reports/praxis_paper_008_20260914/PORTFOLIO_REVIEW.md", "other_candidates/SEPT14_PORTFOLIO_REVIEW.md"),
    ("reports/moe_standing_committee/MOE_STANDING_COMMITTEE_SHORT_PAPER_20260628.md", "other_candidates/MOE_PAPER.md"),
    (str(FINAL / "01_cti/PAPER.md"), "cti/ORIGINAL_PAPER.md"),
    (str(FINAL / "01_cti/slide_summary.json"), "cti/ORIGINAL_METRICS.json"),
    (str(FINAL / "02_008/PAPER.md"), "code_review/PAPER.md"),
    (str(FINAL / "02_008/slide_summary.json"), "code_review/PRIMARY_METRICS.json"),
    (str(FINAL / "02_008/verification/INDEPENDENT_RECOUNT.json"), "code_review/INDEPENDENT_RECOUNT.json"),
    ("C:/w/fp008/final_praxis/008_independent_evidence_audit/code_study/completed_models/schema_extension_v2/MODEL_RESULTS.json", "code_review/MODEL_RESULTS.json"),
    (str(FINAL / "03_010/PAPER.md"), "other_candidates/FORECAST_D0_PAPER.md"),
]


def main():
    manifest = []
    for original, dest in SELECTION:
        source = Path(original)
        if not source.is_absolute():
            source = ROOT / source
        data = source.read_bytes()
        target = HERE / "evidence" / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != data:
            raise RuntimeError(f"Refusing to replace different existing snapshot: {target}")
        if not target.exists():
            shutil.copyfile(source, target)
        digest = hashlib.sha256(data).hexdigest()
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        manifest.append({"original_path": original.replace("\\", "/"), "snapshot_path": "evidence/" + dest,
                         "sha256": digest, "bytes": len(data)})
    out = {"date": "2026-09-18", "status": "BYTE_EXACT_SNAPSHOTS", "files": manifest,
           "scope": "Selected existing evidence only; linked files mentioned inside copied reports are not automatically included. Original results are unchanged."}
    (HERE / "EVIDENCE_SOURCE_MANIFEST.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"files": len(manifest), "bytes": sum(x["bytes"] for x in manifest), "status": out["status"]}))


if __name__ == "__main__":
    main()
