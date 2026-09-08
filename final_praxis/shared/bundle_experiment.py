"""Create a content-addressed source bundle without prior scientific outputs."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("id", choices=["001", "002", "003"])
    args = parser.parse_args()
    experiment = next((ROOT / "final_praxis").glob(args.id + "_*"))
    files = [p for p in experiment.rglob("*") if p.is_file() and not
             set(p.relative_to(experiment).parts).intersection({"__pycache__", "runs", "pilot", "discovery"})
             and p.suffix not in {".pyc", ".zip"}]
    files += [ROOT / "final_praxis" / "shared" / name for name in ["__init__.py", "model_adapter.py", "inference_server.py"]]
    manifest = {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(files)}
    digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    target = ROOT / "tmp" / f"final_praxis_{args.id}_{digest[:12]}.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr(f"final_praxis/execution/20260908/fp{args.id}-bundle-manifest.json", json.dumps(manifest, indent=2))
    print(json.dumps({"bundle": str(target), "content_manifest_sha256": digest,
                      "archive_sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "bytes": target.stat().st_size,
                      "files": len(files)}, indent=2))


if __name__ == "__main__":
    main()
