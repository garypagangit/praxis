import copy
import json
import subprocess
from pathlib import Path

import pytest

import scripts.launch_px062_gate2_2_registered as launch
import scripts.register_px062_gate2_2_launch as registrar
from scripts.register_px062_gate2_2_fetch import FROZEN_EVIDENCE_CONTRACT


def make_label_audit_manifest(root):
    artifact_path = root / "label_audits" / "slot-1.events.jsonl"
    artifact_path.parent.mkdir(parents=True)
    artifact_raw = b'{"type":"thread.started"}\n'
    artifact_path.write_bytes(artifact_raw)
    created_utc = "2026-07-28T14:00:00.000000Z"
    checkpoint = {
        "schema_version": "synthetic-checkpoint-v1",
        "head_commit": "a" * 40,
        "pending_answer_sha256": "b" * 64,
        "source_integrity": {"answer_key_sha256": "b" * 64},
        "config_sha256": "c" * 64,
    }
    sessions_1 = [f"slot-1-session-{index:02d}" for index in range(43)]
    sessions_2 = [f"slot-2-session-{index:02d}" for index in range(43)]
    manifest = {
        "schema_version": "px062-gate2.2-label-audit-evidence-manifest-v1",
        "created_utc": created_utc,
        "answer_key_contents_included": False,
        "pending_answer_checkpoint_hash_included": True,
        "repository_checkpoint": copy.deepcopy(checkpoint),
        "audits": [
            {
                "slot": 1,
                "model": "gpt-5.6-sol",
                "audit_id": "audit-slot-1",
                "accepted_session_ids": sessions_1,
                "prediction_sha256": "1" * 64,
                "sidecar_sha256": "2" * 64,
            },
            {
                "slot": 2,
                "model": "gpt-5.6-terra",
                "audit_id": "audit-slot-2",
                "accepted_session_ids": sessions_2,
                "prediction_sha256": "3" * 64,
                "sidecar_sha256": "4" * 64,
            },
        ],
        "global_session_ids": {
            "accepted_count": 86,
            "all_attempt_count": 86,
            "all_unique_and_cross_audit_disjoint": True,
        },
        "isolated_workdirs": {"attempt_count": 86, "all_unique": True},
        "cross_audit_input_prompt_schema_hashes_match": True,
        "artifacts": [
            {
                "role": "slot_1_batch_01_attempt_1_events",
                "path": artifact_path.relative_to(root).as_posix(),
                "bytes": len(artifact_raw),
                "sha256": registrar.sha256_bytes(artifact_raw),
            }
        ],
    }
    manifest_path = root / registrar.FROZEN_EVIDENCE_PATHS[
        "audit_evidence_manifest"
    ]
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    reconstructed = copy.deepcopy(manifest)
    reconstructed["created_utc"] = "2026-07-28T14:01:00.000000Z"
    calls = []

    def pair_verifier(verifier_root, *, write_manifest, verification_mode):
        calls.append((verifier_root, write_manifest, verification_mode))
        return copy.deepcopy(reconstructed)

    checkpoint_calls = []

    def checkpoint_validator(verifier_root, value, *, descendant_commit):
        checkpoint_calls.append((verifier_root, value, descendant_commit))
        if value != checkpoint:
            raise ValueError("synthetic repository checkpoint binding drift")
        return copy.deepcopy(value)

    return (
        manifest,
        manifest_path,
        artifact_path,
        pair_verifier,
        calls,
        checkpoint_validator,
        checkpoint_calls,
    )


