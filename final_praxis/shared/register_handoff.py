"""Maintain the three Final Praxis handoff entries without touching older studies."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "s3://praxis-garypagan-272615233626-us-east-1/final-praxis/20260908/"
HYPOTHESES = {
    "001": "A deterministic state verifier reduces false-success acceptance against a distinct learned judge while preserving valid completion acceptance on a controlled evaluator-stress corpus.",
    "002": "Deterministic handoff and final-action boundaries contain induced multi-agent errors while preserving clean utility and changing propagation beyond a final-action gate alone.",
    "003": "Mechanically reviewed stability stopping preserves utility, prevents degradation and saves counterfactual investigation cost under frozen harm and review gates.",
}
data = json.loads((ROOT / "final_praxis/status.json").read_text(encoding="utf-8"))
registry_path = ROOT / "configs/experiment_cloud_handoff_registry.json"
registry = json.loads(registry_path.read_text(encoding="utf-8"))
for state in data["experiments"]:
    ident = state["id"]
    folder = next((ROOT / "final_praxis").glob(ident + "_*"))
    rel = folder.relative_to(ROOT).as_posix()
    manifest = {
        "id": "final-praxis-" + ident, "name": state["title"], "created": "2026-09-08", "updated": data["updated_utc"],
        "status": state["status"], "posture": "verified" if state.get("scientifically_complete") else "in_progress",
        "owner": "garyp", "hypothesis": HYPOTHESES[ident],
        "falsification_criteria": ["Apply every numeric promotion/kill threshold in the frozen preregistration.", "Missing raw records, identity/hash mismatch or unverifiable evidence prevents scientific classification."],
        "datasets": [{"id": "final-praxis-" + ident + "-frozen-generated-corpus", "local_paths": [rel + "/configs/"],
                      "s3_prefixes": [BASE + "code/"], "label_requirements": "Frozen deterministic labels for transparently generated inert scenarios; no external incident population is claimed."}],
        "code": {"entrypoints": [rel + "/harness/"], "configs": [rel + "/FROZEN_PROTOCOL.json", rel + "/PREREGISTRATION_v1.md"],
                 "tests": [rel + "/FIXTURE_GATE.md"], "cloud_jobs": ["final_praxis/shared/"]},
        "artifact_policy": {"commit_lightweight_paths": [rel + "/", "final_praxis/status.json", "FINAL_PRAXIS_PROPOSALS.md"],
                            "do_not_commit_paths": [rel + "/runs/", rel + "/artifacts/discovery/", rel + "/artifacts/pilot/"],
                            "s3_output_prefix": BASE + ident + "/"},
        "current_decision": state["status"], "next_action": state["next"],
        "cloud_startup_notes": ["Read FINAL_PRAXIS_EXECUTION_RUNBOOK.md and execution/20260908/EXECUTION_PLAN.md.",
                                "Retrieve exact source bundles and raw evidence from the recorded S3 prefix; never regenerate frozen inputs silently.",
                                "Do not overwrite completed runs, alter frozen thresholds, or count pilots/fixtures as scientific results."]}
    (folder / "CLOUD_HANDOFF_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    entry = {"id": manifest["id"], "name": state["title"], "posture": manifest["posture"], "best_evidence": state["evidence"],
             "decision": state["status"], "lightweight_evidence_paths": [rel + "/CLOUD_HANDOFF_MANIFEST.json", rel + "/FROZEN_PROTOCOL.json", rel + "/FIXTURE_GATE.md", "FINAL_PRAXIS_PROPOSALS.md"],
             "cloud_artifact_prefixes": [BASE + ident + "/", BASE + "code/"], "next_cloud_action": state["next"]}
    if state.get("report"):
        entry["lightweight_evidence_paths"].append("final_praxis/" + state["report"])
    previous = next((i for i,x in enumerate(registry["experiments"]) if x["id"] == manifest["id"]), None)
    if previous is None:
        registry["experiments"].append(entry)
    else:
        registry["experiments"][previous] = entry
registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
print("Updated three Final Praxis handoff entries.")
