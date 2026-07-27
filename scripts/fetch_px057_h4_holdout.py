#!/usr/bin/env python
"""Fetch, verify, and atomically install one PX-057 H4 holdout bundle."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_px057_h4_phase_a import download_versioned, parse_s3_uri
from scripts.px057_h4_common import (
    committed_file_info,
    read_json,
    sha256_file,
    verify_collection_bundle,
    verify_phase_a_freeze,
    write_json,
)
from scripts.submit_px057_h4_holdout import (
    CALIBRATION_ENTRY,
    CELL_JOB_CODES,
    COLLECTION_FILES,
    DEFAULT_TRANSPORT_CONFIG,
    ENTRY,
    HOLDOUT_MAX_RUNTIME_SECONDS,
    PHASE_A_ENTRY,
    canonical_json_sha256,
    committed_and_pushed,
    expected_environment,
    freeze_manifest_path,
    holdout_job_name,
    repo_path,
    read_json_strict,
    science_config_path,
    source_launch_command,
    training_request,
    transport_cell,
    verify_git,
    verify_ltt_locks,
    verify_no_downstream_evidence,
    verify_transport_config,
    verify_transport_freeze,
)


def aws_json(profile: str, region: str, *args: str) -> dict[str, Any]:
    raw = subprocess.check_output(
        ["aws", *args, "--profile", profile, "--region", region, "--output", "json"],
        cwd=ROOT,
        text=True,
    ).strip()
    return json.loads(raw) if raw else {}


def artifact_records(value: Any) -> Iterator[dict[str, Any]]:
    """Yield explicit path/SHA-256 bindings exactly as the cloud entrypoint does."""

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


def require_single_version(
    *, profile: str, region: str, bucket: str, key: str
) -> str:
    listing = aws_json(
        profile,
        region,
        "s3api",
        "list-object-versions",
        "--bucket",
        bucket,
        "--prefix",
        key,
    )
    versions = [row for row in listing.get("Versions", []) if row.get("Key") == key]
    deletes = [
        row for row in listing.get("DeleteMarkers", []) if row.get("Key") == key
    ]
    if len(versions) != 1 or deletes or versions[0].get("IsLatest") is not True:
        raise ValueError(
            f"s3://{bucket}/{key}: expected one latest immutable version and no delete marker"
        )
    return str(versions[0]["VersionId"])


def download_single_version(
    *, profile: str, region: str, uri: str, destination: Path
) -> dict[str, Any]:
    bucket, key = parse_s3_uri(uri)
    version_id = require_single_version(
        profile=profile, region=region, bucket=bucket, key=key
    )
    return download_versioned(
        profile=profile,
        region=region,
        uri=uri,
        destination=destination,
        expected_version_id=version_id,
    )


def _assert_capture_ancestry(capture_commit: str) -> None:
    if (
        len(capture_commit) != 40
        or subprocess.run(
            ["git", "merge-base", "--is-ancestor", capture_commit, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("holdout cloud commit is not an ancestor of current HEAD")


def verify_execution_strategy(
    description: dict[str, Any], transport: dict[str, Any]
) -> None:
    """Require AWS's null retry strategy and explicitly disabled managed spot."""

    aws_config = transport["aws"]
    if (
        aws_config.get("retry_strategy_omitted") is not True
        or (
            "RetryStrategy" in description
            and description["RetryStrategy"] is not None
        )
        or description.get("EnableManagedSpotTraining")
        is not aws_config.get("enable_managed_spot_training")
    ):
        raise ValueError("holdout retry or managed-spot strategy differs from freeze")