def make_final_conformance_case():
    config = json.loads(Path(registrar.CONFIG_PATH).read_text(encoding="utf-8"))
    artifact_raw = {
        registrar.TASKS_PATH: b"tasks\n",
        registrar.ANSWER_KEY_PATH: b"answers\n",
        registrar.CATALOG_PATH: b"catalog\n",
        registrar.BENCHMARK_MANIFEST_PATH: b"benchmark\n",
        registrar.AUDIT_RUNNER_PATH: b"audit-runner\n",
        registrar.AUDIT_TEST_PATH: b"audit-tests\n",
        registrar.AUDIT_PROTOCOL_PATH: Path(
            registrar.AUDIT_PROTOCOL_PATH
        ).read_bytes(),
        "scripts/check_px062_gate2_2_tokenizer_conformance.py": Path(
            "scripts/check_px062_gate2_2_tokenizer_conformance.py"
        ).read_bytes(),
        "scripts/run_px062_gate2_2_models.py": Path(
            "scripts/run_px062_gate2_2_models.py"
        ).read_bytes(),
    }
    config["status"] = registrar.FINAL_CONFIG_STATUS
    config["source_integrity"] = {
        "tasks_sha256": registrar.sha256_bytes(artifact_raw[registrar.TASKS_PATH]),
        "answer_key_sha256": registrar.sha256_bytes(
            artifact_raw[registrar.ANSWER_KEY_PATH]
        ),
        "registry_catalog_sha256": registrar.sha256_bytes(
            artifact_raw[registrar.CATALOG_PATH]
        ),
        "benchmark_manifest_sha256": registrar.sha256_bytes(
            artifact_raw[registrar.BENCHMARK_MANIFEST_PATH]
        ),
    }
    config["label_audit_protocol"]["runner_sha256"] = registrar.sha256_bytes(
        artifact_raw[registrar.AUDIT_RUNNER_PATH]
    )
    config["label_audit_protocol"]["protocol_sha256"] = registrar.sha256_bytes(
        artifact_raw[registrar.AUDIT_PROTOCOL_PATH]
    )
    config["label_audit_protocol"]["tests_sha256"] = registrar.sha256_bytes(
        artifact_raw[registrar.AUDIT_TEST_PATH]
    )
    receipt = json.loads(Path(registrar.CONFORMANCE_PATH).read_text(encoding="utf-8"))
    receipt["tasks_sha256"] = config["source_integrity"]["tasks_sha256"]
    receipt["registry_catalog_sha256"] = config["source_integrity"][
        "registry_catalog_sha256"
    ]
    receipt["checker"]["sha256"] = registrar.sha256_bytes(
        artifact_raw["scripts/check_px062_gate2_2_tokenizer_conformance.py"]
    )
    receipt["message_constructor_source"]["sha256"] = registrar.sha256_bytes(
        artifact_raw["scripts/run_px062_gate2_2_models.py"]
    )
    receipt["semantic_config_projection"] = (
        registrar.semantic_config_projection_record(config)
    )
    artifact_raw[registrar.CONFIG_PATH] = json.dumps(config).encode("utf-8")
    artifact_raw[registrar.CONFORMANCE_PATH] = json.dumps(receipt).encode("utf-8")

    def blob_reader(root, commit, path):
        assert commit == "a" * 40
        return artifact_raw[path]

    return config, receipt, artifact_raw, blob_reader


def source_record():
    return {
        "bucket": "bucket",
        "key": "prefix/source.tar.gz",
        "version_id": "v1",
        "bytes": 123,
        "checksum_sha256_base64": "checksum",
        "sha256": "a" * 64,
    }


def test_launch_and_fetch_freeze_the_same_complete_governance_inventory():
    assert registrar.FROZEN_EVIDENCE_PATHS == FROZEN_EVIDENCE_CONTRACT
    assert {
        "audit_1_run",
        "audit_2_run",
        "audit_evidence_manifest",
        "audit_protocol",
        "audit_provisional_resolution",
        "audit_runner",
        "label_finalizer",
        "label_verifier",
        "benchmark_builder",
        "blind_audit_tests",
        "benchmark_tests",
        "tokenizer_conformance_manifest",
        "tokenizer_conformance_checker",
        "tokenizer_conformance_tests",
        "prelaunch_redesign_record",
    } <= set(registrar.FROZEN_EVIDENCE_PATHS)


def test_label_audit_manifest_validation_is_read_only_and_reconstructs_pair(tmp_path):
    (
        manifest,
        path,
        _,
        pair_verifier,
        calls,
        checkpoint_validator,
        checkpoint_calls,
    ) = make_label_audit_manifest(tmp_path)
    before = path.read_bytes()
    before_mtime = path.stat().st_mtime_ns
    result = registrar.validate_label_audit_evidence_manifest(
        tmp_path,
        pair_verifier=pair_verifier,
        source_commit="f" * 40,
        checkpoint_validator=checkpoint_validator,
    )
    assert result == manifest
    assert calls == [(tmp_path.resolve(), False, "historical")]
    assert checkpoint_calls == [
        (tmp_path.resolve(), manifest["repository_checkpoint"], "f" * 40)
    ]
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == before_mtime


