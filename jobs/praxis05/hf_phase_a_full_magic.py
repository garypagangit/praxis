# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "torch>=2.6",
#   "sae-lens==6.43.0",
#   "PyYAML==6.0.3",
#   "dgl==1.1.2",
#   "scikit-learn>=1.3",
#   "huggingface-hub>=1.0",
# ]
# ///
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def zip_tree(source: Path, archive_path: Path) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in source.rglob("*"):
            if file_path.is_file():
                archive.write(file_path, file_path.relative_to(source))


def upload_artifacts(output_repo: str, artifact_dir: Path, repo_root: Path) -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN missing; skipping Hub upload. Results will be visible only in job logs.", flush=True)
        return

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=token)
    create_repo(output_repo, repo_type="dataset", token=token, exist_ok=True)
    for file_path in artifact_dir.rglob("*"):
        if not file_path.is_file():
            continue
        path_in_repo = str(file_path.relative_to(repo_root)).replace("\\", "/")
        print(f"Uploading {path_in_repo} to dataset repo {output_repo}", flush=True)
        api.upload_file(
            path_or_fileobj=str(file_path),
            path_in_repo=path_in_repo,
            repo_id=output_repo,
            repo_type="dataset",
            token=token,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Praxis 05 full MAGIC Phase A on Hugging Face Jobs.")
    parser.add_argument("--repo-url", default="https://github.com/garypagangit/praxis.git")
    parser.add_argument("--repo-ref", default="feature/two-stage-attack-mlp")
    parser.add_argument("--magic-url", default="https://github.com/FDUDSDE/MAGIC.git")
    parser.add_argument("--output-repo", help="HF dataset repo for result artifacts, e.g. username/praxis05-phase-a.")
    parser.add_argument("--workdir", default="/tmp/praxis05-job")
    parser.add_argument("--seeds", nargs="*", default=["13", "42", "137", "271", "1729"])
    args = parser.parse_args()

    started = time.time()
    workdir = Path(args.workdir)
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)

    praxis_dir = workdir / "praxis"
    magic_dir = workdir / "MAGIC"
    cache_dir = workdir / "activation_cache_cadets_train"
    phase_a_root = workdir / "praxis05-phase-a-full-magic"
    diagnostics_path = workdir / "results" / "praxis05" / "phase_a_full_magic" / "diagnostics.json"
    artifact_dir = workdir / "artifacts"

    print("=== Environment ===", flush=True)
    run([sys.executable, "-c", "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"])
    run([sys.executable, "-c", "import sae_lens; print('sae_lens', getattr(sae_lens, '__version__', 'unknown'))"])
    run([sys.executable, "-c", "import dgl; print('dgl', dgl.__version__)"])

    print("=== Clone repos ===", flush=True)
    run(["git", "clone", "--depth", "1", "--branch", args.repo_ref, args.repo_url, str(praxis_dir)])
    run(["git", "clone", "--depth", "1", args.magic_url, str(magic_dir)])
    praxis_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=praxis_dir, text=True).strip()
    magic_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=magic_dir, text=True).strip()

    print("=== Prepare MAGIC CADETS graphs ===", flush=True)
    graphs_zip = magic_dir / "data" / "cadets" / "graphs.zip"
    with zipfile.ZipFile(graphs_zip, "r") as archive:
        archive.extractall(magic_dir / "data" / "cadets")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(praxis_dir / "src")

    print("=== MAGIC quick eval gate ===", flush=True)
    run([sys.executable, "eval.py", "--dataset", "cadets", "--device", "-1"], cwd=magic_dir, env=env)

    print("=== Extract MAGIC activations ===", flush=True)
    run(
        [
            sys.executable,
            str(praxis_dir / "scripts" / "praxis05_03_extract_activations.py"),
            "--magic-root",
            str(magic_dir),
            "--dataset",
            "cadets",
            "--split",
            "train",
            "--output-dir",
            str(cache_dir),
            "--device",
            "-1",
        ],
        env=env,
    )

    print("=== Train full pre-registered SAEs ===", flush=True)
    run(
        [
            sys.executable,
            str(praxis_dir / "scripts" / "praxis05_04_phase_a_train_saes.py"),
            "--config",
            str(praxis_dir / "configs" / "praxis05-sae-topk-k32-x16.json"),
            "--cache-dir",
            str(cache_dir),
            "--output-root",
            str(phase_a_root),
            "--seeds",
            *args.seeds,
        ],
        env=env,
    )

    print("=== Run Phase A diagnostics ===", flush=True)
    diagnostics_exit = 0
    try:
        run(
            [
                sys.executable,
                str(praxis_dir / "scripts" / "praxis05_05_phase_a_diagnostics.py"),
                "--config",
                str(praxis_dir / "configs" / "praxis05-sae-topk-k32-x16.json"),
                "--phase-a-root",
                str(phase_a_root),
                "--output",
                str(diagnostics_path),
            ],
            env=env,
        )
    except subprocess.CalledProcessError as exc:
        diagnostics_exit = exc.returncode
        print(f"Diagnostics exited with code {diagnostics_exit}; preserving FAIL artifacts.", flush=True)

    diagnostics = read_json(diagnostics_path)
    summary = {
        "praxis": "Praxis 05",
        "phase": "A full MAGIC",
        "praxis_repo": args.repo_url,
        "praxis_ref": args.repo_ref,
        "praxis_sha": praxis_sha,
        "magic_sha": magic_sha,
        "seeds": args.seeds,
        "elapsed_seconds": time.time() - started,
        "diagnostics_exit_code": diagnostics_exit,
        "diagnostics_status": diagnostics.get("status"),
        "checks": diagnostics.get("checks"),
    }

    artifact_dir.mkdir(parents=True, exist_ok=True)
    write_json(artifact_dir / "summary.json", summary)
    shutil.copy2(diagnostics_path, artifact_dir / "diagnostics.json")
    shutil.copy2(cache_dir / "manifest.json", artifact_dir / "activation_cache_manifest.json")
    shutil.copy2(praxis_dir / "configs" / "praxis05-sae-topk-k32-x16.json", artifact_dir / "praxis05-sae-topk-k32-x16.json")
    zip_tree(phase_a_root, artifact_dir / "phase_a_full_magic_runs.zip")

    if args.output_repo:
        upload_artifacts(args.output_repo, artifact_dir, workdir)

    print("=== Praxis 05 Phase A Summary ===", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    if diagnostics_exit:
        raise SystemExit(diagnostics_exit)


if __name__ == "__main__":
    main()