def verify_job_request(
    description: dict[str, Any],
    transport: dict[str, Any],
    science: dict[str, Any],
    *,
    cell_id: str,
    transport_path: Path,
    freeze_sha256: str,
    lock: dict[str, Any],
) -> tuple[str, str, str, dict[str, Any]]:
    """Reconstruct the exact registered request from committed local evidence."""

    aws_config = transport["aws"]
    verify_execution_strategy(description, transport)
    environment = description.get("Environment", {})
    capture_commit = str(environment.get("PX057_H4_GIT_COMMIT", ""))
    _assert_capture_ancestry(capture_commit)
    job_name = transport_cell(transport, cell_id)["job_name"]
    if job_name != holdout_job_name(cell_id):
        raise ValueError("configured holdout job name is not the frozen first attempt")
    prefix = aws_config["s3_prefix"].strip("/")
    code_key = f"{prefix}/code/{job_name}/source.tar.gz"
    code_uri = f"s3://{aws_config['bucket']}/{code_key}"
    output_uri = f"s3://{aws_config['bucket']}/{prefix}/sagemaker-output"
    science_path = science_config_path(transport)
    science_cells = {cell["cell_id"]: cell for cell in science["cells"]}
    lock_path = repo_path(science_cells[cell_id]["ltt_lock_manifest"])
    selected_policy_sha256 = canonical_json_sha256(lock["selected_policy"])
    local_hashes = {
        "transport": sha256_file(transport_path),
        "science": sha256_file(science_path),
        "freeze": freeze_sha256,
        "lock": sha256_file(lock_path),
        "policy": selected_policy_sha256,
    }
    submitted_hashes = {
        "transport": environment.get("PX057_H4_TRANSPORT_CONFIG_SHA256"),
        "science": environment.get("PX057_H4_SCIENCE_CONFIG_SHA256"),
        "freeze": environment.get("PX057_H4_FREEZE_SHA256"),
        "lock": environment.get("PX057_H4_LOCK_SHA256"),
        "policy": environment.get("PX057_H4_SELECTED_POLICY_SHA256"),
    }
    if submitted_hashes != local_hashes:
        raise ValueError("holdout request hashes differ from committed frozen evidence")
    source_version_id = str(environment.get("PX057_H4_SOURCE_VERSION_ID", ""))
    source_sha256 = str(environment.get("PX057_H4_SOURCE_SHA256", ""))
    if not source_version_id or len(source_sha256) != 64:
        raise ValueError("holdout request has no immutable source identity")
    request = training_request(
        transport,
        cell_id=cell_id,
        git_commit=capture_commit,
        code_uri=code_uri,
        code_version_id=source_version_id,
        code_sha256=source_sha256,
        transport_sha256=local_hashes["transport"],
        science_sha256=local_hashes["science"],
        freeze_sha256=local_hashes["freeze"],
        lock_sha256=local_hashes["lock"],
        selected_policy_sha256=local_hashes["policy"],
    )
    algorithm = description["AlgorithmSpecification"]
    resource = description["ResourceConfig"]
    input_config = description.get("InputDataConfig", [])
    if len(input_config) != 1:
        raise ValueError("holdout request has an unexpected input-channel count")
    source_data = input_config[0]["DataSource"]["S3DataSource"]
    expected_input = request["InputDataConfig"][0]
    if (
        description.get("TrainingJobName") != job_name
        or description.get("RoleArn") != request["RoleArn"]
        or algorithm.get("TrainingImage")
        != request["AlgorithmSpecification"]["TrainingImage"]
        or algorithm.get("TrainingInputMode") != "File"
        or algorithm.get("ContainerEntrypoint") != ["bash", "-lc"]
        or algorithm.get("ContainerArguments") != [source_launch_command()]
        or environment
        != expected_environment(
            transport,
            cell_id=cell_id,
            git_commit=capture_commit,
            code_key=code_key,
            code_version_id=source_version_id,
            code_sha256=source_sha256,
            transport_sha256=local_hashes["transport"],
            science_sha256=local_hashes["science"],
            freeze_sha256=local_hashes["freeze"],
            lock_sha256=local_hashes["lock"],
            selected_policy_sha256=local_hashes["policy"],
        )
        or description.get("EnableNetworkIsolation") is not False
        or input_config[0].get("ChannelName") != expected_input["ChannelName"]
        or input_config[0].get("InputMode") != expected_input["InputMode"]
        or source_data != expected_input["DataSource"]["S3DataSource"]
        or description.get("OutputDataConfig", {}).get("S3OutputPath") != output_uri
        or resource.get("InstanceType") != aws_config["instance_type"]
        or int(resource.get("InstanceCount", -1)) != 1
        or int(resource.get("VolumeSizeInGB", -1))
        != int(aws_config["volume_size_gb"])
        or int(description.get("StoppingCondition", {}).get("MaxRuntimeInSeconds", -1))
        != HOLDOUT_MAX_RUNTIME_SECONDS
    ):
        raise ValueError("holdout cloud request differs from the frozen launcher")
    return capture_commit, code_uri, output_uri, request