def test_registrar_uses_historical_pair_mode_from_a_finalized_current_tree(tmp_path):
    (
        manifest,
        _,
        _,
        pair_verifier,
        _,
        checkpoint_validator,
        _,
    ) = make_label_audit_manifest(tmp_path)
    current_config = tmp_path / registrar.CONFIG_PATH
    current_config.parent.mkdir(parents=True, exist_ok=True)
    current_config.write_text(
        '{"status":"FROZEN_PREREGISTERED"}\n', encoding="utf-8"
    )
    current_answer = tmp_path / registrar.ANSWER_KEY_PATH
    current_answer.parent.mkdir(parents=True, exist_ok=True)
    current_answer.write_text(
        '{"label_audit_status":"AUDITED_UNANIMOUS_VERIFIED"}\n',
        encoding="utf-8",
    )
    observed_modes = []

    def finalized_tree_verifier(
        verifier_root, *, write_manifest, verification_mode
    ):
        assert json.loads(current_config.read_text())["status"] == (
            "FROZEN_PREREGISTERED"
        )
        assert "AUDITED_UNANIMOUS_VERIFIED" in current_answer.read_text()
        observed_modes.append(verification_mode)
        return pair_verifier(
            verifier_root,
            write_manifest=write_manifest,
            verification_mode=verification_mode,
        )

    result = registrar.validate_label_audit_evidence_manifest(
        tmp_path,
        pair_verifier=finalized_tree_verifier,
        checkpoint_validator=checkpoint_validator,
    )
    assert result == manifest
    assert observed_modes == ["historical"]


def test_label_audit_manifest_rejects_referenced_artifact_hash_drift(tmp_path):
    _, _, artifact_path, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path)
    )
    artifact_path.write_bytes(b"tampered\n")
    with pytest.raises(ValueError, match="artifact binding drift"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path,
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )


def test_label_audit_manifest_rejects_escaping_artifact_path(tmp_path):
    manifest, path, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path)
    )
    manifest["artifacts"][0]["path"] = "../outside.events.jsonl"
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="escapes repository"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path,
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )


def test_label_audit_manifest_rejects_pair_verifier_mismatch(tmp_path):
    _, _, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path)
    )

    def mismatched_pair(verifier_root, *, write_manifest, verification_mode):
        result = pair_verifier(
            verifier_root,
            write_manifest=write_manifest,
            verification_mode=verification_mode,
        )
        result["global_session_ids"]["accepted_count"] = 85
        return result

    with pytest.raises(ValueError, match="does not match"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path,
            pair_verifier=mismatched_pair,
            checkpoint_validator=checkpoint_validator,
        )


def test_label_audit_manifest_rejects_superseded_or_unblinded_schema(tmp_path):
    manifest, path, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path)
    )
    manifest["answer_key_included"] = manifest.pop("answer_key_contents_included")
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema drift"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path,
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )

    manifest, path, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path / "second")
    )
    manifest["answer_key_contents_included"] = True
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="policy drift"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path / "second",
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )


def test_label_audit_manifest_rejects_pending_checkpoint_or_session_forgery(tmp_path):
    manifest, path, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path)
    )
    manifest["repository_checkpoint"]["pending_answer_sha256"] = "0" * 64
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint binding drift"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path,
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )

    manifest, path, _, pair_verifier, _, checkpoint_validator, _ = (
        make_label_audit_manifest(tmp_path / "second")
    )
    manifest["audits"][1]["accepted_session_ids"][0] = manifest["audits"][0][
        "accepted_session_ids"
    ][0]
    path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="overlap"):
        registrar.validate_label_audit_evidence_manifest(
            tmp_path / "second",
            pair_verifier=pair_verifier,
            checkpoint_validator=checkpoint_validator,
        )


