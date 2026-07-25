#!/usr/bin/env python
"""Fetch, verify, and install one completed PX-057 H4 calibration bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_px057_h4_phase_a import (
    aws_json,
    download_versioned,
    parse_s3_uri,
)
from scripts.px057_h4_common import (
    committed_file_info,
    read_json,
    sha256_file,
    verify_collection_bundle,
    verify_phase_a_freeze,
    write_json,
)
from scripts.submit_px057_h4_calibration import (
    CALIBRATION_MAX_RUNTIME_SECONDS,
    CELL_JOB_CODES,
    ENTRY,
    PHASE_A_ENTRY,
    source_launch_command,
    training_request,
    verify_transport_config,
)


DEFAULT_CONFIG = ROOT / "configs/px057_h4_ltt_transfer_20260725.json"
COLLECTION_FILES = (
    "selected_rows.jsonl",
    "reasoning_traces.jsonl",
    "raw_generations.jsonl",
    "collection_summary.json",
)


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def verify_repository_state(branch: str) -> str:
    if subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT).returncode != 0:
        raise ValueError("fetch requires no tracked worktree changes")
    head = output(["git", "rev-parse", "HEAD"])
    if output(["git", "branch", "--show-current"]) != branch:
        raise ValueError(f"fetch requires branch {branch}")
    remote_line = output(["git", "ls-remote", "origin", f"refs/heads/{branch}"])
    remote_head = remote_line.split()[0] if remote_line else ""
    if remote_head != head:
        raise ValueError("fetch requires the current local HEAD to be pushed")
    return head


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
    deletes = [row for row in listing.get("DeleteMarkers", []) if row.get("Key") == key]
    if len(versions) != 1 or deletes:
        raise ValueError(
            f"s3://{bucket}/{key}: expected exactly one immutable version and no delete marker"
        )
    if not versions[0].get("IsLatest"):
        raise ValueError(f"s3://{bucket}/{key}: sole version is not latest")
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


def expected_environment(
    config: dict[str, Any], *, job_name: str, cell_id: str, git_commit: str
) -> dict[str, str | None]:
    aws_config = config["phase_a"]["aws"]
    prefix = aws_config["s3_prefix"].strip("/")
    result_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/calibration/{cell_id}/{job_name}"
    )
    return {
        "AWS_REGION": aws_config["region"],
        "HF_HOME": "/opt/ml/input/data/huggingface",
        "TOKENIZERS_PARALLELISM": "false",
        "PX057_H4_REPOSITORY_URL": aws_config["repository_url"],
        "PX057_H4_BRANCH": aws_config["branch"],
        "PX057_H4_GIT_COMMIT": git_commit,
        "PX057_CONTAINER_IMAGE_DIGEST": aws_config["container_image_digest"],
        "PX057_H4_HF_SECRET_ID": aws_config["huggingface_secret_id"],
        "PX057_H4_RESULT_S3_URI": result_uri,
        "PX057_H4_JOB_NAME": job_name,
        "PX057_H4_SOURCE_VERSION_ID": None,
        "PX057_H4_SOURCE_SHA256": None,
        "PX057_H4_SOURCE_BUCKET": aws_config["bucket"],
        "PX057_H4_SOURCE_KEY": (
            f"{prefix}/code/{job_name}/source.tar.gz"
        ),
        "PX057_H4_CELL_ID": cell_id,
    }


def verify_job_request(
    description: dict[str, Any],
    config: dict[str, Any],
    *,
    job_name: str,
    cell_id: str,
) -> tuple[str, str, str]:
    aws_config = config["phase_a"]["aws"]
    environment = description["Environment"]
    capture_commit = str(environment.get("PX057_H4_GIT_COMMIT", ""))
    if len(capture_commit) != 40:
        raise ValueError("cloud job has no valid 40-character Git commit")
    if (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", capture_commit, "HEAD"],
            cwd=ROOT,
            check=False,
        ).returncode
        != 0
    ):
        raise ValueError("calibration cloud commit is not an ancestor of current HEAD")
    prefix = aws_config["s3_prefix"].strip("/")
    expected_code_uri = (
        f"s3://{aws_config['bucket']}/{prefix}/code/{job_name}/source.tar.gz"
    )
    expected_output_uri = f"s3://{aws_config['bucket']}/{prefix}/sagemaker-output"
    launch = source_launch_command()
    expected_env = expected_environment(
        config, job_name=job_name, cell_id=cell_id, git_commit=capture_commit
    )
    expected_env["PX057_H4_SOURCE_VERSION_ID"] = environment.get(
        "PX057_H4_SOURCE_VERSION_ID"
    )
    expected_env["PX057_H4_SOURCE_SHA256"] = environment.get("PX057_H4_SOURCE_SHA256")
    algorithm = description["AlgorithmSpecification"]
    resource = description["ResourceConfig"]
    source_data = description["InputDataConfig"][0]["DataSource"]["S3DataSource"]
    if (
        description["TrainingJobName"] != job_name
        or description["RoleArn"] != aws_config["role_arn"]
        or algorithm["TrainingImage"] != aws_config["container_image_pinned_uri"]
        or algorithm["TrainingInputMode"] != "File"
        or algorithm.get("ContainerEntrypoint") != ["bash", "-lc"]
        or algorithm.get("ContainerArguments") != [launch]
        or environment != expected_env
        or description.get("EnableNetworkIsolation") is not False
        or len(description["InputDataConfig"]) != 1
        or description["InputDataConfig"][0]["ChannelName"] != "code"
        or description["InputDataConfig"][0]["InputMode"] != "File"
        or source_data["S3DataType"] != "S3Prefix"
        or source_data["S3Uri"] != expected_code_uri
        or source_data["S3DataDistributionType"] != "FullyReplicated"
        or description["OutputDataConfig"]["S3OutputPath"] != expected_output_uri
        or resource["InstanceType"] != aws_config["instance_type"]
        or int(resource["InstanceCount"]) != 1
        or int(resource["VolumeSizeInGB"]) != int(aws_config["volume_size_gb"])
        or int(description["StoppingCondition"]["MaxRuntimeInSeconds"])
        != CALIBRATION_MAX_RUNTIME_SECONDS
        or not environment.get("PX057_H4_SOURCE_VERSION_ID")
        or len(str(environment.get("PX057_H4_SOURCE_SHA256", ""))) != 64
    ):
        raise ValueError("calibration cloud request differs from the frozen launcher")
    return capture_commit, expected_code_uri, expected_output_uri


def verify_source_archive(
    source_path: Path,
    *,
    expected_entry_sha256: str,
    expected_phase_a_sha256: str,
) -> None:
    with tarfile.open(source_path, "r:gz") as handle:
        names = set(handle.getnames())
        if names != {ENTRY, PHASE_A_ENTRY}:
            raise ValueError(f"unexpected calibration source members: {sorted(names)}")
        entry_file = handle.extractfile(ENTRY)
        phase_file = handle.extractfile(PHASE_A_ENTRY)
        if entry_file is None or phase_file is None:
            raise ValueError("calibration source archive contains a non-file member")
        entry_sha = hashlib.sha256(entry_file.read()).hexdigest()
        phase_sha = hashlib.sha256(phase_file.read()).hexdigest()
    if entry_sha != expected_entry_sha256 or phase_sha != expected_phase_a_sha256:
        raise ValueError("calibration source entry hash mismatch")


def verify_launch_registration(
    config: dict[str, Any],
    cell: dict[str, Any],
    description: dict[str, Any],
    code_uri: str,
) -> dict[str, Any]:
    path = ROOT / cell["calibration_launch_manifest"]
    committed = committed_file_info(ROOT, path)
    remote_refs = [
        value.strip()
        for value in subprocess.check_output(
            [
                "git",
                "branch",
                "-r",
                "--contains",
                committed["last_change_commit"],
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
        if value.strip()
    ]
    if not remote_refs:
        raise ValueError("calibration launch registration has not been pushed")
    launch = read_json(path)
    environment = description["Environment"]
    request = training_request(
        config,
        job_name=description["TrainingJobName"],
        cell_id=cell["cell_id"],
        code_uri=code_uri,
        code_version_id=environment["PX057_H4_SOURCE_VERSION_ID"],
        code_sha256=environment["PX057_H4_SOURCE_SHA256"],
        git_commit=environment["PX057_H4_GIT_COMMIT"],
    )
    request_sha256 = hashlib.sha256(
        (json.dumps(request, sort_keys=True, separators=(",", ":")) + "\n").encode(
            "utf-8"
        )
    ).hexdigest()
    if (
        launch.get("experiment_id") != config["experiment_id"]
        or launch.get("stage") != "H4_calibration_launch_registration"
        or launch.get("status") != "REGISTERED_PRE_RESULT"
        or launch.get("scientific_result_observed") is not False
        or launch.get("cell_id") != cell["cell_id"]
        or launch.get("job_name") != description["TrainingJobName"]
        or launch.get("training_job_arn") != description["TrainingJobArn"]
        or launch.get("git_commit") != environment["PX057_H4_GIT_COMMIT"]
        or launch.get("container_image")
        != config["phase_a"]["aws"]["container_image_pinned_uri"]
        or launch.get("code_uri") != code_uri
        or launch.get("code_version_id")
        != environment["PX057_H4_SOURCE_VERSION_ID"]
        or launch.get("code_sha256") != environment["PX057_H4_SOURCE_SHA256"]
        or launch.get("calibration_result_uri")
        != environment["PX057_H4_RESULT_S3_URI"]
        or int(launch.get("max_runtime_seconds", -1))
        != CALIBRATION_MAX_RUNTIME_SECONDS
        or launch.get("request_sha256") != request_sha256
    ):
        raise ValueError("cloud job differs from its pre-result launch registration")
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": sha256_file(path),
        "last_change_commit": committed["last_change_commit"],
        "remote_refs": remote_refs,
        "registration": launch,
    }


def verify_runtime_summary(
    summary: dict[str, Any], config: dict[str, Any], cell: dict[str, Any]
) -> None:
    frozen = read_json(ROOT / config["phase_a"]["runtime_manifest"])
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
    if any(summary["runtime"].get(key) != value for key, value in expected.items()):
        raise ValueError("downloaded calibration runtime differs from Phase A")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-name", required=True)
    parser.add_argument("--cell", choices=tuple(CELL_JOB_CODES))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--profile")
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = read_json(config_path)
    verify_transport_config(config)
    aws_config = config["phase_a"]["aws"]
    profile = args.profile or aws_config["profile"]
    region = aws_config["region"]
    verify_repository_state(aws_config["branch"])
    phase_a = verify_phase_a_freeze(
        ROOT, config_path, config, require_current_runtime=False
    )

    description = aws_json(
        profile,
        region,
        "sagemaker",
        "describe-training-job",
        "--training-job-name",
        args.job_name,
    )
    if description["TrainingJobStatus"] != "Completed":
        raise ValueError(
            f"{args.job_name}: expected Completed, found {description['TrainingJobStatus']}"
        )
    cell_id = str(description.get("Environment", {}).get("PX057_H4_CELL_ID", ""))
    if cell_id not in CELL_JOB_CODES or (args.cell is not None and args.cell != cell_id):
        raise ValueError("job cell identity is missing or differs from --cell")
    cells = [cell for cell in config["cells"] if cell["cell_id"] == cell_id]
    if len(cells) != 1:
        raise ValueError("job cell is not unique in the frozen config")
    cell = cells[0]
    capture_commit, code_uri, output_uri = verify_job_request(
        description, config, job_name=args.job_name, cell_id=cell_id
    )
    launch_registration = verify_launch_registration(
        config, cell, description, code_uri
    )

    tags_response = aws_json(
        profile,
        region,
        "sagemaker",
        "list-tags",
        "--resource-arn",
        description["TrainingJobArn"],
    )
    tags = {row["Key"]: row["Value"] for row in tags_response.get("Tags", [])}
    expected_tags = {
        "Project": "PraxisResearch",
        "PraxisId": "PX-057",
        "Gate": "H4-Calibration",
        "Cell": cell_id,
        "GitCommit": capture_commit,
    }
    if any(tags.get(key) != value for key, value in expected_tags.items()):
        raise ValueError("calibration cloud job tags differ from the launcher")

    environment = description["Environment"]
    result_uri = str(environment["PX057_H4_RESULT_S3_URI"]).rstrip("/")
    result_bucket, result_prefix = parse_s3_uri(result_uri)
    output_dir = ROOT / cell["output_dirs"]["calibration"]
    cloud_target = (
        ROOT / cell["calibration_cloud_manifest"]
    )
    if output_dir.exists() or cloud_target.exists():
        raise FileExistsError("calibration evidence target already exists")

    with tempfile.TemporaryDirectory(
        prefix=f".px057-h4-{CELL_JOB_CODES[cell_id]}-fetch-", dir=ROOT
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
            raise ValueError("cloud evidence object is not AES256 encrypted")
        evidence = read_json(evidence_temp)
        source_object = download_versioned(
            profile=profile,
            region=region,
            uri=code_uri,
            destination=source_temp,
            expected_version_id=environment["PX057_H4_SOURCE_VERSION_ID"],
        )
        if source_object["sha256"] != environment["PX057_H4_SOURCE_SHA256"]:
            raise ValueError("source archive differs from the job environment hash")
        if source_object["server_side_encryption"] != "AES256":
            raise ValueError("source archive is not AES256 encrypted")

        current_entry_sha = committed_file_info(ROOT, ROOT / ENTRY)["sha256"]
        current_phase_a_sha = committed_file_info(ROOT, ROOT / PHASE_A_ENTRY)[
            "sha256"
        ]
        verify_source_archive(
            source_temp,
            expected_entry_sha256=current_entry_sha,
            expected_phase_a_sha256=current_phase_a_sha,
        )
        observed_branch_head = str(evidence.get("observed_remote_branch_head", ""))
        if (
            len(observed_branch_head) != 40
            or subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    capture_commit,
                    observed_branch_head,
                ],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
            or subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    observed_branch_head,
                    "HEAD",
                ],
                cwd=ROOT,
                check=False,
            ).returncode
            != 0
        ):
            raise ValueError("cloud-observed branch head has invalid ancestry")
        if (
            evidence.get("experiment_id") != config["experiment_id"]
            or evidence.get("stage") != "PX057_H4_calibration_cloud_collection"
            or evidence.get("status") != "PASS"
            or evidence.get("scientific_data_generated") is not True
            or evidence.get("split") != "calibration"
            or evidence.get("cell_id") != cell_id
            or evidence.get("job_name") != args.job_name
            or evidence.get("repository_url") != aws_config["repository_url"]
            or evidence.get("branch") != aws_config["branch"]
            or evidence.get("git_commit") != capture_commit
            or evidence.get("container_image_digest")
            != aws_config["container_image_digest"]
            or evidence.get("entrypoint_sha256") != current_entry_sha
            or evidence.get("phase_a_helper_sha256") != current_phase_a_sha
            or evidence.get("source_version_id") != source_object["version_id"]
            or evidence.get("source_sha256") != source_object["sha256"]
            or evidence.get("phase_a_evidence", {}).get("runtime_sha256")
            != phase_a["runtime_sha256"]
            or evidence.get("phase_a_evidence", {}).get("freeze", {}).get("sha256")
            != phase_a["freeze"]["sha256"]
        ):
            raise ValueError("calibration cloud evidence failed identity checks")

        downloaded_objects: dict[str, dict[str, Any]] = {}
        receipts = evidence.get("collection_objects", {})
        if set(receipts) != set(COLLECTION_FILES):
            raise ValueError("cloud evidence has an incomplete collection receipt set")
        for name in COLLECTION_FILES:
            receipt = receipts[name]
            expected_key = f"{result_prefix}/{name}"
            if (
                receipt.get("bucket") != result_bucket
                or receipt.get("key") != expected_key
                or not receipt.get("version_id")
                or len(str(receipt.get("sha256", ""))) != 64
                or receipt.get("server_side_encryption") != "AES256"
            ):
                raise ValueError(f"invalid cloud receipt for {name}")
            destination = bundle_temp / name
            downloaded = download_versioned(
                profile=profile,
                region=region,
                uri=f"s3://{result_bucket}/{expected_key}",
                destination=destination,
                expected_version_id=receipt["version_id"],
            )
            if (
                downloaded["sha256"] != receipt["sha256"]
                or downloaded["content_length"] != int(receipt["size_bytes"])
                or downloaded["server_side_encryption"] != "AES256"
            ):
                raise ValueError(f"downloaded cloud object differs for {name}")
            downloaded_objects[name] = downloaded

        verification = verify_collection_bundle(
            bundle_temp,
            ROOT / cell["calibration_manifest"],
            expected_cell_id=cell_id,
            expected_split="calibration",
            expected_n=int(config["split_design"]["calibration_n"]),
            expected_rounds=int(config["generation"]["rounds"]),
            expected_model=config["models"][cell["model_key"]],
            expected_prompt_id=config["generation"]["prompt_template_id"],
            expected_prompt_sha256=config["generation"]["prompt_template_sha256"],
        )
        summary = read_json(bundle_temp / "collection_summary.json")
        verify_runtime_summary(summary, config, cell)
        if (
            summary.get("config_commit", {}).get("verified_at_head") != capture_commit
            or summary.get("phase_a_evidence", {}).get("verified_at_head")
            != capture_commit
            or any(
                item.get("verified_at_head") != capture_commit
                for item in summary.get("code_evidence", {}).values()
            )
        ):
            raise ValueError("collection summary was not generated at the cloud commit")

        recorded_verification = evidence.get("collection_verification", {})
        if (
            int(recorded_verification.get("trace_count", -1))
            != verification["trace_count"]
            or int(recorded_verification.get("raw_generation_count", -1))
            != verification["raw_generation_count"]
            or any(
                recorded_verification.get("files", {}).get(name, {}).get("sha256")
                != metadata["sha256"]
                for name, metadata in verification["files"].items()
            )
        ):
            raise ValueError("local collection verification differs from cloud evidence")

        expected_model_uri = (
            f"{output_uri}/{args.job_name}/output/model.tar.gz"
        )
        model_uri = description["ModelArtifacts"]["S3ModelArtifacts"]
        if model_uri != expected_model_uri:
            raise ValueError("SageMaker model artifact URI differs from the request")
        model_object = download_single_version(
            profile=profile,
            region=region,
            uri=model_uri,
            destination=model_temp,
        )

        cloud_manifest = {
            "experiment_id": config["experiment_id"],
            "stage": "H4_calibration_cloud_job_manifest",
            "status": "PASS",
            "scientific_data_generated": True,
            "split": "calibration",
            "cell_id": cell_id,
            "job_name": args.job_name,
            "job_arn": description["TrainingJobArn"],
            "job_status": description["TrainingJobStatus"],
            "creation_time": description["CreationTime"],
            "training_start_time": description["TrainingStartTime"],
            "training_end_time": description["TrainingEndTime"],
            "billable_seconds": description.get("BillableTimeInSeconds"),
            "git_commit": capture_commit,
            "observed_remote_branch_head": observed_branch_head,
            "role_arn": description["RoleArn"],
            "repository_url": environment["PX057_H4_REPOSITORY_URL"],
            "branch": environment["PX057_H4_BRANCH"],
            "huggingface_secret_id": environment["PX057_H4_HF_SECRET_ID"],
            "result_s3_uri": result_uri,
            "output_s3_path": output_uri,
            "max_runtime_seconds": int(
                description["StoppingCondition"]["MaxRuntimeInSeconds"]
            ),
            "network_isolation": description["EnableNetworkIsolation"],
            "tags": tags,
            "entrypoint_sha256": current_entry_sha,
            "phase_a_helper_sha256": current_phase_a_sha,
            "container_image_tag_uri": aws_config["container_image_tag_uri"],
            "container_image_digest": environment["PX057_CONTAINER_IMAGE_DIGEST"],
            "container_image_pinned_uri": description["AlgorithmSpecification"][
                "TrainingImage"
            ],
            "resource_config": description["ResourceConfig"],
            "source_artifact": source_object,
            "cloud_evidence_object": evidence_object,
            "collection_objects": downloaded_objects,
            "collection_verification": verification,
            "model_artifact": model_object,
            "launch_registration": launch_registration,
            "phase_a_evidence": phase_a,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": (
                "This manifest proves immutable retrieval and identity for one frozen "
                "calibration cell; it does not establish a risk-control or held-out result."
            ),
        }
        manifest_temp = temp_path / "calibration_cloud_job_manifest.json"
        write_json(manifest_temp, cloud_manifest)

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        cloud_target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(bundle_temp, output_dir)
        try:
            os.replace(manifest_temp, cloud_target)
        except Exception:
            shutil.rmtree(output_dir)
            raise

    print(
        json.dumps(
            {
                "status": "PASS",
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
