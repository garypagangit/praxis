"""Optional public-source download with exact historical hash; never invokes models."""
import argparse
import hashlib
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="External cache CSV path outside this release")
    args = parser.parse_args()
    if root == args.output.resolve() or root in args.output.resolve().parents:
        raise SystemExit("Use an external cache path to preserve the release's no-prompt-text boundary")
    manifest = json.loads((root / "evidence/source/XSTEST_ID_MANIFEST.json").read_text())
    data = urllib.request.urlopen(manifest["source_url"], timeout=60).read()
    if hashlib.sha256(data).hexdigest() != manifest["source_sha256"]:
        raise SystemExit("Public source has changed; no output written. Obtain the historical CSV matching the documented hash.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(json.dumps({"pass": True, "sha256": manifest["source_sha256"], "bytes": len(data)}))
