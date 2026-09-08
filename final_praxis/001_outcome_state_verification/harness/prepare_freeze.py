"""One-time prospective freeze. Refuses to overwrite existing freeze artifacts."""
from datetime import datetime, timezone
from dataclasses import asdict
import json
import subprocess
import sys
from .scientific_protocol import ROOT, allocation, instantiate, file_hash, digest, write_new
from .validate_fixtures import validate

def main():
    if (ROOT / "FROZEN_PROTOCOL.json").exists():
        raise SystemExit("Freeze exists; use a dated amendment, do not overwrite it")
    errors = validate(ROOT / "artifacts/fixtures/fixtures.jsonl")
    if errors:
        raise SystemExit(errors)
    result = subprocess.run([sys.executable, "-m", "unittest", "final_praxis.001_outcome_state_verification.harness.test_scientific", "-v"],
                            capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(result.stdout + result.stderr)
    evidence = ROOT / "artifacts/fixtures/SCIENTIFIC_INFRASTRUCTURE_TESTS_20260908.txt"
    with evidence.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(result.stdout + result.stderr)
    original = json.loads((ROOT / "configs/experiment.json").read_text(encoding="utf-8"))
    config = {"experiment_id": "Final Praxis 001", "design": "controlled_evaluator_stress_with_separate_natural_action_states",
        "agent": {"model_id": "Qwen/Qwen2.5-7B-Instruct", "revision": "a09a35458c702b33eeacc393d103063234e8bc28"},
        "judge": {"model_id": "mistralai/Mistral-7B-Instruct-v0.3", "revision": "c170c708c41dac9275d15a8fff4eca08d52bab71"},
        "dtype": "bfloat16", "quantization": None, "temperature": 0.0, "seed": 20260908,
        "runtime_target": {"torch": "2.5.1+cu121", "transformers": "4.57.6", "attention": "sdpa"},
        "action_max_new_tokens": 384, "claim_max_new_tokens": 192, "judge_max_new_tokens": 192,
        "max_actions": 12, "infrastructure_retry_max": 2, "semantic_retry_max": 0,
        "primary_units": 400, "pilot_units": 16, "full_state_diagnostic_units": 40,
        "condition_counts": {"clean_success": 100, "alternate_valid": 100, "incomplete_completion": 50,
                             "false_success_claim": 50, "partial_success": 50, "collateral_damage": 50},
        "promotion_gates": original["promotion_gates"], "bootstrap_replicates": 10000,
        "fixture_sha256": file_hash(ROOT / "artifacts/fixtures/fixtures.jsonl"),
        "synthetic_model_output_fallback_allowed": False, "exclusions": [],
        "notes": "State interventions are scripted; all scientific model decisions must be real inference."}
    write_new(ROOT / "configs/scientific_v1.json", config)
    for stage in ("pilot", "discovery"):
        write_new(ROOT / f"configs/{stage}_allocation.json", allocation(stage))
    write_new(ROOT / "configs/scientific_tasks.json", {unit["instance_id"]: asdict(instantiate(unit["task_id"], unit["instance_id"]))
        for stage in ("pilot", "discovery") for unit in allocation(stage)})
    fixtures = [json.loads(line) for line in (ROOT / "artifacts/fixtures/fixtures.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    write_new(ROOT / "artifacts/fixtures/GATE2_PASS.json", {"status": "PASS", "date": "2026-09-08", "legacy_fixture_count": 140,
        "unit_tests": 14, "controlled_state_checks": 400, "fixture_sha256": config["fixture_sha256"],
        "fixture_semantic_sha256": digest(fixtures), "test_evidence_sha256": file_hash(evidence),
        "historical_marker_retained": True, "amendment": "AMENDMENT_20260908_PRE_RESULTS.md"})
    paths = ["PREREGISTRATION_v1.md", "AMENDMENT_20260908_PRE_RESULTS.md", "configs/scientific_v1.json",
        "configs/pilot_allocation.json", "configs/discovery_allocation.json", "configs/scientific_tasks.json",
        "artifacts/fixtures/fixtures.jsonl", "artifacts/fixtures/GATE2_PASS.json", "artifacts/fixtures/SCIENTIFIC_INFRASTRUCTURE_TESTS_20260908.txt",
        "001_SAMPLE_SIZE_AND_FROZEN_GATES_20260908.md", "001_FROZEN_TASK_CATALOG_20260908.md",
        "harness/scientific_protocol.py", "harness/scientific_runner.py", "harness/run_scientific.py",
        "harness/verifier.py", "harness/task_registry.py", "harness/models.py", "harness/verify_scientific.py",
        "harness/test_scientific.py", "../shared/model_adapter.py", "../shared/inference_server.py"]
    write_new(ROOT / "FROZEN_PROTOCOL.json", {"experiment_id": "Final Praxis 001", "version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(), "result_inspection_before_freeze": False,
        "artifact_hashes": {path: file_hash(ROOT / path) for path in paths}})
    print(json.dumps({"status": "FROZEN", "sha256": file_hash(ROOT / "FROZEN_PROTOCOL.json"), "unit_tests": 14}))

if __name__ == "__main__":
    main()
