from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.adjudicate_px062_gate2_2 import verify_adjudication_provenance

from scripts.fetch_px062_gate2_2_results import (
    ANSWER_KEY_PATH,
    BENCHMARK_MANIFEST_PATH,
    CATALOG_PATH,
    CHECKSUM_REQUIREMENTS_PATH,
    COLLECTOR_PATH,
    CONFIG_PATH,
    DEFAULT_DESTINATION,
    ENTRYPOINT_PATH,
    FETCHER_PATH,
    FETCH_TEST_PATH,
    OUTPUT_UNCOMPRESSED_MAX_BYTES,
    OPERATOR_FETCH_POLICY_PATH,
    PX062_GATE22_PREFIX,
    REGISTRAR_PATH,
    REQUIREMENTS_GIT_PATH,
    SEALED_FILES,
    S3_CHECKSUM_FIELDS,
    TASKS_PATH,
    canonical_json_bytes,
    checksum_runtime_record,
    checksum_bytes_base64,
    operator_fetch_policy_record,
    copy_and_validate_traces,
    fetch_and_seal,
    sha256_bytes,
    validate_fetch_receipt_against_completion,
    validate_tar,
)
from scripts.register_px062_gate2_2_fetch import (
    DEFAULT_ADJUDICATION_AUTHORIZATION,
    FROZEN_EVIDENCE_CONTRACT,
    register_adjudication_authorization,
    register_completion,
    registered_artifact,
)


JOB = "px062-g22-confirm1-test"
ARN = f"arn:aws:sagemaker:us-east-1:123456789012:training-job/{JOB}"
BUCKET = "px062-test-bucket"
SOURCE_KEY = f"experiments/px062/code/{JOB}/source.tar.gz"
OUTPUT_PREFIX = "experiments/px062/output"
OUTPUT_KEY = f"{OUTPUT_PREFIX}/{JOB}/output/model.tar.gz"
SOURCE_COMMIT = "7" * 40
FETCH_COMMIT = "8" * 40
CREATED = "2026-07-28T10:00:00Z"
STARTED = "2026-07-28T10:02:00Z"
OUTPUT_TIME = "2026-07-28T10:29:50Z"
ENDED = "2026-07-28T10:30:00Z"
MODIFIED = "2026-07-28T10:30:01Z"
SOURCE_TIME = "2026-07-28T09:45:00Z"
REGISTERED = datetime(2026, 7, 28, 10, 31, tzinfo=timezone.utc)
FETCHED = datetime(2026, 7, 28, 10, 32, tzinfo=timezone.utc)


