"""Seal the documented v2 audit-only correction, preserving all v1 evidence."""
from datetime import datetime, timezone
import json
import subprocess
import sys
from .scientific_protocol import ROOT, file_hash, write_new

def main():
    current = json.loads((ROOT / "FROZEN_PROTOCOL.json").read_text(encoding="utf-8"))
    if current["version"] != 1:
        raise SystemExit("Expected an active v1 freeze; refusing to replace another version")
    historical = ROOT / "history/protocol_v1_20260908/FROZEN_PROTOCOL.json"
    if historical.read_bytes() != (ROOT / "FROZEN_PROTOCOL.json").read_bytes():
        raise SystemExit("v1 preservation check failed")
    allowed_changes = {"harness/scientific_runner.py", "harness/verify_scientific.py", "harness/test_scientific.py"}
    for relative, expected in current["artifact_hashes"].items():
        if relative not in allowed_changes and file_hash(ROOT / relative) != expected:
            raise SystemExit("Unexpected input change during audit correction: " + relative)
    completed = subprocess.run([sys.executable, "-m", "unittest", "final_praxis.001_outcome_state_verification.harness.test_scientific", "-v"], capture_output=True, text=True)
    if completed.returncode:
        raise SystemExit(completed.stdout + completed.stderr)
    evidence = ROOT / "artifacts/fixtures/SCIENTIFIC_INFRASTRUCTURE_TESTS_V2_20260908.txt"
    with evidence.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(completed.stdout + completed.stderr)
    additional = ["AMENDMENT_20260908_AUDIT_BINDING_V2.md", "history/protocol_v1_20260908/FROZEN_PROTOCOL.json",
        "history/protocol_v1_20260908/ARCHIVE_MANIFEST.json", "artifacts/fixtures/SCIENTIFIC_INFRASTRUCTURE_TESTS_V2_20260908.txt"]
    hashes = {relative: file_hash(ROOT / relative) for relative in list(current["artifact_hashes"]) + additional}
    revised = {"experiment_id": "Final Praxis 001", "version": 2, "supersedes_sha256": file_hash(historical),
        "created_utc": datetime.now(timezone.utc).isoformat(), "discovery_started_before_freeze": False,
        "prior_pilot_status": "v1 infrastructure pilot begun; retained historical only; v2 requires a new pilot",
        "artifact_hashes": hashes}
    active = ROOT / "FROZEN_PROTOCOL.json"
    active.write_text(json.dumps(revised, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_new(ROOT / "history/PROTOCOL_VERSION_LEDGER.json", {"v1": file_hash(historical), "v2": file_hash(active),
              "amendment": "AMENDMENT_20260908_AUDIT_BINDING_V2.md"})
    print(json.dumps({"status": "FROZEN_V2", "sha256": file_hash(active), "unit_tests": 18}))

if __name__ == "__main__":
    main()
