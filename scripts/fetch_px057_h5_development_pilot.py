#!/usr/bin/env python
"""Fetch and verify one completed PX-057 H5 development-pilot artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/px057_h5_development_pilot_20260727.json"
FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
    "cloud_job_evidence.json",
)


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def aws(profile: str, region: str, *args: str) -> str:
    return output(["aws", *args, "--profile", profile, "--region", region])


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_extract(archive_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            try:
                target.relative_to(destination_root)
            except ValueError as exc:
                raise ValueError(f"unsafe model artifact member: {member.name}") from exc
            if member.issym() or member.islnk():
                raise ValueError(f"links are forbidden in model artifact: {member.name}")
        archive.extractall(destination)


def verify_bundle(
    bundle: Path,
    *,
    config: dict[str, Any],
    cell: dict[str, Any],
    launch: dict[str, Any],
) -> dict[str, Any]:
    missing = [name for name in FILES if not (bundle / name).is_file()]
    extra = sorted(
        path.name for path in bundle.iterdir() if path.is_file() and path.name not in FILES
    )
    if missing or extra:
        raise ValueError(f"model bundle file set mismatch: missing={missing}, extra={extra}")
    evidence = read_json(bundle / "cloud_job_evidence.json")
    if (
        evidence.get("status") != "PASS"
        or evidence.get("confirmatory_evidence") is not False
        or evidence.get("cell_id") != cell["cell_id"]
        or evidence.get("job_name") != launch["job_name"]
        or evidence.get("git_commit") != launch["git_commit"]
        or evidence.get("experiment_id") != config["experiment_id"]
    ):
        raise ValueError("cloud evidence identity/status mismatch")
    summary = read_json(bundle / "collection_summary.json")
    selected = read_jsonl(bundle / "selected_rows.jsonl")
    traces = read_jsonl(bundle / "reasoning_traces.jsonl")
    raw = read_jsonl(bundle / "raw_generations.jsonl")
    n = int(config["generation"]["pilot_n"])
    rounds = int(config["generation"]["rounds"])
    if len(selected) != n or len(traces) != n or len(raw) != n * rounds:
        raise ValueError("downloaded development collection cardinality mismatch")
    selected_ids = [str(row["question_id"]) for row in selected]
    if len(set(selected_ids)) != n:
        raise ValueError("downloaded selected IDs are duplicated")
    if {str(row["question_id"]) for row in traces} != set(selected_ids):
        raise ValueError("trace IDs differ from selected IDs")
    if {str(row["question_id"]) for row in raw} != set(selected_ids):
        raise ValueError("raw generation IDs differ from selected IDs")
    evidence_files = evidence.get("collection_verification", {}).get("files", {})
    for name in FILES[:-1]:
        expected = evidence_files.get(name, {}).get("sha256")
        if expected != sha256_file(bundle / name):
            raise ValueError(f"cloud evidence SHA-256 mismatch for {name}")
    if summary.get("claim_boundary") != config["claim_boundary"]:
        raise ValueError("collection summary lost the development-only claim boundary")
    return {
        "status": "PASS",
        "cell_id": cell["cell_id"],
        "job_name": launch["job_name"],
        "git_commit": launch["git_commit"],
        "rows": n,
        "generations": n * rounds,
        "files": {name: sha256_file(bundle / name) for name in FILES},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    parser.add_argument("--cell", required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if config_path.resolve() != DEFAULT_CONFIG.resolve():
        raise ValueError("fetch requires the committed default development config")
    config = read_json(config_path)
    matches = [cell for cell in config["cells"] if cell["cell_id"] == args.cell]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate cell: {args.cell}")
    cell = matches[0]
    launch_path = (
        ROOT
        / "manifests/px057_h5_development_pilot_20260727/launches"
        / f"{cell['cell_id']}.json"
    )
    launch = read_json(launch_path)
    aws_config = config["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    described = json.loads(
        aws(
            profile,
            region,
            "sagemaker",
            "describe-training-job",
            "--training-job-name",
            launch["job_name"],
            "--output",
            "json",
        )
    )
    if described.get("TrainingJobStatus") != "Completed":
        reason = described.get("FailureReason")
        raise ValueError(
            f"development job is {described.get('TrainingJobStatus')}: {reason}"
        )
    artifact_uri = described.get("ModelArtifacts", {}).get("S3ModelArtifacts", "")
    if not artifact_uri:
        raise ValueError("completed training job has no model artifact URI")
    output_dir = ROOT / cell["output_dir"]
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"local development output is immutable: {output_dir}")

    with tempfile.TemporaryDirectory(prefix="px057-h5-dev-fetch-") as temp:
        temp_path = Path(temp)
        archive_path = temp_path / "model.tar.gz"
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                artifact_uri,
                str(archive_path),
                "--profile",
                profile,
                "--region",
                region,
                "--only-show-errors",
            ],
            cwd=ROOT,
            check=True,
        )
        extracted = temp_path / "extracted"
        extracted.mkdir()
        safe_extract(archive_path, extracted)
        bundle = extracted / "px057_h5_development_pilot" / cell["cell_id"]
        if not bundle.is_dir():
            raise ValueError(f"model artifact lacks expected bundle: {bundle}")
        verification = verify_bundle(
            bundle,
            config=config,
            cell=cell,
            launch=launch,
        )
        output_dir.mkdir(parents=True, exist_ok=False)
        for name in FILES:
            shutil.copy2(bundle / name, output_dir / name)
    receipt = {
        **verification,
        "confirmatory_evidence": False,
        "claim_boundary": config["claim_boundary"],
        "model_artifact_uri": artifact_uri,
    }
    receipt_path = output_dir / "fetch_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
