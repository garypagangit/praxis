#!/usr/bin/env python
"""Collect one PX-057 H4 holdout cell from an exact frozen Git commit."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


STAGED_ROOT = Path(__file__).resolve().parents[2]
if str(STAGED_ROOT) not in sys.path:
    sys.path.insert(0, str(STAGED_ROOT))

from cloud_jobs.px057_h4_calibration_20260725.sagemaker_entry import (  # noqa: E402
    clone_exact_branch_history,
    put_file,
)
from cloud_jobs.px057_h4_phase_a_20260725.sagemaker_entry import (  # noqa: E402
    canonical_json_bytes,
    install_locked_dependencies,
    output,
    parse_s3_uri,
    read_huggingface_token,
    required_env,
    run,
    sha256_file,
)


ENTRY = "cloud_jobs/px057_h4_holdout_20260727/sagemaker_entry.py"
CALIBRATION_ENTRY = (
    "cloud_jobs/px057_h4_calibration_20260725/sagemaker_entry.py"
)
PHASE_A_ENTRY = "cloud_jobs/px057_h4_phase_a_20260725/sagemaker_entry.py"
TRANSPORT_CONFIG = "configs/px057_h4_holdout_transport_20260727.json"
FREEZE_MANIFEST = "manifests/px057_h4_20260725/holdout_transport_freeze.json"
SCIENCE_CONFIG = "configs/px057_h4_ltt_transfer_20260725.json"
COLLECTION_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)


def read_json(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, nested in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = nested
        return result

    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def artifact_records(value: Any) -> Iterator[dict[str, Any]]:
    """Yield every explicit path/SHA-256 binding in a frozen JSON object."""

    if isinstance(value, dict):
        if isinstance(value.get("path"), str) and isinstance(
            value.get("sha256"), str
        ):
            yield value
        for key, path in value.items():
            if not key.endswith("_path") or not isinstance(path, str):
                continue
            digest = value.get(f"{key[:-5]}_sha256")
            if isinstance(digest, str):
                yield {"path": path, "sha256": digest}
        for nested in value.values():
            yield from artifact_records(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from artifact_records(nested)


def verified_frozen_artifacts(
    repo: Path,
    payload: Any,
    *,
    committed_file_info: Any,
) -> dict[str, dict[str, str]]:
    """Verify all static file bindings and reject duplicate-path ambiguity."""

    verified: dict[str, dict[str, str]] = {}
    for record in artifact_records(payload):
        relative = str(record["path"])
        expected_sha256 = str(record["sha256"])
        if Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValueError(f"frozen artifact path is not repository-relative: {relative}")
        if len(expected_sha256) != 64:
            raise ValueError(f"invalid frozen SHA-256 for {relative}")
        path = repo / relative
        observed_sha256 = sha256_file(path)
        if observed_sha256 != expected_sha256:
            raise ValueError(
                f"frozen artifact hash mismatch for {relative}: "
                f"{observed_sha256} != {expected_sha256}"
            )
        if record.get("bytes") is not None and path.stat().st_size != int(
            record["bytes"]
        ):
            raise ValueError(f"frozen artifact byte length changed for {relative}")
        commit = committed_file_info(repo, path)
        evidence = {
            "path": relative,
            "sha256": observed_sha256,
            "last_change_commit": str(commit["last_change_commit"]),
            "verified_at_head": str(commit["verified_at_head"]),
        }
        previous = verified.get(relative)
        if previous is not None and previous != evidence:
            raise ValueError(f"conflicting frozen bindings for {relative}")
        recorded_commit = record.get("last_change_commit")
        if recorded_commit is not None and recorded_commit != evidence["last_change_commit"]:
            raise ValueError(f"frozen artifact commit changed for {relative}")
        verified[relative] = evidence
    return verified


def get_cell(cells: Any, cell_id: str) -> dict[str, Any]:
    if isinstance(cells, dict):
        cell = cells.get(cell_id)
        if not isinstance(cell, dict):
            raise ValueError(f"unknown PX-057 H4 holdout cell: {cell_id}")
        return {"cell_id": cell_id, **cell}
    if not isinstance(cells, list):
        raise ValueError("holdout transport cells must be an object or list")
    matching = [cell for cell in cells if cell.get("cell_id") == cell_id]
    if len(matching) != 1:
        raise ValueError(f"unknown or duplicate PX-057 H4 holdout cell: {cell_id}")
    return matching[0]


def verify_artifacts_at_freeze_base(
    repo: Path,
    records: dict[str, dict[str, Any]],
    *,
    freeze_base_commit: str,
) -> None:
    """Prove every protected byte was present at the claimed freeze commit."""

    for relative, record in records.items():
        last_change_commit = str(record["last_change_commit"])
        if (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    last_change_commit,
                    freeze_base_commit,
                ],
                cwd=repo,
                check=False,
            ).returncode
            != 0
        ):
            raise ValueError(f"artifact postdates transport freeze: {relative}")
        try:
            body = subprocess.check_output(
                ["git", "show", f"{freeze_base_commit}:{relative}"], cwd=repo
            )
            blob = output(
                ["git", "rev-parse", f"{freeze_base_commit}:{relative}"], cwd=repo
            )
        except subprocess.CalledProcessError as exc:
            raise ValueError(
                f"artifact did not exist at transport freeze: {relative}"
            ) from exc
        if (
            hashlib.sha256(body).hexdigest() != record["sha256"]
            or len(body) != int(record["bytes"])
            or blob != record["git_blob"]
        ):
            raise ValueError(f"artifact bytes differ at transport freeze: {relative}")


def relative_value(record: dict[str, Any], *names: str) -> str:
    for name in names:
        value = record.get(name)
        if isinstance(value, str) and value:
            return value
    raise ValueError(f"missing required path field; expected one of {names}")


def require_equal(observed: Any, expected: Any, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} differs from the frozen holdout transport")


def main() -> None:
    repository_url = required_env("PX057_H4_REPOSITORY_URL")
    branch = required_env("PX057_H4_BRANCH")
    expected_commit = required_env("PX057_H4_GIT_COMMIT")
    container_digest = required_env("PX057_CONTAINER_IMAGE_DIGEST")
    secret_id = required_env("PX057_H4_HF_SECRET_ID")
    result_uri = required_env("PX057_H4_RESULT_S3_URI")
    region = required_env("AWS_REGION")
    job_name = required_env("PX057_H4_JOB_NAME")
    source_version_id = required_env("PX057_H4_SOURCE_VERSION_ID")
    source_sha256 = required_env("PX057_H4_SOURCE_SHA256")
    source_bucket = required_env("PX057_H4_SOURCE_BUCKET")
    source_key = required_env("PX057_H4_SOURCE_KEY")
    cell_id = required_env("PX057_H4_CELL_ID")
    transport_id = required_env("PX057_H4_TRANSPORT_ID")
    science_config_sha256 = required_env("PX057_H4_SCIENCE_CONFIG_SHA256")
    transport_config_sha256 = required_env("PX057_H4_TRANSPORT_CONFIG_SHA256")
    freeze_sha256 = required_env("PX057_H4_FREEZE_SHA256")
    lock_sha256 = required_env("PX057_H4_LOCK_SHA256")
    selected_policy_sha256 = required_env("PX057_H4_SELECTED_POLICY_SHA256")

    staged_archive = Path("/tmp/s")
    if not staged_archive.is_file() or sha256_file(staged_archive) != source_sha256:
        raise ValueError("staged holdout source differs from the submitted SHA-256")

    started = datetime.now(timezone.utc).isoformat()
    repo = Path("/opt/ml/code/px057_h4_repo")
    observed_branch_head = clone_exact_branch_history(
        repository_url, branch, expected_commit, repo
    )

    committed_entry = repo / ENTRY
    committed_calibration_entry = repo / CALIBRATION_ENTRY
    committed_phase_a_entry = repo / PHASE_A_ENTRY
    if sha256_file(Path(__file__).resolve()) != sha256_file(committed_entry):
        raise ValueError("staged holdout entry differs from the committed entry")
    if sha256_file(STAGED_ROOT / CALIBRATION_ENTRY) != sha256_file(
        committed_calibration_entry
    ):
        raise ValueError("staged calibration helper differs from the committed helper")
    if sha256_file(STAGED_ROOT / PHASE_A_ENTRY) != sha256_file(
        committed_phase_a_entry
    ):
        raise ValueError("staged Phase A helper differs from the committed helper")

    transport_path = repo / TRANSPORT_CONFIG
    freeze_path = repo / FREEZE_MANIFEST
    science_path = repo / SCIENCE_CONFIG
    require_equal(sha256_file(transport_path), transport_config_sha256, "transport config")
    require_equal(sha256_file(freeze_path), freeze_sha256, "transport freeze")
    require_equal(sha256_file(science_path), science_config_sha256, "science config")
    transport = read_json(transport_path)
    freeze = read_json(freeze_path)
    science = read_json(science_path)

    if str(transport.get("transport_id", "")) != transport_id:
        raise ValueError("transport ID differs from the submitted registration")
    require_equal(
        transport.get("experiment_id"),
        science.get("experiment_id"),
        "experiment identity",
    )
    if freeze.get("status") != "PASS":
        raise ValueError("holdout transport freeze did not pass")
    if freeze.get("scientific_data_generated") not in (None, False):
        raise ValueError("holdout transport freeze was not pre-outcome")
    require_equal(freeze.get("transport_id"), transport_id, "transport freeze ID")
    require_equal(
        freeze.get("experiment_id"),
        science.get("experiment_id"),
        "transport freeze experiment",
    )

    repository = transport.get("repository", {})
    require_equal(repository.get("url"), repository_url, "repository URL")
    require_equal(repository.get("branch"), branch, "repository branch")
    aws = transport.get("aws", {})
    require_equal(aws.get("region"), region, "AWS region")
    require_equal(aws.get("container_digest"), container_digest, "container image digest")
    require_equal(aws.get("huggingface_secret_id"), secret_id, "Hugging Face secret")
    require_equal(aws.get("bucket"), source_bucket, "source S3 bucket")
    source = transport.get("source", {})
    if source.get("bootstrap") != "explicit_s3_version_and_sha256_before_extraction":
        raise ValueError("holdout source bootstrap is not the frozen pre-extraction gate")
    require_equal(source.get("entrypoint"), ENTRY, "holdout entrypoint")
    require_equal(
        source.get("calibration_entrypoint"),
        CALIBRATION_ENTRY,
        "calibration helper entrypoint",
    )
    require_equal(
        source.get("phase_a_entrypoint"),
        PHASE_A_ENTRY,
        "Phase A helper entrypoint",
    )
    require_equal(source.get("freeze_manifest"), FREEZE_MANIFEST, "freeze manifest path")
    archive_members = set(source.get("archive_members", ()))
    required_archive_members = {ENTRY, CALIBRATION_ENTRY, PHASE_A_ENTRY}
    if not required_archive_members.issubset(archive_members):
        raise ValueError("holdout source archive omits a bootstrap entry dependency")
    collection = transport.get("collection", {})
    if (
        collection.get("split") != "holdout"
        or int(collection.get("expected_traces", -1)) != 300
        or int(collection.get("expected_generations", -1)) != 2400
        or int(collection.get("rounds", -1)) != 8
        or tuple(collection.get("files", ())) != COLLECTION_FILES
        or int(aws.get("max_runtime_seconds", -1)) != 86400
        or transport.get("rules", {}).get("first_attempt_only") is not True
        or transport.get("rules", {}).get("no_retry")
        != "No retry or replacement job is allowed under this transport ID."
    ):
        raise ValueError("holdout collection contract differs from the frozen transport")

    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from scripts.px057_h4_common import (  # noqa: E402
        committed_file_info,
        verify_collection_bundle,
    )
    from scripts.freeze_px057_h4_holdout_transport import (  # noqa: E402
        validate_freeze_manifest,
    )
    from scripts.run_px057_h4_holdout_gate import verify_all_locks  # noqa: E402

    validate_freeze_manifest(transport, freeze, repo_root=repo)
    freeze_base_commit = str(freeze["freeze_base_commit"])
    freeze_commit = committed_file_info(repo, freeze_path)["last_change_commit"]
    for ancestor, descendant, label in (
        (
            freeze_base_commit,
            freeze_commit,
            "holdout freeze base does not precede its manifest commit",
        ),
        (
            freeze_commit,
            expected_commit,
            "holdout freeze manifest commit does not precede launch",
        ),
    ):
        if (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant],
                cwd=repo,
                check=False,
            ).returncode
            != 0
        ):
            raise ValueError(label)

    frozen_artifacts = verified_frozen_artifacts(
        repo,
        transport,
        committed_file_info=committed_file_info,
    )
    freeze_artifacts = verified_frozen_artifacts(
        repo,
        freeze,
        committed_file_info=committed_file_info,
    )
    verify_artifacts_at_freeze_base(
        repo,
        freeze["protected_artifacts"],
        freeze_base_commit=freeze_base_commit,
    )
    required_static_paths = {
        SCIENCE_CONFIG,
        "requirements-px057-h4.txt",
        "manifests/px057_h4_20260725/phase_a_freeze_v2.json",
        "scripts/px057_h4_common.py",
        "scripts/run_px057_h4_trace_collection.py",
        "scripts/run_px057_h4_holdout_gate.py",
    }
    missing_bindings = sorted(required_static_paths - set(frozen_artifacts))
    if missing_bindings:
        raise ValueError(
            f"holdout transport omits required scientific bindings: {missing_bindings}"
        )
    required_freeze_paths = {
        TRANSPORT_CONFIG,
        SCIENCE_CONFIG,
        ENTRY,
        CALIBRATION_ENTRY,
        PHASE_A_ENTRY,
    } | archive_members
    missing_freeze_paths = sorted(required_freeze_paths - set(freeze_artifacts))
    if missing_freeze_paths:
        raise ValueError(
            f"holdout freeze omits required transport bindings: {missing_freeze_paths}"
        )
    frozen_science = transport.get("frozen_science", {})
    require_equal(frozen_science.get("config_path"), SCIENCE_CONFIG, "science config path")
    require_equal(
        frozen_science.get("config_sha256"),
        science_config_sha256,
        "science config binding",
    )
    calibration_commit = str(
        frozen_science.get("calibration_evidence_commit", "")
    )
    if not calibration_commit or len(calibration_commit) != 40:
        raise ValueError("calibration evidence commit is missing from the transport")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", calibration_commit, expected_commit],
            cwd=repo,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("calibration evidence commit is not an ancestor of the launch")

    transport_cell = get_cell(transport.get("cells"), cell_id)
    science_cell = get_cell(science.get("cells"), cell_id)
    holdout_manifest = relative_value(
        transport_cell, "holdout_manifest", "holdout_manifest_path"
    )
    output_dir_relative = relative_value(
        transport_cell, "output_dir", "holdout_output_dir"
    )
    lock_relative = relative_value(
        transport_cell, "ltt_lock_manifest", "ltt_lock_path"
    )
    determination_relative = relative_value(
        transport_cell, "ltt_determination", "ltt_determination_path"
    )
    require_equal(
        holdout_manifest,
        science_cell["holdout_manifest"],
        f"{cell_id} holdout manifest",
    )
    require_equal(
        output_dir_relative,
        science_cell["output_dirs"]["holdout"],
        f"{cell_id} output directory",
    )
    require_equal(
        lock_relative,
        science_cell["ltt_lock_manifest"],
        f"{cell_id} LTT lock path",
    )
    require_equal(
        determination_relative,
        science_cell["ltt_determination"],
        f"{cell_id} LTT determination path",
    )
    expected_holdout_sha = transport_cell.get("holdout_manifest_sha256")
    if expected_holdout_sha is not None:
        require_equal(
            sha256_file(repo / holdout_manifest),
            expected_holdout_sha,
            f"{cell_id} holdout manifest hash",
        )

    all_lock_evidence = verify_all_locks(science, science_path)
    if set(all_lock_evidence) != {
        str(cell["cell_id"]) for cell in science["cells"]
    }:
        raise ValueError("the complete three-cell LTT lock set was not verified")
    target_lock_path = repo / lock_relative
    target_determination_path = repo / determination_relative
    require_equal(sha256_file(target_lock_path), lock_sha256, "target LTT lock")
    target_lock = read_json(target_lock_path)
    if target_lock.get("cell_id") != cell_id:
        raise ValueError("target LTT lock cell differs from the submitted cell")
    if target_lock.get("selected_policy") is None:
        raise ValueError(f"{cell_id}: null selected policy forbids holdout generation")
    observed_policy_sha256 = hashlib.sha256(
        canonical_json_bytes(target_lock["selected_policy"])
    ).hexdigest()
    require_equal(
        observed_policy_sha256,
        selected_policy_sha256,
        "target selected-policy hash",
    )
    require_equal(
        sha256_file(target_determination_path),
        target_lock["determination_sha256"],
        "target LTT determination",
    )

    install_locked_dependencies(repo)
    token = read_huggingface_token(secret_id, region)
    os.environ["HF_TOKEN"] = token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = token
    os.environ["PX057_CONTAINER_IMAGE_DIGEST"] = container_digest
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    output_dir = repo / output_dir_relative
    if output_dir.exists():
        raise FileExistsError(
            f"holdout output already exists in clean clone: {output_dir}"
        )
    run(
        [
            sys.executable,
            "scripts/run_px057_h4_trace_collection.py",
            "--config",
            SCIENCE_CONFIG,
            "--cell",
            cell_id,
            "--split",
            "holdout",
        ],
        cwd=repo,
    )

    verification = verify_collection_bundle(
        output_dir,
        repo / science_cell["holdout_manifest"],
        expected_cell_id=cell_id,
        expected_split="holdout",
        expected_n=300,
        expected_rounds=8,
        expected_model=science["models"][science_cell["model_key"]],
        expected_prompt_id=science["generation"]["prompt_template_id"],
        expected_prompt_sha256=science["generation"]["prompt_template_sha256"],
    )
    if (
        verification["trace_count"] != 300
        or verification["raw_generation_count"] != 2400
    ):
        raise ValueError("holdout bundle failed the frozen 300/2400 cardinality gate")

    import boto3

    bucket, prefix = parse_s3_uri(result_uri)
    expected_bucket = aws.get("bucket")
    if expected_bucket is not None:
        require_equal(bucket, expected_bucket, "result S3 bucket")
    expected_prefix = transport_cell.get("result_prefix")
    if isinstance(expected_prefix, str) and expected_prefix:
        require_equal(prefix, expected_prefix.strip("/"), "result S3 prefix")
    require_equal(transport_cell.get("job_name"), job_name, "holdout job name")

    client = boto3.client("s3", region_name=region)
    receipts: dict[str, dict[str, Any]] = {}
    for name in COLLECTION_FILES:
        receipts[name] = put_file(
            client,
            bucket=bucket,
            key=f"{prefix}/{name}",
            path=output_dir / name,
            git_commit=expected_commit,
        )

    summary = read_json(output_dir / "collection_summary.json")
    target_lock_commit = committed_file_info(repo, target_lock_path)
    target_determination_commit = committed_file_info(
        repo, target_determination_path
    )
    evidence = {
        "experiment_id": science["experiment_id"],
        "transport_id": transport_id,
        "stage": "PX057_H4_holdout_cloud_collection",
        "status": "PASS",
        "scientific_data_generated": True,
        "split": "holdout",
        "cell_id": cell_id,
        "job_name": job_name,
        "repository_url": repository_url,
        "branch": branch,
        "git_commit": expected_commit,
        "observed_remote_branch_head": observed_branch_head,
        "container_image_digest": container_digest,
        "entrypoint_sha256": sha256_file(committed_entry),
        "calibration_helper_sha256": sha256_file(committed_calibration_entry),
        "phase_a_helper_sha256": sha256_file(committed_phase_a_entry),
        "transport_config": {
            "path": TRANSPORT_CONFIG,
            "sha256": transport_config_sha256,
        },
        "transport_freeze": {
            "path": FREEZE_MANIFEST,
            "sha256": freeze_sha256,
            "status": freeze.get("status"),
        },
        "science_config": {
            "path": SCIENCE_CONFIG,
            "sha256": science_config_sha256,
        },
        "source_version_id": source_version_id,
        "source_sha256": source_sha256,
        "source_bucket": source_bucket,
        "source_key": source_key,
        "frozen_scientific_artifacts": frozen_artifacts,
        "frozen_transport_artifacts": freeze_artifacts,
        "all_ltt_lock_evidence": all_lock_evidence,
        "target_ltt_binding": {
            "lock_path": lock_relative,
            "lock_sha256": lock_sha256,
            "lock_commit": target_lock_commit,
            "determination_path": determination_relative,
            "determination_sha256": target_lock["determination_sha256"],
            "determination_commit": target_determination_commit,
            "selected_policy_sha256": selected_policy_sha256,
        },
        "phase_a_evidence": summary["phase_a_evidence"],
        "collection_verification": verification,
        "collection_objects": receipts,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    evidence_bytes = canonical_json_bytes(evidence)
    model_dir = Path(os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    evidence_path = model_dir / "cloud_job_evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_bytes(evidence_bytes)
    evidence_receipt = put_file(
        client,
        bucket=bucket,
        key=f"{prefix}/cloud_job_evidence.json",
        path=evidence_path,
        git_commit=expected_commit,
    )

    bundle_target = model_dir / "px057_h4_holdout" / cell_id
    bundle_target.mkdir(parents=True, exist_ok=False)
    for name in COLLECTION_FILES:
        shutil.copy2(output_dir / name, bundle_target / name)
    shutil.copy2(evidence_path, bundle_target / evidence_path.name)
    print(
        json.dumps(
            {
                "status": "PASS",
                "job_name": job_name,
                "cell_id": cell_id,
                "evidence_version_id": evidence_receipt["version_id"],
                "collection_version_ids": {
                    name: receipt["version_id"]
                    for name, receipt in receipts.items()
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