def verify_tags(
    tags_response: dict[str, Any],
    *,
    transport: dict[str, Any],
    cell_id: str,
    capture_commit: str,
) -> dict[str, str]:
    tags = {row["Key"]: row["Value"] for row in tags_response.get("Tags", [])}
    expected = {
        "Project": "PraxisResearch",
        "PraxisId": "PX-057",
        "Gate": "H4-Holdout",
        "Cell": cell_id,
        "GitCommit": capture_commit,
        "TransportId": transport["transport_id"],
    }
    if tags != expected:
        raise ValueError("holdout cloud job tags differ from the frozen launcher")
    return tags


def verify_launch_registration(
    transport: dict[str, Any],
    *,
    cell_id: str,
    description: dict[str, Any],
    request: dict[str, Any],
) -> dict[str, Any]:
    path = repo_path(transport_cell(transport, cell_id)["launch_manifest"])
    committed = committed_and_pushed(path)
    launch = read_json_strict(path)
    environment = request["Environment"]
    source = launch.get("source_object", {})
    if (
        launch.get("transport_id") != transport["transport_id"]
        or launch.get("experiment_id") != transport["experiment_id"]
        or launch.get("stage") != "H4_holdout_launch_registration"
        or launch.get("status") != "REGISTERED_PRE_RESULT"
        or launch.get("scientific_result_observed") is not False
        or launch.get("cell_id") != cell_id
        or launch.get("job_name") != description["TrainingJobName"]
        or launch.get("training_job_arn") != description["TrainingJobArn"]
        or launch.get("git_commit") != environment["PX057_H4_GIT_COMMIT"]
        or launch.get("container_image")
        != request["AlgorithmSpecification"]["TrainingImage"]
        or launch.get("code_uri")
        != request["InputDataConfig"][0]["DataSource"]["S3DataSource"]["S3Uri"]
        or launch.get("code_version_id")
        != environment["PX057_H4_SOURCE_VERSION_ID"]
        or launch.get("code_sha256") != environment["PX057_H4_SOURCE_SHA256"]
        or source.get("version_id") != environment["PX057_H4_SOURCE_VERSION_ID"]
        or source.get("sha256") != environment["PX057_H4_SOURCE_SHA256"]
        or source.get("server_side_encryption") != "AES256"
        or launch.get("result_uri") != environment["PX057_H4_RESULT_S3_URI"]
        or int(launch.get("max_runtime_seconds", -1))
        != HOLDOUT_MAX_RUNTIME_SECONDS
        or launch.get("retry_strategy_omitted") is not True
        or launch.get("managed_spot_training") is not False
        or launch.get("transport_config_sha256")
        != environment["PX057_H4_TRANSPORT_CONFIG_SHA256"]
        or launch.get("science_config_sha256")
        != environment["PX057_H4_SCIENCE_CONFIG_SHA256"]
        or launch.get("transport_freeze_sha256")
        != environment["PX057_H4_FREEZE_SHA256"]
        or launch.get("ltt_lock_sha256") != environment["PX057_H4_LOCK_SHA256"]
        or launch.get("selected_policy_sha256")
        != environment["PX057_H4_SELECTED_POLICY_SHA256"]
        or launch.get("request_sha256") != canonical_json_sha256(request)
    ):
        raise ValueError("cloud job differs from its pushed pre-result registration")
    capture_commit = environment["PX057_H4_GIT_COMMIT"]
    if (
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                capture_commit,
                committed["last_change_commit"],
            ],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("launch registration does not descend from the cloud commit")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        "commit": committed,
        "registration": launch,
    }


def verify_source_archive(
    source_path: Path,
    *,
    transport: dict[str, Any],
    capture_commit: str,
    expected_sha256: str,
) -> dict[str, str]:
    if sha256_file(source_path) != expected_sha256:
        raise ValueError("downloaded holdout source differs from the request hash")
    expected_members = set(transport["source"]["archive_members"])
    observed: dict[str, str] = {}
    with tarfile.open(source_path, "r:gz") as handle:
        files = [member for member in handle.getmembers() if member.isfile()]
        if (
            {member.name for member in files} != expected_members
            or len(files) != len(expected_members)
        ):
            raise ValueError("holdout source archive has unexpected members")
        if any(not member.isfile() for member in handle.getmembers()):
            raise ValueError("holdout source archive contains non-file members")
        for member in files:
            extracted = handle.extractfile(member)
            if extracted is None:
                raise ValueError("holdout source archive contains an unreadable member")
            body = extracted.read()
            expected = subprocess.check_output(
                ["git", "show", f"{capture_commit}:{member.name}"], cwd=ROOT
            )
            if body != expected:
                raise ValueError(f"source member differs from cloud commit: {member.name}")
            observed[member.name] = hashlib.sha256(body).hexdigest()
    return observed