def write(root: Path, relative: str, raw: bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return path


def json_bytes(value: object) -> bytes:
    return canonical_json_bytes(value)


def compact_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def checksum(raw: bytes) -> str:
    return base64.b64encode(hashlib.sha256(raw).digest()).decode("ascii")


def add_member(
    handle: tarfile.TarFile,
    name: str,
    raw: bytes,
    *,
    kind: str = "file",
    linkname: str = "",
) -> None:
    info = tarfile.TarInfo(name)
    info.uid = 0
    info.gid = 0
    info.mtime = 0
    if kind == "directory":
        info.type = tarfile.DIRTYPE
        info.size = 0
        handle.addfile(info)
    elif kind == "symlink":
        info.type = tarfile.SYMTYPE
        info.linkname = linkname
        info.size = 0
        handle.addfile(info)
    else:
        info.size = len(raw)
        handle.addfile(info, io.BytesIO(raw))


def make_tar(
    files: dict[str, bytes],
    *,
    directories: tuple[str, ...] = (),
    extra: tuple[str, bytes, str, str] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as handle:
        for directory in directories:
            add_member(handle, directory, b"", kind="directory")
        for name, raw in files.items():
            add_member(handle, name, raw)
        if extra is not None:
            add_member(handle, extra[0], extra[1], kind=extra[2], linkname=extra[3])
    return buffer.getvalue()


def artifact(raw: bytes, key: str, version: str, modified: str, encryption: str):
    etag = hashlib.md5(raw, usedforsecurity=False).hexdigest()
    checksum_value = checksum(raw)
    row = {
        "Key": key,
        "VersionId": version,
        "IsLatest": True,
        "ETag": f'"{etag}"',
        "Size": len(raw),
        "LastModified": modified,
        "ChecksumAlgorithm": ["SHA256"],
        "ChecksumType": "FULL_OBJECT",
    }
    head = {
        "VersionId": version,
        "ETag": f'"{etag}"',
        "ContentLength": len(raw),
        "LastModified": modified,
        "ChecksumSHA256": checksum_value,
        "ChecksumType": "FULL_OBJECT",
        "ServerSideEncryption": encryption,
        "Metadata": {},
    }
    return row, head


def multipart_artifact(
    raw: bytes,
    key: str,
    version: str,
    modified: str,
    encryption: str,
    *,
    algorithms: list[str],
    checksum_type: str,
    part_count: int = 3,
) -> tuple[dict, dict, dict | None]:
    if part_count < 2 or part_count > len(raw):
        raise ValueError("invalid fixture part count")
    base, remainder = divmod(len(raw), part_count)
    sizes = [base + (1 if index < remainder else 0) for index in range(part_count)]
    parts: list[bytes] = []
    offset = 0
    for size in sizes:
        parts.append(raw[offset : offset + size])
        offset += size
    etag_digest = hashlib.md5(
        b"".join(
            hashlib.md5(part, usedforsecurity=False).digest() for part in parts
        ),
        usedforsecurity=False,
    ).hexdigest()
    etag = f"{etag_digest}-{part_count}"
    object_checksums: dict[str, str] = {}
    part_records: list[dict] = [
        {"PartNumber": index + 1, "Size": len(part)}
        for index, part in enumerate(parts)
    ]
    for algorithm in algorithms:
        field = S3_CHECKSUM_FIELDS[algorithm]
        if checksum_type == "FULL_OBJECT":
            object_checksums[field] = checksum_bytes_base64(raw, algorithm)
            continue
        encoded_parts = []
        for record, part in zip(part_records, parts, strict=True):
            encoded = checksum_bytes_base64(part, algorithm)
            record[field] = encoded
            encoded_parts.append(base64.b64decode(encoded))
        object_checksums[field] = (
            checksum_bytes_base64(b"".join(encoded_parts), algorithm)
            + f"-{part_count}"
        )
    row = {
        "Key": key,
        "VersionId": version,
        "IsLatest": True,
        "ETag": f'"{etag}"',
        "Size": len(raw),
        "LastModified": modified,
        "ChecksumAlgorithm": algorithms,
        "ChecksumType": checksum_type,
    }
    head = {
        "VersionId": version,
        "ETag": f'"{etag}"',
        "ContentLength": len(raw),
        "LastModified": modified,
        **object_checksums,
        "ChecksumType": checksum_type,
        "ServerSideEncryption": encryption,
        "Metadata": {},
    }
    attributes = None
    if checksum_type == "COMPOSITE":
        attributes = {
            "VersionId": version,
            "ETag": etag,
            "ObjectSize": len(raw),
            "LastModified": modified,
            "Checksum": {**object_checksums, "ChecksumType": checksum_type},
            "ObjectParts": {
                "TotalPartsCount": part_count,
                "PartNumberMarker": 0,
                "IsTruncated": False,
                "Parts": part_records,
            },
        }
    return row, head, attributes


def listing(row: dict) -> dict:
    return {"IsTruncated": False, "Versions": [copy.deepcopy(row)], "DeleteMarkers": []}


def transitions() -> list[dict]:
    times = [
        ("Starting", "09:59:59", "10:00:30"),
        ("Pending", "10:00:30", "10:01:00"),
        ("Downloading", "10:01:00", "10:02:00"),
        ("Training", "10:02:00", "10:29:00"),
        ("Uploading", "10:29:00", "10:29:59"),
        ("Completed", "10:29:59", "10:30:00"),
    ]
    return [
        {
            "Status": status,
            "StartTime": f"2026-07-28T{start}Z",
            "EndTime": f"2026-07-28T{end}Z",
            "StatusMessage": status,
        }
        for status, start, end in times
    ]


def make_case(tmp_path: Path) -> dict:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    answer_raw = b'{"task_id":"t1","expected_skill":"alpha"}\n'
    tasks_raw = b'{"task_id":"t1","prompt":"do alpha","option_map":[]}\n'
    catalog_raw = json_bytes(
        {
            "count": 1,
            "names": ["alpha"],
            "entries": [{"name": "alpha", "description": "alpha work"}],
        }
    )
    benchmark_raw = json_bytes(
        {
            "artifacts": {
                "tasks.jsonl": {"sha256": sha256_bytes(tasks_raw)},
                "answer_key.jsonl": {"sha256": sha256_bytes(answer_raw)},
                "registry_catalog.json": {"sha256": sha256_bytes(catalog_raw)},
            }
        }
    )
    config = {
        "experiment_id": "px062-g22-fixture",
        "protocol_version": "2.2.0",
        "status": "FROZEN_PREREGISTERED",
        "models": ["model-a", "model-b"],
        "model_revisions": {"model-a": "rev-a", "model-b": "rev-b"},
        "dependency_versions": {
            "torch": "2.3.0",
            "transformers": "4.46.3",
            "accelerate": "1.1.1",
            "jinja2": "3.1.4",
            "numpy": "1.26.4",
            "protobuf": "5.28.3",
            "safetensors": "0.4.5",
            "sentencepiece": "0.2.0",
        },
        "require_cuda": True,
        "expected_tasks": 1,
        "expected_traces": 2,
        "frozen_inputs": {
            "tasks": TASKS_PATH,
            "answer_key": ANSWER_KEY_PATH,
            "registry_catalog": CATALOG_PATH,
            "benchmark_manifest": BENCHMARK_MANIFEST_PATH,
        },
        "source_integrity": {
            "tasks_sha256": sha256_bytes(tasks_raw),
            "answer_key_sha256": sha256_bytes(answer_raw),
            "registry_catalog_sha256": sha256_bytes(catalog_raw),
            "benchmark_manifest_sha256": sha256_bytes(benchmark_raw),
        },
    }
    config_raw = json_bytes(config)
    source_files = {
        CONFIG_PATH: config_raw,
        TASKS_PATH: tasks_raw,
        CATALOG_PATH: catalog_raw,
        BENCHMARK_MANIFEST_PATH: benchmark_raw,
        COLLECTOR_PATH: b"collector\n",
        ENTRYPOINT_PATH: b"entrypoint\n",
        "requirements.txt": b"numpy==1.26.4\ntransformers==4.46.3\n",
    }
    source_manifest = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "source_commit": SOURCE_COMMIT,
        "answer_key_blinding": {
            "included_in_archive": False,
            "registered_sha256": sha256_bytes(answer_raw),
            "registered_bytes": len(answer_raw),
        },
        "files": {
            name: {"sha256": sha256_bytes(raw), "bytes": len(raw)}
            for name, raw in sorted(source_files.items())
        },
    }
    source_files["bundle_manifest.json"] = json_bytes(source_manifest)
    source_archive = make_tar(source_files)
    source_row, source_head = artifact(
        source_archive, SOURCE_KEY, "source-version", SOURCE_TIME, "AES256"
    )
    source_head["Metadata"] = {"sha256": sha256_bytes(source_archive)}

    summary = {
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "models": config["models"],
        "model_revisions": config["model_revisions"],
        "expected_tasks": 1,
        "expected_traces": 2,
        "observed_traces": 2,
        "generation_calls": 6,
        "constrained_decoder_escapes": 0,
        "source_integrity": {
            "config_sha256": sha256_bytes(config_raw),
            "tasks_sha256": sha256_bytes(tasks_raw),
            "registry_catalog_sha256": sha256_bytes(catalog_raw),
            "benchmark_manifest_sha256": sha256_bytes(benchmark_raw),
        },
        "environment": {
            **config["dependency_versions"],
            "cuda_available": True,
        },
        "collector_pid": 42,
    }
    tokenizer_manifest = {
        "schema_version": "px062-gate2.2-tokenizer-artifacts-v1",
        "decode_contract": {
            "skip_special_tokens": True,
            "clean_up_tokenization_spaces": False,
            "completion_token_ids_include_special_tokens": True,
            "empty_generated_token_ids_allowed": False,
        },
        "models": {},
    }
    tokenizer_manifest_raw = compact_json_bytes(tokenizer_manifest)
    tokenizer_raw = make_tar({"tokenizer_manifest.json": tokenizer_manifest_raw})
    summary["tokenizer_artifacts"] = {
        "path": "tokenizer_artifacts.tar.gz",
        "sha256": sha256_bytes(tokenizer_raw),
        "bytes": len(tokenizer_raw),
        "manifest_sha256": sha256_bytes(tokenizer_manifest_raw),
        "manifest": tokenizer_manifest,
    }
    trace_rows = []
    for model_id in config["models"]:
        trace_rows.append(
            {
                "model_id": model_id,
                "task_id": "t1",
                "arms": {
                    "A_open_text": {"generated": True},
                    "B_structured_names": {
                        "generated": True,
                        "decoder_escape": False,
                    },
                    "C_structured_catalog": {
                        "generated": True,
                        "decoder_escape": False,
                    },
                    "D_contextual_repair": {
                        "generated": False,
                        "decoder_escape": False,
                    },
                    "E_decontextualized_repair": {
                        "generated": False,
                        "decoder_escape": False,
                    },
                },
            }
        )
    trace_raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in trace_rows)
    output_files = {
        "px062_gate2_2/frozen_config.json": config_raw,
        "px062_gate2_2/source_bundle_manifest.json": json_bytes(source_manifest),
        "px062_gate2_2/collection_summary.json": json_bytes(summary),
        "px062_gate2_2/model_traces.jsonl": trace_raw,
        "px062_gate2_2/tokenizer_artifacts.tar.gz": tokenizer_raw,
    }
    output_archive = make_tar(output_files, directories=("px062_gate2_2",))
    output_row, output_head = artifact(
        output_archive, OUTPUT_KEY, "output-version", OUTPUT_TIME, "aws:kms"
    )

    request = {
        "TrainingJobName": JOB,
        "AlgorithmSpecification": {
            "TrainingImage": "example.invalid/image@sha256:" + "a" * 64,
            "TrainingInputMode": "File",
        },
        "RoleArn": "arn:aws:iam::123456789012:role/test",
        "OutputDataConfig": {"S3OutputPath": f"s3://{BUCKET}/{OUTPUT_PREFIX}"},
        "ResourceConfig": {
            "InstanceType": "ml.g5.2xlarge",
            "InstanceCount": 1,
            "VolumeSizeInGB": 200,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": 86400},
        "HyperParameters": {
            "sagemaker_program": ENTRYPOINT_PATH,
            "sagemaker_submit_directory": f"s3://{BUCKET}/{SOURCE_KEY}",
            "sagemaker_container_log_level": "20",
            "sagemaker_region": "us-east-1",
        },
        "Environment": {
            "PX062_GATE22_CONFIG": CONFIG_PATH,
            "HF_HOME": "/opt/ml/input/data/huggingface",
            "TOKENIZERS_PARALLELISM": "false",
        },
        "EnableNetworkIsolation": False,
        "RetryStrategy": {"MaximumRetryAttempts": 0},
        "Tags": [
            {"Key": "praxis-experiment", "Value": "PX-062-Gate-2.2"},
            {"Key": "praxis-one-look", "Value": "confirmatory"},
        ],
    }
    request_raw = json_bytes(request)
    checksum_requirements_raw = b"xxhash==3.8.1\n"
    operator_policy_raw = (
        Path(__file__).resolve().parents[1] / OPERATOR_FETCH_POLICY_PATH
    ).read_bytes().replace(
        b"praxis-garypagan-272615233626-us-east-1", BUCKET.encode("ascii")
    )
    evidence_raw = {
        path: (
            source_files[COLLECTOR_PATH]
            if label == "collector"
            else checksum_requirements_raw
            if label == "checksum_requirements"
            else operator_policy_raw
            if label == "operator_fetch_policy"
            else f"{label}\n".encode()
        )
        for label, path in FROZEN_EVIDENCE_CONTRACT.items()
    }
    launch = {
        "schema_version": "px062-gate2.2-launch-registration-v1",
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "registered_at_utc": "2026-07-28T09:46:00Z",
        "branch": "agent/test",
        "region": "us-east-1",
        "job_name": JOB,
        "initial_job_absence": {
            "method": "DescribeTrainingJob",
            "job_name": JOB,
            "result": "ResourceNotFound",
            "authorized_initial_absence": True,
        },
        "source_commit": SOURCE_COMMIT,
        "source_remote_refs": ["origin/agent/test"],
        "request_file": "manifests/px062_gate2_2_20260728/confirmatory_request.json",
        "request_sha256": sha256_bytes(request_raw),
        "source_bundle": {
            "bucket": BUCKET,
            "key": SOURCE_KEY,
            "version_id": source_row["VersionId"],
            "etag": source_row["ETag"].strip('"'),
            "sha256": sha256_bytes(source_archive),
            "checksum_sha256_base64": checksum(source_archive),
            "bytes": len(source_archive),
            "last_modified": SOURCE_TIME,
            "manifest": source_manifest,
        },
        "frozen_sources": {
            "config_sha256": sha256_bytes(config_raw),
            **config["source_integrity"],
        },
        "frozen_evidence": {
            label: {
                "path": path,
                "sha256": sha256_bytes(evidence_raw[path]),
                "bytes": len(evidence_raw[path]),
                "included_in_collection_source_bundle": path in source_manifest["files"],
            }
            for label, path in FROZEN_EVIDENCE_CONTRACT.items()
        },
        "checksum_runtime": checksum_runtime_record(checksum_requirements_raw),
        "fetch_operator_policy": operator_fetch_policy_record(
            operator_policy_raw, BUCKET
        ),
        "operator_access_preflight": {
            "source_version_attributes": {
                "method": "GetObjectAttributes",
                "version_id": source_row["VersionId"],
                "etag": source_row["ETag"].strip('"'),
                "bytes": len(source_archive),
                "checksum_sha256_base64": checksum(source_archive),
                "checksum_type": "FULL_OBJECT",
                "authorized": True,
            },
            "output_version_listing": {
                "method": "ListObjectVersions",
                "prefix": f"{PX062_GATE22_PREFIX}/output/{JOB}/",
                "authorized": True,
                "existing_versions": 0,
                "existing_delete_markers": 0,
            },
        },
        "frozen_collection": {
            "tasks": 1,
            "traces": 2,
            "models": config["models"],
            "arms": ["A", "B", "C", "D", "E"],
            "instance_type": "ml.g5.2xlarge",
            "max_runtime_seconds": 86400,
            "container_image": request["AlgorithmSpecification"]["TrainingImage"],
        },
        "role_arn": request["RoleArn"],
        "output_prefix": request["OutputDataConfig"]["S3OutputPath"],
        "one_look": {
            "allowed_training_job_creations": 1,
            "threshold_prompt_parser_or_label_changes_after_launch": 0,
            "answer_key_in_source_bundle": False,
        },
    }
    launch_path = write(
        root,
        "manifests/px062_gate2_2_20260728/confirmatory_registration.json",
        json_bytes(launch),
    )
    request_path = write(root, launch["request_file"], request_raw)
    receipt = {
        "schema_version": "px062-gate2.2-launch-receipt-v1",
        "experiment_id": config["experiment_id"],
        "protocol_version": config["protocol_version"],
        "launch_commit": "6" * 40,
        "launch_remote_refs": ["origin/agent/test"],
        "registration_path": launch_path.relative_to(root).as_posix(),
        "registration_sha256": sha256_bytes(launch_path.read_bytes()),
        "request_sha256": sha256_bytes(request_raw),
        "launched_at_utc": "2026-07-28T09:59:58Z",
        "receipt_recorded_at_utc": "2026-07-28T10:00:01Z",
        "launch_mode": "CREATE_ACCEPTED",
        "training_job_name": JOB,
        "training_job_arn": ARN,
        "status_at_receipt": "InProgress",
        "secondary_status_at_receipt": "Pending",
        "source_version_id": source_row["VersionId"],
        "source_sha256": sha256_bytes(source_archive),
        "create_response": {"TrainingJobArn": ARN},
        "interpretation": "Infrastructure state only.",
    }
    receipt_path = write(
        root,
        "manifests/px062_gate2_2_20260728/launch_receipt.json",
        json_bytes(receipt),
    )
    description = {
        "TrainingJobName": JOB,
        "TrainingJobArn": ARN,
        "ModelArtifacts": {"S3ModelArtifacts": f"s3://{BUCKET}/{OUTPUT_KEY}"},
        "TrainingJobStatus": "Completed",
        "SecondaryStatus": "Completed",
        "HyperParameters": request["HyperParameters"],
        "AlgorithmSpecification": {
            **request["AlgorithmSpecification"],
            "EnableSageMakerMetricsTimeSeries": False,
        },
        "RoleArn": request["RoleArn"],
        "InputDataConfig": [],
        "OutputDataConfig": {
            **request["OutputDataConfig"],
            "KmsKeyId": "",
            "CompressionType": "GZIP",
        },
        "ResourceConfig": request["ResourceConfig"],
        "StoppingCondition": request["StoppingCondition"],
        "CreationTime": CREATED,
        "TrainingStartTime": STARTED,
        "TrainingEndTime": ENDED,
        "LastModifiedTime": MODIFIED,
        "SecondaryStatusTransitions": transitions(),
        "EnableNetworkIsolation": False,
        "EnableInterContainerTrafficEncryption": False,
        "EnableManagedSpotTraining": False,
        "TrainingTimeInSeconds": 1680,
        "BillableTimeInSeconds": 1680,
        "ProfilingStatus": "Disabled",
        "Environment": request["Environment"],
        "RetryStrategy": request["RetryStrategy"],
    }
    tags = {"Tags": request["Tags"]}

    code_files = {
        REGISTRAR_PATH: b"registrar-code\n",
        FETCHER_PATH: b"fetcher-code\n",
        FETCH_TEST_PATH: b"fetch-tests\n",
    }
    for path, raw in code_files.items():
        write(root, path, raw)
    git_sources = {
        CONFIG_PATH: config_raw,
        TASKS_PATH: tasks_raw,
        CATALOG_PATH: catalog_raw,
        BENCHMARK_MANIFEST_PATH: benchmark_raw,
        COLLECTOR_PATH: source_files[COLLECTOR_PATH],
        ENTRYPOINT_PATH: source_files[ENTRYPOINT_PATH],
        REQUIREMENTS_GIT_PATH: source_files["requirements.txt"],
        ANSWER_KEY_PATH: answer_raw,
    }
    blobs: dict[tuple[str, str], bytes] = {}
    for path in [launch_path, request_path, receipt_path]:
        blobs[(FETCH_COMMIT, path.relative_to(root).as_posix())] = path.read_bytes()
    for path, raw in code_files.items():
        blobs[(FETCH_COMMIT, path)] = raw
    for path, raw in git_sources.items():
        blobs[(SOURCE_COMMIT, path)] = raw
    for path, raw in evidence_raw.items():
        blobs[(SOURCE_COMMIT, path)] = raw
    state = {
        "head": FETCH_COMMIT,
        "branch": "agent/test",
        "clean": True,
        "remote_refs": ["origin/agent/test"],
    }
    calls: list[tuple[str, ...]] = []
    list_counts = {SOURCE_KEY: 0, OUTPUT_KEY: 0}
    attribute_counts = {SOURCE_KEY: 0, OUTPUT_KEY: 0}
    attributes = {SOURCE_KEY: None, OUTPUT_KEY: None}
    mutations: dict[object, object] = {}

    def fake_aws(_profile: str, _region: str, *args: str):
        calls.append(args)
        if args[:2] == ("sagemaker", "describe-training-job"):
            return mutations.get("description", description)
        if args[:2] == ("sagemaker", "list-tags"):
            return mutations.get("tags", tags)
        if args[:2] == ("s3api", "list-object-versions"):
            key = args[args.index("--prefix") + 1]
            list_counts[key] += 1
            base = listing(source_row if key == SOURCE_KEY else output_row)
            return mutations.get(("listing", key, list_counts[key]), base)
        if args[:2] == ("s3api", "head-object"):
            key = args[args.index("--key") + 1]
            base = source_head if key == SOURCE_KEY else output_head
            return mutations.get(("head", key), base)
        if args[:2] == ("s3api", "get-object-attributes"):
            key = args[args.index("--key") + 1]
            attribute_counts[key] += 1
            base = attributes[key]
            if base is None:
                raise AssertionError(f"unexpected object attributes call: {key}")
            return mutations.get(
                ("attributes", key, attribute_counts[key]), base
            )
        raise AssertionError(f"unexpected AWS call: {args}")

    archives = {SOURCE_KEY: source_archive, OUTPUT_KEY: output_archive}
    heads = {SOURCE_KEY: source_head, OUTPUT_KEY: output_head}

    def fake_download(
        _profile: str,
        _region: str,
        _bucket: str,
        key: str,
        version_id: str,
        destination: Path,
    ):
        calls.append(("download", key, version_id))
        raw = mutations.get(("archive", key), archives[key])
        destination.write_bytes(raw)
        return mutations.get(("download_response", key), heads[key])

    def fake_blob(_root: Path, revision: str, path: str) -> bytes:
        value = mutations.get(("blob", revision, path))
        return value if isinstance(value, bytes) else blobs[(revision, path)]

    def fake_state(_root: Path):
        return mutations.get("state", state)

    completion_path = root / "manifests/px062_gate2_2_20260728/completion_registration.json"
    destination_parent = root / DEFAULT_DESTINATION.parent
    destination_parent.mkdir(parents=True, exist_ok=True)
    case = {
        "root": root,
        "launch_path": launch_path,
        "receipt_path": receipt_path,
        "completion_path": completion_path,
        "destination": root / DEFAULT_DESTINATION,
        "fake_aws": fake_aws,
        "fake_download": fake_download,
        "fake_blob": fake_blob,
        "fake_state": fake_state,
        "mutations": mutations,
        "calls": calls,
        "list_counts": list_counts,
        "attribute_counts": attribute_counts,
        "attributes": attributes,
        "blobs": blobs,
        "state": state,
        "description": description,
        "tags": tags,
        "source_row": source_row,
        "source_head": source_head,
        "output_row": output_row,
        "output_head": output_head,
        "source_files": source_files,
        "source_manifest": source_manifest,
        "source_archive": source_archive,
        "output_files": output_files,
        "output_archive": output_archive,
        "trace_raw": trace_raw,
        "answer_raw": answer_raw,
    }
    return case


def configure_output_s3_contract(
    case: dict,
    *,
    algorithms: list[str],
    checksum_type: str,
    part_count: int = 3,
    head_only: bool = False,
) -> tuple[dict, dict, dict | None]:
    row, head, attributes = multipart_artifact(
        case["output_archive"],
        OUTPUT_KEY,
        "output-version",
        OUTPUT_TIME,
        "aws:kms",
        algorithms=algorithms,
        checksum_type=checksum_type,
        part_count=part_count,
    )
    if head_only:
        row.pop("ChecksumAlgorithm")
        row.pop("ChecksumType")
    case["output_row"].clear()
    case["output_row"].update(row)
    case["output_head"].clear()
    case["output_head"].update(head)
    case["attributes"][OUTPUT_KEY] = attributes
    return row, head, attributes


def register(case: dict) -> dict:
    return register_completion(
        root=case["root"],
        profile="test",
        launch_path=case["launch_path"],
        receipt_path=case["receipt_path"],
        completion_path=case["completion_path"],
        aws_call=case["fake_aws"],
        blob_reader=case["fake_blob"],
        state_reader=case["fake_state"],
        registered_at=REGISTERED,
    )


def prepare_fetch(case: dict) -> dict:
    completion = register(case)
    case["blobs"][(FETCH_COMMIT, case["completion_path"].relative_to(case["root"]).as_posix())] = (
        case["completion_path"].read_bytes()
    )
    case["calls"].clear()
    case["list_counts"][SOURCE_KEY] = 0
    case["list_counts"][OUTPUT_KEY] = 0
    case["attribute_counts"][SOURCE_KEY] = 0
    case["attribute_counts"][OUTPUT_KEY] = 0
    return completion


def rewrite_completion(case: dict, mutate) -> dict:
    completion = json.loads(case["completion_path"].read_text())
    mutate(completion)
    case["completion_path"].write_bytes(json_bytes(completion))
    relative = case["completion_path"].relative_to(case["root"]).as_posix()
    case["blobs"][(FETCH_COMMIT, relative)] = case["completion_path"].read_bytes()
    return completion


def replace_registered_output(case: dict, row: dict, head: dict) -> dict:
    completion = json.loads(case["completion_path"].read_text())
    completion["output_artifact"] = registered_artifact(
        bucket=BUCKET,
        key=OUTPUT_KEY,
        row=row,
        head=head,
    )
    case["completion_path"].write_bytes(json_bytes(completion))
    relative = case["completion_path"].relative_to(case["root"]).as_posix()
    case["blobs"][(FETCH_COMMIT, relative)] = case["completion_path"].read_bytes()
    case["mutations"][("listing", OUTPUT_KEY, 1)] = listing(row)
    case["mutations"][("listing", OUTPUT_KEY, 2)] = listing(row)
    case["mutations"][("head", OUTPUT_KEY)] = head
    case["mutations"][("download_response", OUTPUT_KEY)] = head
    return completion


def fetch(case: dict) -> dict:
    source_bytes = case["mutations"].get(
        ("archive", SOURCE_KEY), case["source_archive"]
    )
    output_bytes = case["mutations"].get(
        ("archive", OUTPUT_KEY), case["output_archive"]
    )
    return fetch_and_seal(
        root=case["root"],
        profile="test",
        completion_path=case["completion_path"],
        destination=case["destination"],
        aws_call=case["fake_aws"],
        download_call=case["fake_download"],
        blob_reader=case["fake_blob"],
        state_reader=case["fake_state"],
        fetched_at=FETCHED,
        source_compressed_ceiling=len(source_bytes) + 1,
        output_compressed_ceiling=len(output_bytes) + 1,
    )


def test_completion_registration_is_metadata_only_and_output_blind(tmp_path):
    case = make_case(tmp_path)
    result = register(case)
    assert result["job"]["status"] == "Completed"
    assert result["scientific_outputs_downloaded"] is False
    assert result["scientific_outputs_inspected"] is False
    assert "sha256" not in result["output_artifact"]
    assert result["answer_key"]["included_in_cloud_source"] is False
    assert not any(call and call[0] == "download" for call in case["calls"])
    assert not any(call[:2] == ("s3api", "get-object") for call in case["calls"])


def test_crc_reference_vectors_match_s3_wire_encoding():
    raw = b"123456789"
    assert checksum_bytes_base64(raw, "CRC32C") == base64.b64encode(
        bytes.fromhex("e3069283")
    ).decode()
    assert checksum_bytes_base64(raw, "CRC64NVME") == base64.b64encode(
        bytes.fromhex("ae8b14860a799888")
    ).decode()


def test_multipart_crc64_full_object_is_locally_verified_without_etag_md5(tmp_path):
    case = make_case(tmp_path)
    configure_output_s3_contract(
        case, algorithms=["CRC64NVME"], checksum_type="FULL_OBJECT"
    )
    completion = prepare_fetch(case)
    receipt = fetch(case)
    output = receipt["output_artifact"]
    assert completion["output_artifact"]["etag_shape"] == "MULTIPART"
    assert output["md5"] != output["etag"].split("-", 1)[0]
    assert output["checksum_verification"]["method"] == (
        "LOCAL_FULL_OBJECT_RECOMPUTATION"
    )
    assert output["checksum_verification"]["algorithms"]["CRC64NVME"][
        "local_value"
    ] == output["checksums"]["ChecksumCRC64NVME"]


@pytest.mark.parametrize(
    "algorithm",
    [
        "CRC32",
        "CRC32C",
        "SHA1",
        "SHA256",
        "MD5",
        "XXHASH64",
        "XXHASH3",
        "XXHASH128",
        "SHA512",
    ],
)
def test_every_supported_composite_checksum_is_part_aware_verified(
    tmp_path, algorithm
):
    case = make_case(tmp_path)
    configure_output_s3_contract(
        case, algorithms=[algorithm], checksum_type="COMPOSITE"
    )
    prepare_fetch(case)
    receipt = fetch(case)
    proof = receipt["output_artifact"]["checksum_verification"]
    assert proof["method"] == "LOCAL_PART_AWARE_COMPOSITE_RECOMPUTATION"
    assert proof["algorithms"][algorithm]["parts_recomputed"] == 3
    assert receipt["output_artifact"]["object_attributes_repeated"] is True
    assert case["attribute_counts"][OUTPUT_KEY] == 2


def test_multiple_head_checksums_and_head_only_negotiation_are_supported(tmp_path):
    case = make_case(tmp_path / "multiple")
    configure_output_s3_contract(
        case,
        algorithms=["CRC32C", "SHA256"],
        checksum_type="COMPOSITE",
    )
    prepare_fetch(case)
    receipt = fetch(case)
    assert receipt["output_artifact"]["checksum_algorithm"] == ["CRC32C", "SHA256"]

    case = make_case(tmp_path / "head-only")
    configure_output_s3_contract(
        case,
        algorithms=["CRC64NVME"],
        checksum_type="FULL_OBJECT",
        head_only=True,
    )
    completion = prepare_fetch(case)
    assert completion["output_artifact"]["checksum_algorithm"] == ["CRC64NVME"]
    assert completion["output_artifact"]["version_fingerprint"][
        "ChecksumAlgorithm"
    ] == []
    fetch(case)


@pytest.mark.parametrize(
    ("algorithm", "checksum_type"),
    [
        ("CRC64NVME", "COMPOSITE"),
        ("SHA256", "FULL_OBJECT"),
    ],
)
def test_registration_rejects_impossible_multipart_checksum_matrix(
    tmp_path, algorithm, checksum_type
):
    case = make_case(tmp_path)
    configure_output_s3_contract(
        case, algorithms=[algorithm], checksum_type=checksum_type
    )
    with pytest.raises(ValueError, match="inconsistent"):
        register(case)


@pytest.mark.parametrize("algorithm", ["XXHASH64", "XXHASH3", "XXHASH128", "SHA512"])
def test_single_part_put_object_supports_all_full_object_algorithms(
    tmp_path, algorithm
):
    case = make_case(tmp_path)
    row = case["output_row"]
    head = case["output_head"]
    row["ChecksumAlgorithm"] = [algorithm]
    row["ChecksumType"] = "FULL_OBJECT"
    head.pop("ChecksumSHA256")
    head[S3_CHECKSUM_FIELDS[algorithm]] = checksum_bytes_base64(
        case["output_archive"], algorithm
    )
    head["ChecksumType"] = "FULL_OBJECT"
    prepare_fetch(case)
    receipt = fetch(case)
    assert receipt["output_artifact"]["checksum_verification"]["algorithms"][
        algorithm
    ]["local_value"] == head[S3_CHECKSUM_FIELDS[algorithm]]


def test_registration_rejects_missing_substituted_or_malformed_checksums(tmp_path):
    case = make_case(tmp_path / "missing")
    case["output_head"].pop("ChecksumSHA256")
    with pytest.raises(ValueError, match="no supported checksum"):
        register(case)

    case = make_case(tmp_path / "substitution")
    case["output_head"].pop("ChecksumSHA256")
    case["output_head"]["ChecksumCRC64NVME"] = checksum_bytes_base64(
        case["output_archive"], "CRC64NVME"
    )
    with pytest.raises(ValueError, match="substitution"):
        register(case)

    case = make_case(tmp_path / "invalid-base64")
    case["output_head"]["ChecksumSHA256"] = "not-base64"
    with pytest.raises(ValueError, match="Base64|width"):
        register(case)

    case = make_case(tmp_path / "duplicate")
    case["output_row"]["ChecksumAlgorithm"] = ["SHA256", "SHA256"]
    with pytest.raises(ValueError, match="algorithm listing"):
        register(case)

    case = make_case(tmp_path / "single-composite")
    case["output_row"]["ChecksumType"] = "COMPOSITE"
    case["output_head"]["ChecksumType"] = "COMPOSITE"
    case["output_head"]["ChecksumSHA256"] += "-1"
    with pytest.raises(ValueError, match="single-part.*inconsistent"):
        register(case)

    case = make_case(tmp_path / "type-substitution")
    case["output_row"]["ChecksumType"] = "COMPOSITE"
    with pytest.raises(ValueError, match="type mismatch|inconsistent"):
        register(case)

    case = make_case(tmp_path / "unknown-field")
    case["output_head"]["ChecksumFuture"] = "opaque"
    with pytest.raises(ValueError, match="unsupported checksum fields"):
        register(case)


def test_composite_part_count_or_attributes_substitution_is_rejected(tmp_path):
    case = make_case(tmp_path / "suffix")
    configure_output_s3_contract(
        case, algorithms=["SHA256"], checksum_type="COMPOSITE"
    )
    case["output_head"]["ChecksumSHA256"] = case["output_head"][
        "ChecksumSHA256"
    ].rsplit("-", 1)[0] + "-2"
    with pytest.raises(ValueError, match="part count"):
        register(case)

    case = make_case(tmp_path / "attributes")
    configure_output_s3_contract(
        case, algorithms=["SHA256"], checksum_type="COMPOSITE"
    )
    attributes = copy.deepcopy(case["attributes"][OUTPUT_KEY])
    attributes["ObjectParts"]["Parts"][0]["ChecksumSHA256"] = checksum_bytes_base64(
        b"substituted", "SHA256"
    )
    case["attributes"][OUTPUT_KEY] = attributes
    with pytest.raises(ValueError, match="part checksum|composite"):
        register(case)


def test_same_size_crc64_download_corruption_is_rejected(tmp_path):
    case = make_case(tmp_path)
    configure_output_s3_contract(
        case, algorithms=["CRC64NVME"], checksum_type="FULL_OBJECT"
    )
    prepare_fetch(case)
    damaged = bytearray(case["output_archive"])
    damaged[len(damaged) // 2] ^= 1
    case["mutations"][("archive", OUTPUT_KEY)] = bytes(damaged)
    with pytest.raises(ValueError, match="CRC64NVME checksum mismatch"):
        fetch(case)


def test_fetch_structurally_reconciles_traces_without_semantic_adjudication(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    receipt = fetch(case)
    assert receipt["model_trace_content_parsed"] is True
    assert receipt["model_trace_structure_validated"] is True
    assert receipt["trace_summary_reconciled"] is True
    assert receipt["scientific_outputs_inspected"] is False
    assert receipt["adjudication_run"] is False
    assert (case["destination"] / "model_traces.jsonl").read_bytes() == case["trace_raw"]
    assert (case["destination"] / "answer_key.jsonl").read_bytes() == case["answer_raw"]
    assert {path.name for path in case["destination"].iterdir()} == SEALED_FILES


def test_receipt_binds_every_sealed_input_and_remote_artifact(tmp_path):
    case = make_case(tmp_path)
    completion = prepare_fetch(case)
    receipt = fetch(case)
    assert receipt["source_artifact"]["version_id"] == "source-version"
    assert receipt["output_artifact"]["version_id"] == "output-version"
    assert receipt["source_artifact"]["version_listing_repeated"] is True
    assert receipt["output_artifact"]["version_listing_repeated"] is True
    for name, record in receipt["sealed_files"].items():
        raw = (case["destination"] / name).read_bytes()
        assert record == {"bytes": len(raw), "sha256": sha256_bytes(raw)}
    assert completion["output_artifact"]["checksums"] == receipt[
        "output_artifact"
    ]["checksums"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("checksum_algorithm", ["CRC32"]),
        ("checksum_type", "COMPOSITE"),
        ("server_side_encryption", "AES256"),
        ("version_fingerprint", {"forged": True}),
    ],
)
def test_receipt_rejects_registered_provenance_field_drift(tmp_path, field, value):
    case = make_case(tmp_path)
    completion = prepare_fetch(case)
    receipt = fetch(case)
    forged = copy.deepcopy(receipt)
    forged["output_artifact"][field] = value
    with pytest.raises(ValueError, match="drift"):
        validate_fetch_receipt_against_completion(
            forged, completion, case["completion_path"].read_bytes()
        )


def test_post_fetch_authorization_exclusively_binds_registered_provenance(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    receipt = fetch(case)
    authorization_path = case["root"] / DEFAULT_ADJUDICATION_AUTHORIZATION
    authorization = register_adjudication_authorization(
        root=case["root"],
        fetch_receipt_path=case["destination"] / "completion_fetch_receipt.json",
        completion_path=case["completion_path"],
        authorization_path=authorization_path,
        blob_reader=case["fake_blob"],
        state_reader=case["fake_state"],
        authorized_at=FETCHED,
    )
    assert authorization["fetch_receipt"]["sha256"] == sha256_bytes(
        (case["destination"] / "completion_fetch_receipt.json").read_bytes()
    )
    assert authorization["output_artifact"] == receipt["output_artifact"]
    assert authorization["one_look"]["allowed_adjudications"] == 1
    provenance = verify_adjudication_provenance(
        root=case["root"],
        authorization_path=authorization_path,
        authorization=authorization,
        inputs={
            name: case["destination"] / name
            for name in receipt["sealed_files"]
        },
        blob_reader=case["fake_blob"],
        state_reader=case["fake_state"],
    )
    assert provenance["cloud_archives"][
        "sealed_outcomes_match_registered_archive"
    ] is True
    with pytest.raises(FileExistsError, match="already exists"):
        register_adjudication_authorization(
            root=case["root"],
            fetch_receipt_path=case["destination"] / "completion_fetch_receipt.json",
            completion_path=case["completion_path"],
            authorization_path=authorization_path,
            blob_reader=case["fake_blob"],
            state_reader=case["fake_state"],
        )


def test_authorization_rejects_post_fetch_archive_mutation(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    fetch(case)
    (case["destination"] / "output_artifact.tar.gz").write_bytes(b"forged\n")
    with pytest.raises(ValueError, match="sealed payload differs"):
        register_adjudication_authorization(
            root=case["root"],
            fetch_receipt_path=case["destination"] / "completion_fetch_receipt.json",
            completion_path=case["completion_path"],
            authorization_path=case["root"] / DEFAULT_ADJUDICATION_AUTHORIZATION,
            blob_reader=case["fake_blob"],
            state_reader=case["fake_state"],
        )


@pytest.mark.parametrize("status", ["InProgress", "Failed", "Stopped"])
def test_registration_requires_completed_job(tmp_path, status):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description["TrainingJobStatus"] = status
    case["mutations"]["description"] = description
    with pytest.raises(ValueError, match="not Completed"):
        register(case)


@pytest.mark.parametrize("kind", ["multiple", "delete", "null", "not-latest"])
def test_registration_requires_one_immutable_output_version(tmp_path, kind):
    case = make_case(tmp_path)
    value = listing(case["output_row"])
    if kind == "multiple":
        value["Versions"].append(copy.deepcopy(case["output_row"]))
    elif kind == "delete":
        value["DeleteMarkers"] = [{"Key": OUTPUT_KEY, "VersionId": "deleted"}]
    elif kind == "null":
        value["Versions"][0]["VersionId"] = "null"
    else:
        value["Versions"][0]["IsLatest"] = False
    case["mutations"][("listing", OUTPUT_KEY, 1)] = value
    with pytest.raises(ValueError):
        register(case)


def test_registration_rejects_live_request_or_tag_drift(tmp_path):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description["ResourceConfig"]["VolumeSizeInGB"] = 201
    case["mutations"]["description"] = description
    with pytest.raises(ValueError, match="ResourceConfig"):
        register(case)


def test_registration_rejects_closed_world_job_or_receipt_schema_drift(tmp_path):
    case = make_case(tmp_path)
    description = copy.deepcopy(case["description"])
    description["VpcConfig"] = {"SecurityGroupIds": ["sg-x"]}
    case["mutations"]["description"] = description
    with pytest.raises(ValueError, match="description schema drift"):
        register(case)

    case = make_case(tmp_path / "receipt")
    receipt = json.loads(case["receipt_path"].read_text())
    receipt["unexpected"] = True
    case["receipt_path"].write_bytes(json_bytes(receipt))
    relative = case["receipt_path"].relative_to(case["root"]).as_posix()
    case["blobs"][(FETCH_COMMIT, relative)] = case["receipt_path"].read_bytes()
    with pytest.raises(ValueError, match="receipt schema"):
        register(case)

    case = make_case(tmp_path / "tags")
    case["mutations"]["tags"] = {"Tags": []}
    with pytest.raises(ValueError, match="tags differ"):
        register(case)


def test_registration_rejects_output_timestamp_outside_job(tmp_path):
    case = make_case(tmp_path)
    row = copy.deepcopy(case["output_row"])
    head = copy.deepcopy(case["output_head"])
    row["LastModified"] = "2026-07-28T10:31:00Z"
    head["LastModified"] = "2026-07-28T10:31:00Z"
    case["mutations"][("listing", OUTPUT_KEY, 1)] = listing(row)
    case["mutations"][("head", OUTPUT_KEY)] = head
    with pytest.raises(ValueError, match="postdates"):
        register(case)


def test_registration_rejects_source_commit_answer_key_mismatch(tmp_path):
    case = make_case(tmp_path)
    case["mutations"][("blob", SOURCE_COMMIT, ANSWER_KEY_PATH)] = b"changed\n"
    with pytest.raises(ValueError, match="answer key"):
        register(case)


def test_registration_rejects_governance_evidence_binding_drift(tmp_path):
    governance_labels = tuple(
        label for label in FROZEN_EVIDENCE_CONTRACT if label != "collector"
    )
    for index, label in enumerate(governance_labels):
        case = make_case(tmp_path / str(index))
        path = FROZEN_EVIDENCE_CONTRACT[label]
        case["mutations"][("blob", SOURCE_COMMIT, path)] = b"mutated\n"
        with pytest.raises(
            ValueError,
            match="frozen-evidence binding|checksum requirements|operator fetch policy|invalid UTF-8 JSON",
        ):
            register(case)


def test_existing_destination_fails_before_aws_or_download(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    case["destination"].mkdir()
    case["calls"].clear()
    with pytest.raises(FileExistsError):
        fetch(case)
    assert case["calls"] == []


@pytest.mark.parametrize(
    "state_change",
    [
        {"clean": False},
        {"remote_refs": []},
        {"head": "not-a-commit"},
    ],
)
def test_fetch_requires_clean_pushed_commit(tmp_path, state_change):
    case = make_case(tmp_path)
    prepare_fetch(case)
    case["mutations"]["state"] = {**case["state"], **state_change}
    with pytest.raises(ValueError):
        fetch(case)


def test_fetch_requires_registered_branch_and_answer_source_binding(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    case["mutations"]["state"] = {**case["state"], "branch": "agent/other"}
    with pytest.raises(ValueError, match="branch"):
        fetch(case)

    case = make_case(tmp_path / "answer")
    prepare_fetch(case)
    rewrite_completion(
        case,
        lambda completion: completion["answer_key"].update(
            {"source_commit": "9" * 40}
        ),
    )
    with pytest.raises(ValueError, match="source commit"):
        fetch(case)


def test_fetch_rejects_registered_source_identity_or_encryption_drift(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    rewrite_completion(
        case,
        lambda completion: completion["source_artifact"].update(
            {"key": "different/source.tar.gz"}
        ),
    )
    with pytest.raises(ValueError, match="source artifact.*drift"):
        fetch(case)

    case = make_case(tmp_path / "encryption")
    prepare_fetch(case)
    head = copy.deepcopy(case["output_head"])
    head["ServerSideEncryption"] = "AES256"
    case["mutations"][("head", OUTPUT_KEY)] = head
    with pytest.raises(ValueError, match="HeadObject fingerprint"):
        fetch(case)


def test_completion_and_fetch_timestamps_are_monotonic(tmp_path):
    case = make_case(tmp_path)
    with pytest.raises(ValueError, match="predates completed job"):
        register_completion(
            root=case["root"],
            profile="test",
            launch_path=case["launch_path"],
            receipt_path=case["receipt_path"],
            completion_path=case["completion_path"],
            aws_call=case["fake_aws"],
            blob_reader=case["fake_blob"],
            state_reader=case["fake_state"],
            registered_at=datetime(2026, 7, 28, 10, 29, tzinfo=timezone.utc),
        )

    case = make_case(tmp_path / "fetch")
    prepare_fetch(case)
    with pytest.raises(ValueError, match="predates completion registration"):
        fetch_and_seal(
            root=case["root"],
            profile="test",
            completion_path=case["completion_path"],
            destination=case["destination"],
            aws_call=case["fake_aws"],
            download_call=case["fake_download"],
            blob_reader=case["fake_blob"],
            state_reader=case["fake_state"],
            fetched_at=datetime(2026, 7, 28, 10, 30, tzinfo=timezone.utc),
            source_compressed_ceiling=len(case["source_archive"]) + 1,
            output_compressed_ceiling=len(case["output_archive"]) + 1,
        )


def test_fetch_rejects_fetcher_hash_or_committed_registration_drift(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    (case["root"] / FETCHER_PATH).write_bytes(b"changed\n")
    case["blobs"][(FETCH_COMMIT, FETCHER_PATH)] = b"changed\n"
    with pytest.raises(ValueError, match="hash mismatch"):
        fetch(case)

    case = make_case(tmp_path / "registration")
    prepare_fetch(case)
    case["blobs"][(FETCH_COMMIT, case["completion_path"].relative_to(case["root"]).as_posix())] = b"different\n"
    with pytest.raises(ValueError, match="pushed HEAD"):
        fetch(case)


@pytest.mark.parametrize("key", [SOURCE_KEY, OUTPUT_KEY])
def test_fetch_repeats_version_listing_and_rejects_change(tmp_path, key):
    case = make_case(tmp_path)
    prepare_fetch(case)
    row = copy.deepcopy(case["source_row"] if key == SOURCE_KEY else case["output_row"])
    changed = listing(row)
    changed["DeleteMarkers"] = [{"Key": key, "VersionId": "late-delete"}]
    case["mutations"][("listing", key, 2)] = changed
    with pytest.raises(ValueError):
        fetch(case)


def test_fetch_rejects_downloaded_bytes_or_checksum_response_drift(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    case["mutations"][("archive", SOURCE_KEY)] = case["source_archive"] + b"x"
    with pytest.raises(ValueError, match="size mismatch"):
        fetch(case)

    case = make_case(tmp_path / "checksum")
    prepare_fetch(case)
    response = copy.deepcopy(case["output_head"])
    response["ChecksumSHA256"] = "wrong"
    case["mutations"][("download_response", OUTPUT_KEY)] = response
    with pytest.raises(ValueError, match="registered fingerprint"):
        fetch(case)


@pytest.mark.parametrize(
    "extra",
    [
        ("unexpected.txt", b"x", "file", ""),
        ("../escape", b"", "symlink", "target"),
        ("px062_gate2_2/link", b"", "symlink", "target"),
    ],
)
def test_output_archive_rejects_extra_unsafe_or_link_member(tmp_path, extra):
    case = make_case(tmp_path)
    prepare_fetch(case)
    bad = make_tar(
        case["output_files"], directories=("px062_gate2_2",), extra=extra
    )
    case["mutations"][("archive", OUTPUT_KEY)] = bad
    # Keep the registered object response coherent through download validation;
    # the closed-world tar validator must be the rejecting layer.
    head = copy.deepcopy(case["output_head"])
    head.update(
        {
            "ContentLength": len(bad),
            "ETag": f'"{hashlib.md5(bad, usedforsecurity=False).hexdigest()}"',
            "ChecksumSHA256": checksum(bad),
        }
    )
    row = copy.deepcopy(case["output_row"])
    row.update(
        {"Size": len(bad), "ETag": head["ETag"], "ChecksumAlgorithm": ["SHA256"]}
    )
    replace_registered_output(case, row, head)
    with pytest.raises(ValueError, match="member set|unsafe|nonregular"):
        fetch(case)


def test_tar_member_and_total_size_ceilings_are_enforced():
    raw = make_tar({"trace": b"12345"})
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as handle:
        with pytest.raises(ValueError, match="member ceiling"):
            validate_tar(handle, {"trace": {"max_bytes": 4}}, 100, "fixture")
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as handle:
        with pytest.raises(ValueError, match="total uncompressed"):
            validate_tar(handle, {"trace": {"max_bytes": 10}}, 4, "fixture")
    assert OUTPUT_UNCOMPRESSED_MAX_BYTES >= 512 * 1024 * 1024


def test_trace_reconciliation_rejects_nonzero_escape_and_count_drift(tmp_path):
    row = {
        "model_id": "model-a",
        "task_id": "t1",
        "arms": {
            "A_open_text": {"generated": True},
            "B_structured_names": {"generated": True, "decoder_escape": True},
            "C_structured_catalog": {"generated": True, "decoder_escape": False},
            "D_contextual_repair": {"generated": False, "decoder_escape": False},
            "E_decontextualized_repair": {"generated": False, "decoder_escape": False},
        },
    }
    raw = json.dumps(row, separators=(",", ":")).encode() + b"\n"
    summary = {
        "observed_traces": 1,
        "expected_traces": 1,
        "models": ["model-a"],
        "expected_tasks": 1,
        "constrained_decoder_escapes": 0,
        "generation_calls": 3,
    }
    with pytest.raises(ValueError, match="decoder escapes"):
        copy_and_validate_traces(io.BytesIO(raw), tmp_path / "escape.jsonl", len(raw), summary)

    row["arms"]["B_structured_names"]["decoder_escape"] = False
    raw = json.dumps(row, separators=(",", ":")).encode() + b"\n"
    summary["generation_calls"] = 4
    with pytest.raises(ValueError, match="generation-call"):
        copy_and_validate_traces(io.BytesIO(raw), tmp_path / "count.jsonl", len(raw), summary)


def test_trace_reconciliation_rejects_duplicate_json_keys(tmp_path):
    raw = (
        b'{"model_id":"model-a","model_id":"model-b","task_id":"t1","arms":{}}\n'
    )
    summary = {
        "observed_traces": 1,
        "expected_traces": 1,
        "models": ["model-a"],
        "expected_tasks": 1,
        "constrained_decoder_escapes": 0,
        "generation_calls": 0,
    }
    with pytest.raises(ValueError, match="duplicate JSON key"):
        copy_and_validate_traces(io.BytesIO(raw), tmp_path / "duplicate.jsonl", len(raw), summary)


def test_source_archive_rejects_manifest_or_source_commit_drift(tmp_path):
    case = make_case(tmp_path)
    prepare_fetch(case)
    case["mutations"][("blob", SOURCE_COMMIT, COLLECTOR_PATH)] = b"different\n"
    with pytest.raises(ValueError, match="source commit"):
        fetch(case)


def test_output_archive_rejects_config_manifest_or_summary_drift(tmp_path):
    for index, member in enumerate(
        [
            "px062_gate2_2/frozen_config.json",
            "px062_gate2_2/source_bundle_manifest.json",
            "px062_gate2_2/collection_summary.json",
        ]
    ):
        case = make_case(tmp_path / str(index))
        prepare_fetch(case)
        files = dict(case["output_files"])
        files[member] = b"{}\n"
        bad = make_tar(files, directories=("px062_gate2_2",))
        case["mutations"][("archive", OUTPUT_KEY)] = bad
        head = copy.deepcopy(case["output_head"])
        head.update(
            {
                "ContentLength": len(bad),
                "ETag": f'"{hashlib.md5(bad, usedforsecurity=False).hexdigest()}"',
                "ChecksumSHA256": checksum(bad),
            }
        )
        row = copy.deepcopy(case["output_row"])
        row.update({"Size": len(bad), "ETag": head["ETag"]})
        replace_registered_output(case, row, head)
        with pytest.raises(ValueError):
            fetch(case)