def test_historical_checkpoint_binds_git_bytes_config_and_ancestry(
    tmp_path, monkeypatch
):
    head = "a" * 40
    source = "b" * 40
    paths = list(registrar.CHECKPOINT_TRACKED_PATHS)
    raw = {path: f"historical:{path}\n".encode() for path in paths}
    source_integrity = {
        "tasks_sha256": registrar.sha256_bytes(raw[paths[0]]),
        "answer_key_sha256": registrar.sha256_bytes(raw[paths[2]]),
        "registry_catalog_sha256": registrar.sha256_bytes(raw[paths[1]]),
        "benchmark_manifest_sha256": registrar.sha256_bytes(raw[paths[3]]),
    }
    protocol = {"binding": "historical-audit-protocol"}
    config = {
        "status": "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT",
        "source_integrity": source_integrity,
        "label_audit_protocol": protocol,
    }
    raw[registrar.CHECKPOINT_CONFIG_PATH] = json.dumps(config).encode()
    tracked = {
        path: {
            "head_blob": f"{index + 1:040x}",
            "sha256": registrar.sha256_bytes(value),
            "bytes": len(value),
        }
        for index, (path, value) in enumerate(raw.items())
    }
    checkpoint = {
        "head_commit": head,
        "tracked_files": tracked,
        "config_sha256": registrar.sha256_bytes(
            raw[registrar.CHECKPOINT_CONFIG_PATH]
        ),
        "source_integrity": source_integrity,
        "label_audit_protocol": protocol,
    }
    monkeypatch.setattr(
        registrar,
        "validate_pending_repository_checkpoint",
        lambda value, **kwargs: copy.deepcopy(value),
    )

    def blob_reader(root, commit, path):
        assert root == tmp_path
        assert commit == head
        return raw[path]

    def object_reader(root, commit, path):
        return tracked[path]["head_blob"]

    result = registrar.validate_historical_audit_checkpoint(
        tmp_path,
        checkpoint,
        descendant_commit=source,
        blob_reader=blob_reader,
        object_reader=object_reader,
        ancestor_check=lambda root, ancestor, descendant: True,
    )
    assert result == checkpoint

    answer_path = paths[2]
    with pytest.raises(ValueError, match="Git binding drift"):
        registrar.validate_historical_audit_checkpoint(
            tmp_path,
            checkpoint,
            blob_reader=lambda root, commit, path: (
                b"tampered\n" if path == answer_path else raw[path]
            ),
            object_reader=object_reader,
        )

    forged_checkpoint = copy.deepcopy(checkpoint)
    forged_checkpoint["source_integrity"]["answer_key_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="pending config binding drift"):
        registrar.validate_historical_audit_checkpoint(
            tmp_path,
            forged_checkpoint,
            blob_reader=blob_reader,
            object_reader=object_reader,
        )

    with pytest.raises(ValueError, match="not an ancestor"):
        registrar.validate_historical_audit_checkpoint(
            tmp_path,
            checkpoint,
            descendant_commit=source,
            blob_reader=blob_reader,
            object_reader=object_reader,
            ancestor_check=lambda root, ancestor, descendant: False,
        )


def test_final_registration_semantically_validates_conformance_receipt(tmp_path):
    _, receipt, _, blob_reader = make_final_conformance_case()
    result = registrar.validate_final_config_and_conformance(
        tmp_path, "a" * 40, blob_reader=blob_reader
    )
    assert result["conformance"] == receipt
    assert sum(
        row["rendered_model_task_arm_sets"] for row in receipt["models"]
    ) == 10320


def test_final_registration_rejects_pending_or_semantically_drifted_config(tmp_path):
    config, _, artifacts, blob_reader = make_final_conformance_case()
    config["status"] = "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT"
    artifacts[registrar.CONFIG_PATH] = json.dumps(config).encode("utf-8")
    with pytest.raises(ValueError, match="FROZEN_PREREGISTERED"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )

    config["status"] = registrar.FINAL_CONFIG_STATUS
    config["gates"]["C_overall_accuracy_min"] = 0.76
    artifacts[registrar.CONFIG_PATH] = json.dumps(config).encode("utf-8")
    with pytest.raises(ValueError, match="semantic projection"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )


def test_final_registration_rejects_stale_pending_conformance_receipt(tmp_path):
    _, receipt, artifacts, blob_reader = make_final_conformance_case()
    receipt["schema_version"] = "px062-gate2.2-tokenizer-conformance-v2"
    del receipt["semantic_config_projection"]
    artifacts[registrar.CONFORMANCE_PATH] = json.dumps(receipt).encode("utf-8")
    with pytest.raises(ValueError, match="semantic projection|stale"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )


def test_final_registration_rejects_checker_or_context_headroom_drift(tmp_path):
    _, receipt, artifacts, blob_reader = make_final_conformance_case()
    receipt["checker"]["sha256"] = "0" * 64
    artifacts[registrar.CONFORMANCE_PATH] = json.dumps(receipt).encode("utf-8")
    with pytest.raises(ValueError, match="checker binding"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )


def test_final_registration_directly_validates_excluded_audit_test_hash(tmp_path):
    config, _, artifacts, blob_reader = make_final_conformance_case()
    config["label_audit_protocol"]["tests_sha256"] = "0" * 64
    artifacts[registrar.CONFIG_PATH] = json.dumps(config).encode("utf-8")
    with pytest.raises(ValueError, match="audit-tests hash drift"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )


def test_final_registration_rejects_context_headroom_drift(tmp_path):
    _, receipt, artifacts, blob_reader = make_final_conformance_case()
    receipt["models"][0]["minimum_context_headroom_tokens"] -= 1
    artifacts[registrar.CONFORMANCE_PATH] = json.dumps(receipt).encode("utf-8")
    with pytest.raises(ValueError, match="context headroom"):
        registrar.validate_final_config_and_conformance(
            tmp_path, "a" * 40, blob_reader=blob_reader
        )


def test_unversioned_source_must_be_exactly_one_latest_registered_version(monkeypatch):
    responses = iter(
        [
            {
                "Versions": [
                    {
                        "Key": "prefix/source.tar.gz",
                        "VersionId": "v1",
                        "IsLatest": True,
                    }
                ]
            },
            {
                "VersionId": "v1",
                "ContentLength": 123,
                "ChecksumSHA256": "checksum",
                "Metadata": {"sha256": "a" * 64},
            },
        ]
    )
    monkeypatch.setattr(launch, "aws", lambda *args: next(responses))
    launch.validate_unversioned_source_binding("profile", "region", source_record())


@pytest.mark.parametrize(
    "listing",
    [
        {
            "Versions": [
                {"Key": "prefix/source.tar.gz", "VersionId": "v1", "IsLatest": True},
                {"Key": "prefix/source.tar.gz", "VersionId": "v0", "IsLatest": False},
            ]
        },
        {
            "Versions": [
                {"Key": "prefix/source.tar.gz", "VersionId": "v1", "IsLatest": True}
            ],
            "DeleteMarkers": [{"Key": "prefix/source.tar.gz"}],
        },
        {
            "Versions": [
                {"Key": "prefix/source.tar.gz", "VersionId": "v1", "IsLatest": False}
            ]
        },
    ],
)
def test_unversioned_source_rejects_ambiguous_or_nonlatest_version(monkeypatch, listing):
    monkeypatch.setattr(launch, "aws", lambda *args: listing)
    with pytest.raises(ValueError, match="sole/latest"):
        launch.validate_unversioned_source_binding("profile", "region", source_record())


def test_find_job_propagates_non_resource_not_found_describe_error(monkeypatch):
    def fake_aws(*args):
        raise subprocess.CalledProcessError(
            255, ["aws"], stderr="An error occurred (AccessDeniedException)"
        )

    monkeypatch.setattr(launch, "aws", fake_aws)
    with pytest.raises(subprocess.CalledProcessError):
        launch.find_training_job("profile", "region", "job")


def test_find_job_treats_only_explicit_resource_not_found_as_absent(monkeypatch):
    def fake_aws(*args):
        raise subprocess.CalledProcessError(
            255, ["aws"], stderr="An error occurred (ResourceNotFound)"
        )

    monkeypatch.setattr(launch, "aws", fake_aws)
    assert launch.find_training_job("profile", "region", "job") is None


def test_empty_list_payload_cannot_authorize_initial_absence(monkeypatch):
    calls = []

    def fake_aws(*args):
        calls.append(args)
        return {"TrainingJobSummaries": []}

    monkeypatch.setattr(launch, "aws", fake_aws)
    observed = launch.find_training_job("profile", "region", "job")
    assert observed == {"TrainingJobSummaries": []}
    assert calls[0][2:4] == ("sagemaker", "describe-training-job")


def test_registration_absence_requires_explicit_resource_not_found(monkeypatch):
    error = subprocess.CalledProcessError(
        255, ["aws"], stderr="An error occurred (ResourceNotFoundException)"
    )
    monkeypatch.setattr(registrar, "aws", lambda *args: (_ for _ in ()).throw(error))
    assert registrar.require_explicit_training_job_absence(
        "profile", "region", "job"
    )["authorized_initial_absence"] is True

    monkeypatch.setattr(
        registrar, "aws", lambda *args: {"TrainingJobSummaries": []}
    )
    with pytest.raises(FileExistsError, match="already exists"):
        registrar.require_explicit_training_job_absence(
            "profile", "region", "job"
        )


def test_checksum_backend_preflight_fails_before_any_aws_call(tmp_path, monkeypatch):
    monkeypatch.setattr(
        registrar,
        "validate_git_state",
        lambda *_args: {"branch": "test", "remote_refs": ["origin/test"]},
    )
    monkeypatch.setattr(
        registrar, "validate_label_audit_evidence_manifest", lambda *_args, **_kw: None
    )
    monkeypatch.setattr(
        registrar, "validate_final_config_and_conformance", lambda *_args: None
    )
    monkeypatch.setattr(
        registrar.subprocess,
        "check_output",
        lambda *_args, **_kw: b"xxhash==3.8.1\n",
    )
    monkeypatch.setattr(
        registrar,
        "checksum_runtime_record",
        lambda _raw: (_ for _ in ()).throw(ValueError("backend drift")),
    )
    aws_calls = []
    monkeypatch.setattr(registrar, "aws", lambda *args: aws_calls.append(args))
    with pytest.raises(ValueError, match="backend drift"):
        registrar.register(
            root=tmp_path,
            profile="test",
            source_commit="a" * 40,
            job_name="job",
            bucket="bucket",
            region="us-east-1",
            role_arn="role",
            image="image",
        )
    assert aws_calls == []


def test_operator_fetch_policy_is_exact_and_least_privilege():
    root = Path(__file__).resolve().parents[1]
    raw = (root / registrar.OPERATOR_FETCH_POLICY_PATH).read_bytes()
    record = registrar.operator_fetch_policy_record(raw, registrar.DEFAULT_BUCKET)
    assert record["versioned_read_actions"] == [
        "s3:GetObjectVersion",
        "s3:GetObjectVersionAttributes",
    ]
    assert record["version_listing_action"] == "s3:ListBucketVersions"
    assert b"PutObject" not in raw and b"DeleteObject" not in raw

    policy = json.loads(raw)
    policy["Statement"][1]["Action"].append("s3:GetObject")
    with pytest.raises(ValueError, match="least-privilege exact"):
        registrar.operator_fetch_policy_record(
            json.dumps(policy).encode(), registrar.DEFAULT_BUCKET
        )


def test_recovery_requires_existing_job_to_match_registered_request():
    request = {
        "AlgorithmSpecification": {"TrainingImage": "image", "TrainingInputMode": "File"},
        "RoleArn": "role",
        "OutputDataConfig": {"S3OutputPath": "s3://bucket/out"},
        "ResourceConfig": {"InstanceType": "ml.g5.2xlarge", "InstanceCount": 1},
        "StoppingCondition": {"MaxRuntimeInSeconds": 10},
        "HyperParameters": {"sagemaker_submit_directory": "s3://bucket/source"},
        "Environment": {"A": "B"},
        "EnableNetworkIsolation": False,
        "RetryStrategy": {"MaximumRetryAttempts": 0},
    }
    description = {
        "TrainingJobName": "job",
        "TrainingJobArn": "arn:aws:sagemaker:r:a:training-job/job",
        **request,
    }
    registration = {"job_name": "job"}
    launch.validate_recoverable_job(description, request, registration)
    description["RoleArn"] = "attacker-role"
    with pytest.raises(ValueError, match="RoleArn"):
        launch.validate_recoverable_job(description, request, registration)