def verify_runtime_summary(
    summary: dict[str, Any], science: dict[str, Any], cell: dict[str, Any]
) -> None:
    frozen = read_json(repo_path(science["phase_a"]["runtime_manifest"]))
    frozen_model = frozen["model_smokes"][cell["model_key"]]
    expected = {
        "python": frozen["python"],
        "platform": frozen["platform"],
        "torch": frozen["torch"],
        "transformers": frozen["transformers"],
        "cuda_runtime": frozen["cuda_runtime"],
        "cudnn": frozen["cudnn"],
        "cuda_devices": frozen["cuda_devices"],
        "model_config_commit": frozen_model["resolved_config_commit"],
        "model_dtype": frozen_model["model_dtype"],
        "chat_template_sha256": frozen_model["chat_template_sha256"],
        "model_class": frozen_model["model_class"],
        "tokenizer_class": frozen_model["tokenizer_class"],
    }
    if any(summary.get("runtime", {}).get(key) != value for key, value in expected.items()):
        raise ValueError("downloaded holdout runtime differs from Phase A")


def _without_contextual_git_fields(value: Any) -> Any:
    """Remove fields that legitimately change when evidence is reverified later."""

    if isinstance(value, dict):
        return {
            key: _without_contextual_git_fields(nested)
            for key, nested in value.items()
            if key not in {"verified_at_head", "remote_refs", "lock_remote_refs"}
        }
    if isinstance(value, list):
        return [_without_contextual_git_fields(item) for item in value]
    return value


def _all_verified_at_head(value: Any, expected: str) -> bool:
    if isinstance(value, dict):
        if "verified_at_head" in value and value["verified_at_head"] != expected:
            return False
        return all(_all_verified_at_head(item, expected) for item in value.values())
    if isinstance(value, list):
        return all(_all_verified_at_head(item, expected) for item in value)
    return True


def verify_frozen_artifact_evidence(
    evidence: dict[str, Any], frozen_payload: dict[str, Any], capture_commit: str
) -> None:
    expected_bindings: dict[str, str] = {}
    for record in artifact_records(frozen_payload):
        path = str(record["path"])
        digest = str(record["sha256"])
        previous = expected_bindings.get(path)
        if previous is not None and previous != digest:
            raise ValueError(f"conflicting local frozen bindings for {path}")
        expected_bindings[path] = digest
    if set(evidence) != set(expected_bindings):
        raise ValueError("cloud frozen-artifact path set is incomplete")
    for path, metadata in evidence.items():
        committed = committed_file_info(ROOT, repo_path(path))
        if (
            metadata.get("path") != path
            or metadata.get("sha256") != expected_bindings[path]
            or metadata.get("sha256") != committed["sha256"]
            or metadata.get("last_change_commit")
            != committed["last_change_commit"]
            or metadata.get("verified_at_head") != capture_commit
        ):
            raise ValueError(f"cloud frozen-artifact evidence differs for {path}")


def verify_lock_evidence(
    evidence: dict[str, Any],
    local: dict[str, dict[str, Any]],
    *,
    capture_commit: str,
    target_cell_id: str,
    target_binding: dict[str, Any],
    transport: dict[str, Any],
    lock: dict[str, Any],
) -> None:
    if set(evidence) != set(local) or not _all_verified_at_head(
        evidence, capture_commit
    ):
        raise ValueError("cloud LTT evidence is incomplete or from another commit")
    if _without_contextual_git_fields(evidence) != _without_contextual_git_fields(local):
        raise ValueError("cloud LTT evidence differs from canonical re-verification")
    cell = transport_cell(transport, target_cell_id)
    lock_path = repo_path(cell["ltt_lock_manifest"])
    determination_path = repo_path(cell["ltt_determination"])
    expected = {
        "lock_path": cell["ltt_lock_manifest"],
        "lock_sha256": sha256_file(lock_path),
        "lock_commit": committed_file_info(ROOT, lock_path),
        "determination_path": cell["ltt_determination"],
        "determination_sha256": sha256_file(determination_path),
        "determination_commit": committed_file_info(ROOT, determination_path),
        "selected_policy_sha256": canonical_json_sha256(lock["selected_policy"]),
    }
    if not _all_verified_at_head(target_binding, capture_commit) or (
        _without_contextual_git_fields(target_binding)
        != _without_contextual_git_fields(expected)
    ):
        raise ValueError("cloud target-lock binding differs from committed evidence")


