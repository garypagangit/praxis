"""Capture final software tests and hash checks; never imply human approval."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import re
import subprocess
import sys


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(output):
    root = Path(__file__).resolve().parent
    repo = root.parents[1]
    if output.exists():
        raise ValueError("Preserve previous verification attempts")
    output.mkdir(parents=True)
    command = [sys.executable, "-m", "unittest", "discover", "-s", "experiments/cert_gate/tests", "-v"]
    completed = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               encoding="utf-8", errors="replace")
    (output/"UNITTEST.txt").write_text(completed.stdout, encoding="utf-8")
    counts = re.search(r"Ran (\d+) tests? in", completed.stdout)
    if completed.returncode != 0 or counts is None:
        raise RuntimeError("Tests did not pass; inspect saved UNITTEST.txt")
    checked = {}
    for relative in ("results/g0_20260920_v2/ELIGIBILITY_AND_REVIEW.json",
                     "results/qualification_20260920_v2/RESULTS.json",
                     "results/replay_fixture_20260920/run/RESULTS.json"):
        path = root/relative
        receipt = json.loads(path.read_text(encoding="utf-8"))
        for name, expected in receipt["code_sha256"].items():
            if sha(root/name) != expected:
                raise ValueError(f"Code hash mismatch for {relative}: {name}")
        if "registration_sha256" in receipt and sha(root/"REGISTRATION.json") != receipt["registration_sha256"]:
            raise ValueError("Registration hash mismatch")
        checked[relative] = sha(path)
    q = json.loads((root/"results/qualification_20260920_v2/RESULTS.json").read_text())
    arrays = root/"results/qualification_20260920_v2/SIMULATION_ARRAYS.npz"
    if sha(arrays) != q["simulation_arrays_sha256"] or arrays.read_bytes() != (root/"results/qualification_20260920/SIMULATION_ARRAYS.npz").read_bytes():
        raise ValueError("Qualification arrays changed or have wrong hash")
    original = root/"source/USER_PROPOSAL.txt"
    if sha(original) != "7b5ce9e793c1caf24d7b90325601d8aeaa47f710a481bb827c8e1fcececc1f01":
        raise ValueError("Original proposal bytes changed")
    source_paths = sorted(root.glob("*.py")) + sorted((root/"tests").glob("*.py"))
    result = {
        "status": "SOFTWARE_TESTS_AND_ARTIFACT_BINDINGS_PASS_NOT_HUMAN_REVIEW",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "command": command, "exit_code": completed.returncode,
        "tests_run": int(counts.group(1)), "python": sys.version,
        "packages": {name: version(name) for name in ("numpy", "scipy", "scikit-learn")},
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "source_sha256": {str(path.relative_to(root)).replace("\\", "/"): sha(path) for path in source_paths},
        "checked_result_receipts_sha256": checked,
        "qualification_v1_v2_npz_byte_identical": True,
        "original_user_proposal_sha256": sha(original),
        "test_log_sha256": sha(output/"UNITTEST.txt"),
        "real_soc_model_runs": 0, "human_review_completed": False, "qwen_inference_tested": False,
    }
    (output/"TEST_RECEIPT.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "tests_run": result["tests_run"],
                      "source_commit": result["source_commit"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args().output)
