"""Check every file recorded in MANIFEST.json; no external dependencies."""
import hashlib
import json
from pathlib import Path, PurePosixPath


def verify(root):
    root = root.resolve()
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    failures = []
    seen = set()
    for row in manifest["files"]:
        relative = PurePosixPath(row["file"])
        if relative.is_absolute() or ".." in relative.parts or row["file"] in seen:
            failures.append({"file": row["file"], "reason": "invalid/duplicate manifest path"})
            continue
        seen.add(row["file"])
        path = root.joinpath(*relative.parts).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            failures.append({"file": row["file"], "reason": "missing or outside package"})
            continue
        raw = path.read_bytes()
        if len(raw) != row["bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            failures.append({"file": row["file"], "reason": "size/hash mismatch"})
    return {"status": "PASS" if not failures else "FAIL", "files_checked": len(seen), "failures": failures}


if __name__ == "__main__":
    result = verify(Path(__file__).parent)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
