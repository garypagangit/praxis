"""Verify Git's committed bytes against every current scientific freeze."""
import hashlib
import argparse
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--read-only", action="store_true")
args = parser.parse_args()
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
results = []
for folder in sorted((root / "final_praxis").glob("00*")):
    freeze_path = folder / "FROZEN_PROTOCOL.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    files = freeze.get("files", freeze.get("artifact_hashes"))
    errors = []
    for name, expected in files.items():
        target = (folder / name).resolve()
        relative = target.relative_to(root).as_posix()
        result = subprocess.run(["git", "cat-file", "blob", f"{commit}:{relative}"], cwd=root, capture_output=True)
        if result.returncode or hashlib.sha256(result.stdout).hexdigest() != expected:
            errors.append(relative)
    results.append({"experiment": folder.name[:3], "frozen_files": len(files), "errors": errors, "status": "PASS" if not errors else "FAIL"})
receipt = {"commit": commit, "status": "PASS" if all(x["status"] == "PASS" for x in results) else "FAIL", "experiments": results}
if not args.read_only:
    (root / "final_praxis/execution/20260908/GIT_FROZEN_BYTE_AUDIT.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
if receipt["status"] != "PASS":
    raise SystemExit(1)