def verify_model_artifact(
    model_path: Path,
    *,
    cell_id: str,
    bundle_dir: Path,
    evidence_path: Path,
) -> dict[str, str]:
    prefix = f"px057_h4_holdout/{cell_id}"
    expected = {"cloud_job_evidence.json": sha256_file(evidence_path)}
    expected.update(
        {
            f"{prefix}/{name}": sha256_file(bundle_dir / name)
            for name in COLLECTION_FILES
        }
    )
    expected[f"{prefix}/cloud_job_evidence.json"] = sha256_file(evidence_path)
    observed: dict[str, str] = {}
    regular_file_count = 0
    with tarfile.open(model_path, "r:gz") as handle:
        for member in handle.getmembers():
            normalized = member.name.removeprefix("./")
            if member.isdir():
                continue
            regular_file_count += 1
            if not member.isfile() or normalized not in expected:
                raise ValueError(f"unexpected SageMaker model member: {member.name}")
            if normalized in observed:
                raise ValueError(
                    f"duplicate SageMaker model member: {member.name}"
                )
            extracted = handle.extractfile(member)
            if extracted is None:
                raise ValueError(f"unreadable SageMaker model member: {member.name}")
            observed[normalized] = hashlib.sha256(extracted.read()).hexdigest()
    if regular_file_count != len(expected) or observed != expected:
        raise ValueError("SageMaker model artifact is incomplete or differs from S3 evidence")
    return observed


def atomic_install(
    bundle_source: Path,
    manifest_source: Path,
    *,
    output_dir: Path,
    cloud_target: Path,
) -> None:
    """Install the verified pair without leaving a half-installed bundle."""

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    cloud_target.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() or cloud_target.exists():
        raise FileExistsError("holdout evidence target already exists")
    os.replace(bundle_source, output_dir)
    try:
        os.replace(manifest_source, cloud_target)
    except Exception:
        shutil.rmtree(output_dir)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cell", required=True, choices=tuple(CELL_JOB_CODES))
    parser.add_argument("--config", type=Path, default=DEFAULT_TRANSPORT_CONFIG)
    parser.add_argument("--profile")
    args = parser.parse_args()

    transport_path = args.config.resolve()
    transport = read_json_strict(transport_path)
    verify_transport_config(transport)
    verify_git(transport["repository"]["branch"])
    freeze_evidence = verify_transport_freeze(transport_path, transport)
    freeze_path = freeze_manifest_path(transport)
    science_path = science_config_path(transport)
    science = read_json(science_path)
    phase_a = verify_phase_a_freeze(
        ROOT, science_path, science, require_current_runtime=False
    )
    cell_id = args.cell
    local_ltt_evidence, locks = verify_ltt_locks(
        transport,
        science,
        science_path,
        eligible_cell_id=cell_id,
    )
    lock = locks[cell_id]
    cell = transport_cell(transport, cell_id)
    science_cells = {row["cell_id"]: row for row in science["cells"]}
    science_cell = science_cells[cell_id]
    job_name = cell["job_name"]
    if job_name != holdout_job_name(cell_id):
        raise ValueError("--cell does not map to the frozen first-attempt job")

    aws_config = transport["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    description = aws_json(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        job_name,
    )
    if description.get("TrainingJobStatus") != "Completed":
        raise ValueError(
            f"{job_name}: expected Completed, found {description.get('TrainingJobStatus')}"
        )
    capture_commit, code_uri, output_uri, request = verify_job_request(
        description,
        transport,
        science,
        cell_id=cell_id,
        transport_path=transport_path,
        freeze_sha256=freeze_evidence["freeze_sha256"],
        lock=lock,
    )
    launch_registration = verify_launch_registration(
        transport,
        cell_id=cell_id,
        description=description,
        request=request,
    )
    tags = verify_tags(
        aws_json(
            profile,
            region,
            "sagemaker",
            "list-tags",
            "--resource-arn",
            description["TrainingJobArn"],
        ),
        transport=transport,
        cell_id=cell_id,
        capture_commit=capture_commit,
    )

    output_dir = repo_path(cell["output_dir"])
    cloud_target = repo_path(cell["cloud_manifest"])
    if output_dir.exists() or cloud_target.exists():
        raise FileExistsError("holdout evidence target already exists")
    verify_no_downstream_evidence(transport, cell_id=cell_id)
    result_uri = request["Environment"]["PX057_H4_RESULT_S3_URI"].rstrip("/")
    result_bucket, result_prefix = parse_s3_uri(result_uri)
    if (
        result_bucket != aws_config["bucket"]
        or result_prefix != str(cell["result_prefix"]).strip("/")
    ):
        raise ValueError("holdout result URI differs from the frozen cell prefix")

    with tempfile.TemporaryDirectory(
        prefix=f".px057-h4-{CELL_JOB_CODES[cell_id]}-holdout-fetch-", dir=ROOT
    ) as temp:
        temp_path = Path(temp)
        bundle_temp = temp_path / "bundle"
        bundle_temp.mkdir()
        evidence_temp = temp_path / "cloud_job_evidence.json"
        source_temp = temp_path / "source.tar.gz"
        model_temp = temp_path / "model.tar.gz"

        evidence_object = download_single_version(
            profile=profile,
            region=region,
            uri=f"{result_uri}/cloud_job_evidence.json",
            destination=evidence_temp,
        )
        if evidence_object["server_side_encryption"] != "AES256":
            raise ValueError("holdout cloud evidence object is not AES256 encrypted")
        evidence = read_json_strict(evidence_temp)

        source_bucket, source_key = parse_s3_uri(code_uri)
        sole_source_version = require_single_version(
            profile=profile,
            region=region,
            bucket=source_bucket,
            key=source_key,
        )
        expected_source_version = request["Environment"]["PX057_H4_SOURCE_VERSION_ID"]
        if sole_source_version != expected_source_version:
            raise ValueError("source S3 history differs from the registered version")
        source_object = download_versioned(
            profile=profile,
            region=region,
            uri=code_uri,
            destination=source_temp,
            expected_version_id=expected_source_version,
        )
        if source_object["server_side_encryption"] != "AES256":
            raise ValueError("holdout source object is not AES256 encrypted")
        source_members = verify_source_archive(
            source_temp,
            transport=transport,
            capture_commit=capture_commit,
            expected_sha256=request["Environment"]["PX057_H4_SOURCE_SHA256"],
        )

        observed_branch_head = str(evidence.get("observed_remote_branch_head", ""))
        if (
            len(observed_branch_head) != 40
            or subprocess.run(
                ["git", "merge-base", "--is-ancestor", capture_commit, observed_branch_head],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
            or subprocess.run(
                ["git", "merge-base", "--is-ancestor", observed_branch_head, "HEAD"],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
        ):
            raise ValueError("cloud-observed branch head has invalid ancestry")
        entry_hashes = {
            relative: hashlib.sha256(
                subprocess.check_output(
                    ["git", "show", f"{capture_commit}:{relative}"], cwd=ROOT
                )
            ).hexdigest()
            for relative in (ENTRY, CALIBRATION_ENTRY, PHASE_A_ENTRY)
        }
        expected_identity = {
            "experiment_id": transport["experiment_id"],
            "transport_id": transport["transport_id"],
            "stage": "PX057_H4_holdout_cloud_collection",
            "status": "PASS",
            "scientific_data_generated": True,
            "split": "holdout",
            "cell_id": cell_id,
            "job_name": job_name,
            "repository_url": transport["repository"]["url"],
            "branch": transport["repository"]["branch"],
            "git_commit": capture_commit,
            "container_image_digest": aws_config["container_digest"],
            "entrypoint_sha256": entry_hashes[ENTRY],
            "calibration_helper_sha256": entry_hashes[CALIBRATION_ENTRY],
            "phase_a_helper_sha256": entry_hashes[PHASE_A_ENTRY],
        }
        if any(evidence.get(key) != value for key, value in expected_identity.items()):
            raise ValueError("holdout cloud evidence failed identity checks")
        expected_artifacts = {
            "transport_config": {
                "path": transport_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(transport_path),
            },
            "transport_freeze": {
                "path": freeze_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(freeze_path),
                "status": "PASS",
            },
            "science_config": {
                "path": science_path.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(science_path),
            },
        }
        if any(evidence.get(key) != value for key, value in expected_artifacts.items()):
            raise ValueError("holdout cloud evidence has different frozen manifests")
        if (
            evidence.get("source_version_id") != source_object["version_id"]
            or evidence.get("source_sha256") != source_object["sha256"]
            or evidence.get("source_bucket") != source_bucket
            or evidence.get("source_key") != source_key
        ):
            raise ValueError("holdout cloud evidence has a different source identity")
        verify_frozen_artifact_evidence(
            evidence.get("frozen_scientific_artifacts", {}),
            transport,
            capture_commit,
        )
        verify_frozen_artifact_evidence(
            evidence.get("frozen_transport_artifacts", {}),
            read_json_strict(freeze_path),
            capture_commit,
        )
        verify_lock_evidence(
            evidence.get("all_ltt_lock_evidence", {}),
            local_ltt_evidence,
            capture_commit=capture_commit,
            target_cell_id=cell_id,
            target_binding=evidence.get("target_ltt_binding", {}),
            transport=transport,
            lock=lock,
        )
        if _without_contextual_git_fields(evidence.get("phase_a_evidence", {})) != (
            _without_contextual_git_fields(phase_a)
        ) or not _all_verified_at_head(evidence.get("phase_a_evidence", {}), capture_commit):
            raise ValueError("holdout Phase A evidence differs from the frozen capture")

        receipts = evidence.get("collection_objects", {})
        if set(receipts) != set(COLLECTION_FILES):
            raise ValueError("holdout cloud evidence has an incomplete receipt set")
        downloaded_objects: dict[str, dict[str, Any]] = {}
        for name in COLLECTION_FILES:
            receipt = receipts[name]
            key = f"{result_prefix}/{name}"
            if (
                receipt.get("bucket") != result_bucket
                or receipt.get("key") != key
                or not receipt.get("version_id")
                or len(str(receipt.get("sha256", ""))) != 64
                or receipt.get("server_side_encryption") != "AES256"
            ):
                raise ValueError(f"invalid holdout cloud receipt for {name}")
            sole_version = require_single_version(
                profile=profile,
                region=region,
                bucket=result_bucket,
                key=key,
            )
            if sole_version != receipt["version_id"]:
                raise ValueError(f"holdout S3 history differs for {name}")
            destination = bundle_temp / name
            downloaded = download_versioned(
                profile=profile,
                region=region,
                uri=f"s3://{result_bucket}/{key}",
                destination=destination,
                expected_version_id=receipt["version_id"],
            )
            if (
                downloaded["sha256"] != receipt["sha256"]
                or downloaded["content_length"] != int(receipt["size_bytes"])
                or downloaded["server_side_encryption"] != "AES256"
            ):
                raise ValueError(f"downloaded holdout object differs for {name}")
            downloaded_objects[name] = downloaded

        verification = verify_collection_bundle(
            bundle_temp,
            repo_path(cell["holdout_manifest"]),
            expected_cell_id=cell_id,
            expected_split="holdout",
            expected_n=int(transport["collection"]["expected_traces"]),
            expected_rounds=int(transport["collection"]["rounds"]),
            expected_model=science["models"][science_cell["model_key"]],
            expected_prompt_id=science["generation"]["prompt_template_id"],
            expected_prompt_sha256=science["generation"]["prompt_template_sha256"],
        )
        if (
            verification["trace_count"] != 300
            or verification["raw_generation_count"] != 2400
        ):
            raise ValueError("holdout collection is not the frozen 300/2400 design")
        summary = read_json_strict(bundle_temp / "collection_summary.json")
        verify_runtime_summary(summary, science, science_cell)
        if (
            summary.get("config_commit", {}).get("verified_at_head") != capture_commit
            or summary.get("phase_a_evidence", {}).get("verified_at_head")
            != capture_commit
            or any(
                item.get("verified_at_head") != capture_commit
                for item in summary.get("code_evidence", {}).values()
            )
        ):
            raise ValueError("holdout summary was not generated at the cloud commit")
        recorded_verification = evidence.get("collection_verification", {})
        if (
            int(recorded_verification.get("trace_count", -1)) != 300
            or int(recorded_verification.get("raw_generation_count", -1)) != 2400
            or any(
                recorded_verification.get("files", {}).get(name, {}).get("sha256")
                != metadata["sha256"]
                for name, metadata in verification["files"].items()
            )
        ):
            raise ValueError("local holdout verification differs from cloud evidence")

        model_uri = description.get("ModelArtifacts", {}).get("S3ModelArtifacts")
        expected_model_uri = f"{output_uri}/{job_name}/output/model.tar.gz"
        if model_uri != expected_model_uri:
            raise ValueError("SageMaker model artifact URI differs from the request")
        model_object = download_single_version(
            profile=profile,
            region=region,
            uri=model_uri,
            destination=model_temp,
        )
        if model_object["server_side_encryption"] != "AES256":
            raise ValueError("SageMaker model artifact is not AES256 encrypted")
        model_members = verify_model_artifact(
            model_temp,
            cell_id=cell_id,
            bundle_dir=bundle_temp,
            evidence_path=evidence_temp,
        )

        cloud_manifest = {
            "experiment_id": transport["experiment_id"],
            "transport_id": transport["transport_id"],
            "stage": "H4_holdout_cloud_job_manifest",
            "status": "PASS",
            "scientific_data_generated": True,
            "scientific_result_computed": False,
            "split": "holdout",
            "cell_id": cell_id,
            "job_name": job_name,
            "job_arn": description["TrainingJobArn"],
            "job_status": description["TrainingJobStatus"],
            "creation_time": description["CreationTime"],
            "training_start_time": description["TrainingStartTime"],
            "training_end_time": description["TrainingEndTime"],
            "billable_seconds": description.get("BillableTimeInSeconds"),
            "git_commit": capture_commit,
            "observed_remote_branch_head": observed_branch_head,
            "role_arn": description["RoleArn"],
            "repository_url": transport["repository"]["url"],
            "branch": transport["repository"]["branch"],
            "huggingface_secret_id": aws_config["huggingface_secret_id"],
            "result_s3_uri": result_uri,
            "output_s3_path": output_uri,
            "max_runtime_seconds": HOLDOUT_MAX_RUNTIME_SECONDS,
            "network_isolation": description["EnableNetworkIsolation"],
            "tags": tags,
            "entrypoint_sha256": entry_hashes[ENTRY],
            "calibration_helper_sha256": entry_hashes[CALIBRATION_ENTRY],
            "phase_a_helper_sha256": entry_hashes[PHASE_A_ENTRY],
            "container_image_digest": aws_config["container_digest"],
            "container_image_pinned_uri": description["AlgorithmSpecification"][
                "TrainingImage"
            ],
            "resource_config": description["ResourceConfig"],
            "source_artifact": source_object,
            "source_members": source_members,
            "cloud_evidence_object": evidence_object,
            "collection_objects": downloaded_objects,
            "collection_verification": verification,
            "model_artifact": model_object,
            "model_members": model_members,
            "launch_registration": launch_registration,
            "transport_freeze": freeze_evidence,
            "all_ltt_lock_evidence": local_ltt_evidence,
            "target_ltt_binding": evidence["target_ltt_binding"],
            "phase_a_evidence": phase_a,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": (
                "This manifest proves immutable retrieval and structural identity "
                "for one frozen held-out cell. It does not compute H4 point gates, "
                "perform the blinded manual audit, or establish an H4 result."
            ),
        }
        manifest_temp = temp_path / "holdout_cloud_job_manifest.json"
        write_json(manifest_temp, cloud_manifest)

        verify_no_downstream_evidence(transport, cell_id=cell_id)
        atomic_install(
            bundle_temp,
            manifest_temp,
            output_dir=output_dir,
            cloud_target=cloud_target,
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "scientific_result_computed": False,
                "cell_id": cell_id,
                "output_dir": output_dir.relative_to(ROOT).as_posix(),
                "cloud_job_manifest": cloud_target.relative_to(ROOT).as_posix(),
                "cloud_evidence_version_id": evidence_object["version_id"],
                "model_artifact_version_id": model_object["version_id"],
                "trace_count": verification["trace_count"],
                "raw_generation_count": verification["raw_generation_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
