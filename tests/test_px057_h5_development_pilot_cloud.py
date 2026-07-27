from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import cloud_jobs.px057_h5_development_pilot_20260727.sagemaker_entry as cloud
import scripts.px057_h5_development_integrity as integrity


ROOT = Path(__file__).resolve().parents[1]


def canonical_line(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_line(row) for row in rows), encoding="utf-8")


def source_rows() -> list[dict]:
    path = ROOT / cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"]
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def make_bundle(output_dir: Path) -> tuple[list[dict], dict[str, dict]]:
    selected = source_rows()[: cloud.EXPECTED_PILOT_ROWS]
    source_by_id = {row["question_id"]: row for row in source_rows()}
    traces = [
        {
            "question_id": row["question_id"],
            "steps": [
                {"step": round_index, "answer": "1", "tokens": round_index}
                for round_index in range(1, cloud.EXPECTED_ROUNDS + 1)
            ],
        }
        for row in selected
    ]
    raw = [
        {
            "question_id": row["question_id"],
            "round": round_index,
            "response": "Final answer: 1",
        }
        for row in selected
        for round_index in range(1, cloud.EXPECTED_ROUNDS + 1)
    ]
    output_dir.mkdir(parents=True)
    write_jsonl(output_dir / "selected_rows.jsonl", selected)
    write_jsonl(output_dir / "reasoning_traces.jsonl", traces)
    write_jsonl(output_dir / "raw_generations.jsonl", raw)
    summary = {
        "stage": "H5_DEVELOPMENT_PILOT_COLLECTION",
        "status": "PASS",
        "confirmatory_evidence": False,
        "attempt_id": "r2",
        "protocol_id": "px057-h5-c1-development-native-chat-v1",
        "frozen_cell_id": "C1-H4DEV-NATIVECHAT-V1",
        "policy_id": "m4-k2-valid-v1",
        "cell_id": "cell1_llama31_gsm8k",
        "source_manifest": {
            "path": cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"],
            "sha256": cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["sha256"],
            "outcome_exposed": True,
        },
        "selection": {"rows": cloud.EXPECTED_PILOT_ROWS},
        "generation": {
            "rounds": cloud.EXPECTED_ROUNDS,
            "pilot_n": cloud.EXPECTED_PILOT_ROWS,
        },
        "observed_generation_rows": cloud.EXPECTED_RAW_ROWS,
    }
    (output_dir / "collection_summary.json").write_bytes(
        cloud.canonical_json_bytes(summary)
    )
    return selected, source_by_id


def valid_environment(archive: Path) -> dict[str, str]:
    return {
        "PX057_H5_DEV_REPOSITORY_URL": "https://example.test/praxis.git",
        "PX057_H5_DEV_BRANCH": "agent/px057-h5-certified-transfer",
        "PX057_H5_DEV_GIT_COMMIT": "a" * 40,
        "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST": "sha256:" + "b" * 64,
        "PX057_H5_DEV_HF_SECRET_ID": "praxis/huggingface/token",
        "PX057_H5_DEV_AWS_REGION": "us-east-1",
        "PX057_H5_DEV_JOB_NAME": "px057-h5-dev-c1-ccchat-n500-r2-20260727",
        "PX057_H5_DEV_SOURCE_VERSION_ID": "version-1",
        "PX057_H5_DEV_SOURCE_ARCHIVE_SHA256": cloud.sha256_file(archive),
        "PX057_H5_DEV_CONFIG_SHA256": "c" * 64,
        "PX057_H5_DEV_CELL_ID": "cell1_llama31_gsm8k",
        "PX057_H5_DEV_ATTEMPT_ID": "r2",
        "PX057_H5_DEV_PROTOCOL_ID": "px057-h5-c1-development-native-chat-v1",
        "PX057_H5_DEV_FROZEN_CELL_ID": "C1-H4DEV-NATIVECHAT-V1",
        "PX057_H5_DEV_POLICY_ID": "m4-k2-valid-v1",
    }


def test_required_environment_rejects_null_source_version(tmp_path: Path) -> None:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"source")
    environment = valid_environment(archive)
    environment["PX057_H5_DEV_SOURCE_VERSION_ID"] = "null"

    with pytest.raises(ValueError, match="must be a real version"):
        cloud.required_environment(environment)


def copy_preflight_repo(target: Path) -> None:
    for relative in (
        cloud.ENTRY,
        cloud.CONFIG,
        cloud.RUNNER,
        cloud.MECHANISM,
        cloud.CONTRACT,
        cloud.INTEGRITY,
        cloud.H4_REQUIREMENTS,
        cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"],
    ):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)


def make_execute_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    source_path: Path | None = None,
) -> tuple[dict[str, str], cloud.Preflight, Path, Path, Path]:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"authenticated staged entry archive")
    repo = tmp_path / "repo"
    copy_preflight_repo(repo)
    model_dir = tmp_path / "model"
    config = json.loads((ROOT / cloud.CONFIG).read_text(encoding="utf-8"))
    cell = config["cells"][0]
    source_path = source_path or repo / cell["source_manifest"]
    rows = tuple(source_rows())
    preflight = cloud.Preflight(
        config=config,
        cell=cell,
        source_path=source_path,
        source_rows=rows,
        source_by_id={str(row["question_id"]): row for row in rows},
        output_dir=tmp_path / "output",
        committed_entry_sha256=cloud.sha256_file(ROOT / cloud.ENTRY),
        config_sha256=cloud.sha256_file(ROOT / cloud.CONFIG),
        runner_sha256=cloud.sha256_file(ROOT / cloud.RUNNER),
        mechanism_sha256=cloud.sha256_file(ROOT / cloud.MECHANISM),
        contract_sha256=cloud.sha256_file(ROOT / cloud.CONTRACT),
        integrity_sha256=cloud.sha256_file(ROOT / cloud.INTEGRITY),
        requirements_sha256=cloud.sha256_file(ROOT / cloud.H4_REQUIREMENTS),
    )
    environment = valid_environment(archive)
    environment.update(
        {
            "PX057_H5_DEV_REPOSITORY_URL": config["repository"]["url"],
            "PX057_H5_DEV_BRANCH": config["repository"]["branch"],
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST": config["aws"][
                "container_image"
            ].rsplit("@", 1)[1],
            "PX057_H5_DEV_CONFIG_SHA256": preflight.config_sha256,
        }
    )
    monkeypatch.setattr(
        cloud,
        "clone_exact_pushed_commit",
        lambda *_args, **_kwargs: "d" * 40,
    )
    monkeypatch.setattr(
        cloud,
        "validate_pre_model_contract",
        lambda *_args, **_kwargs: preflight,
    )
    monkeypatch.setattr(cloud, "install_locked_h4_dependencies", lambda *_args: None)
    monkeypatch.setattr(
        cloud,
        "read_huggingface_token",
        lambda *_args: "test-huggingface-token",
    )
    return environment, preflight, archive, repo, model_dir


def synthetic_collection_verification(
    preflight: cloud.Preflight,
) -> dict[str, Any]:
    files = {
        name: {"sha256": hashlib.sha256(name.encode("utf-8")).hexdigest(), "bytes": 1}
        for name in cloud.COLLECTION_FILES
    }
    return {
        "status": "PASS",
        "experiment_id": preflight.config["experiment_id"],
        "frozen_cell_id": preflight.config["frozen_cell_id"],
        "cell_id": preflight.cell["cell_id"],
        "trace_count": 500,
        "rounds_per_trace": 8,
        "raw_generation_count": 4000,
        "source_membership": "EXACT_H4_CALIBRATION_MANIFEST",
        "source_sha256": preflight.cell["source_manifest_sha256"],
        "selected_id_sha256": "e" * 64,
        "files": files,
    }


def test_environment_contract_uses_only_px057_h5_dev_names() -> None:
    assert cloud.REQUIRED_ENVIRONMENT
    assert all(name.startswith("PX057_H5_DEV_") for name in cloud.REQUIRED_ENVIRONMENT)
    assert set(cloud.H4_CALIBRATION_SOURCES) == {"cell1_llama31_gsm8k"}


def test_archive_failure_occurs_before_clone_dependency_secret_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"staged archive")
    environment = valid_environment(archive)
    environment["PX057_H5_DEV_SOURCE_ARCHIVE_SHA256"] = "0" * 64
    calls: list[str] = []
    monkeypatch.setattr(
        cloud,
        "clone_exact_pushed_commit",
        lambda *_args, **_kwargs: calls.append("clone"),
    )
    monkeypatch.setattr(
        cloud,
        "install_locked_h4_dependencies",
        lambda *_args, **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        cloud,
        "read_huggingface_token",
        lambda *_args, **_kwargs: calls.append("secret"),
    )
    monkeypatch.setattr(
        cloud,
        "run_development_pilot",
        lambda *_args, **_kwargs: calls.append("runner"),
    )

    with pytest.raises(ValueError, match="staged source archive"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=tmp_path / "entry.py",
            repo_dir=tmp_path / "repo",
            model_dir=tmp_path / "model",
        )

    assert calls == []


def test_committed_entry_mismatch_fails_before_dependency_secret_or_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"staged archive")
    repo = tmp_path / "repo"
    copy_preflight_repo(repo)
    config = json.loads((repo / cloud.CONFIG).read_text(encoding="utf-8"))
    environment = valid_environment(archive)
    environment.update(
        {
            "PX057_H5_DEV_REPOSITORY_URL": config["repository"]["url"],
            "PX057_H5_DEV_BRANCH": config["repository"]["branch"],
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST": config["aws"][
                "container_image"
            ].rsplit("@", 1)[1],
            "PX057_H5_DEV_CONFIG_SHA256": cloud.sha256_file(repo / cloud.CONFIG),
        }
    )
    staged_entry = tmp_path / "e.py"
    staged_entry.write_text("# forged entry\n", encoding="utf-8")
    calls: list[str] = []
    monkeypatch.setattr(
        cloud,
        "clone_exact_pushed_commit",
        lambda *_args, **_kwargs: environment["PX057_H5_DEV_GIT_COMMIT"],
    )
    monkeypatch.setattr(
        cloud,
        "install_locked_h4_dependencies",
        lambda *_args, **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        cloud,
        "read_huggingface_token",
        lambda *_args, **_kwargs: calls.append("secret"),
    )
    monkeypatch.setattr(
        cloud,
        "run_development_pilot",
        lambda *_args, **_kwargs: calls.append("runner"),
    )

    with pytest.raises(ValueError, match="staged development entry"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=staged_entry,
            repo_dir=repo,
            model_dir=tmp_path / "model",
        )

    assert calls == []


def test_secret_identity_mismatch_fails_before_dependency_or_model_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"staged archive")
    repo = tmp_path / "repo"
    copy_preflight_repo(repo)
    config = json.loads((repo / cloud.CONFIG).read_text(encoding="utf-8"))
    environment = valid_environment(archive)
    environment.update(
        {
            "PX057_H5_DEV_REPOSITORY_URL": config["repository"]["url"],
            "PX057_H5_DEV_BRANCH": config["repository"]["branch"],
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST": config["aws"][
                "container_image"
            ].rsplit("@", 1)[1],
            "PX057_H5_DEV_CONFIG_SHA256": cloud.sha256_file(repo / cloud.CONFIG),
            "PX057_H5_DEV_HF_SECRET_ID": "wrong/secret",
        }
    )
    calls: list[str] = []
    monkeypatch.setattr(
        cloud,
        "clone_exact_pushed_commit",
        lambda *_args, **_kwargs: environment["PX057_H5_DEV_GIT_COMMIT"],
    )
    monkeypatch.setattr(
        cloud,
        "install_locked_h4_dependencies",
        lambda *_args, **_kwargs: calls.append("install"),
    )
    monkeypatch.setattr(
        cloud,
        "read_huggingface_token",
        lambda *_args, **_kwargs: calls.append("secret"),
    )
    monkeypatch.setattr(
        cloud,
        "run_development_pilot",
        lambda *_args, **_kwargs: calls.append("runner"),
    )

    with pytest.raises(ValueError, match="credential/region"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=repo / cloud.ENTRY,
            repo_dir=repo,
            model_dir=tmp_path / "model",
        )

    assert calls == []


def test_clone_accepts_a_submitted_commit_behind_the_pushed_branch_head(
    tmp_path: Path,
) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    clone = tmp_path / "clone"
    descendant_clone = tmp_path / "descendant-clone"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "pilot", str(work)], check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.test"],
        cwd=work,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PX057 Fixture"],
        cwd=work,
        check=True,
    )
    (work / "evidence.txt").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    subprocess.run(["git", "commit", "-qm", "first"], cwd=work, check=True)
    first = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=work, text=True
    ).strip()
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=work, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", "pilot"], cwd=work, check=True)

    assert cloud.clone_exact_pushed_commit(str(remote), "pilot", first, clone) == first

    (work / "evidence.txt").write_text("two", encoding="utf-8")
    subprocess.run(["git", "commit", "-qam", "second"], cwd=work, check=True)
    subprocess.run(["git", "push", "-q"], cwd=work, check=True)
    observed = cloud.clone_exact_pushed_commit(
        str(remote), "pilot", first, descendant_clone
    )
    second = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=work, text=True
    ).strip()
    assert observed == second
    assert subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=descendant_clone, text=True
    ).strip() == first


def test_clone_rejects_a_commit_not_in_the_remote_branch_history(
    tmp_path: Path,
) -> None:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    clone = tmp_path / "clone"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "pilot", str(work)], check=True)
    subprocess.run(
        ["git", "config", "user.email", "fixture@example.test"],
        cwd=work,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PX057 Fixture"],
        cwd=work,
        check=True,
    )
    (work / "evidence.txt").write_text("one", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=work, check=True)
    subprocess.run(["git", "commit", "-qm", "first"], cwd=work, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=work, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", "pilot"], cwd=work, check=True)

    with pytest.raises(ValueError, match="not an ancestor"):
        cloud.clone_exact_pushed_commit(str(remote), "pilot", "f" * 40, clone)


def test_locked_h4_dependency_parser_requires_exact_versions() -> None:
    packages = cloud.locked_h4_packages(ROOT / "requirements-px057-h4.txt")

    assert "transformers==4.46.3" in packages
    assert "torch==2.3.0" not in packages
    assert all("==" in package for package in packages)


def test_collection_bundle_is_exactly_500_by_8_and_h4_sourced(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _selected, source_by_id = make_bundle(output_dir)

    result = cloud.verify_collection_bundle(
        output_dir,
        cell_id="cell1_llama31_gsm8k",
        source_path=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"],
        source_sha256=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["sha256"],
        source_by_id=source_by_id,
    )

    assert result["trace_count"] == 500
    assert result["rounds_per_trace"] == 8
    assert result["raw_generation_count"] == 4000
    assert result["source_membership"] == "EXACT_H4_CALIBRATION_SUBSET"
    assert set(result["files"]) == set(cloud.COLLECTION_FILES)


def test_collection_rejects_an_id_outside_h4_calibration_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    selected, source_by_id = make_bundle(output_dir)
    selected[0] = {**selected[0], "question_id": "not-an-h4-calibration-id"}
    write_jsonl(output_dir / "selected_rows.jsonl", selected)

    with pytest.raises(ValueError, match="outside the H4 calibration"):
        cloud.verify_collection_bundle(
            output_dir,
            cell_id="cell1_llama31_gsm8k",
            source_path=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"],
            source_sha256=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["sha256"],
            source_by_id=source_by_id,
        )


def test_collection_rejects_incomplete_round_cartesian_set(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    _selected, source_by_id = make_bundle(output_dir)
    raw_path = output_dir / "raw_generations.jsonl"
    raw = [json.loads(line) for line in raw_path.read_text(encoding="utf-8").splitlines()]
    write_jsonl(raw_path, raw[:-1])

    with pytest.raises(ValueError, match="500-by-8 Cartesian"):
        cloud.verify_collection_bundle(
            output_dir,
            cell_id="cell1_llama31_gsm8k",
            source_path=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"],
            source_sha256=cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["sha256"],
            source_by_id=source_by_id,
        )


def test_model_bundle_contains_four_outputs_and_cloud_evidence(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    make_bundle(output_dir)
    model_dir = tmp_path / "model"

    target = cloud.write_model_bundle(
        output_dir,
        model_dir,
        cell_id="cell1_llama31_gsm8k",
        evidence={"status": "PASS", "confirmatory_evidence": False},
    )

    assert {path.name for path in target.iterdir()} == {
        *cloud.COLLECTION_FILES,
        "cloud_job_evidence.json",
    }
    evidence = json.loads((target / "cloud_job_evidence.json").read_text())
    assert evidence == {"status": "PASS", "confirmatory_evidence": False}


def test_execute_passes_exact_inputs_to_both_integrity_apis_before_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment, preflight, archive, repo, model_dir = make_execute_fixture(
        tmp_path, monkeypatch
    )
    verification = synthetic_collection_verification(preflight)
    calls: list[str] = []

    def run_pilot(*_args: Any, **_kwargs: Any) -> None:
        calls.append("runner")

    def verify_scientific(
        collection_dir: Path,
        *,
        config: dict[str, Any],
        source_manifest_bytes: bytes,
        expected_source_sha256: str,
    ) -> dict[str, Any]:
        calls.append("scientific_integrity")
        assert collection_dir == preflight.output_dir
        assert config is preflight.config
        assert source_manifest_bytes == preflight.source_path.read_bytes()
        assert expected_source_sha256 == preflight.cell["source_manifest_sha256"]
        return verification

    def verify_cloud(
        evidence: dict[str, Any],
        *,
        config: dict[str, Any],
        collection_verification: dict[str, Any],
        expected_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        calls.append("cloud_integrity")
        assert config is preflight.config
        assert collection_verification is verification
        assert expected_metadata["job_name"] == environment[
            "PX057_H5_DEV_JOB_NAME"
        ]
        assert expected_metadata["git_commit"] == environment[
            "PX057_H5_DEV_GIT_COMMIT"
        ]
        assert expected_metadata["container_image_digest"] == environment[
            "PX057_H5_DEV_CONTAINER_IMAGE_DIGEST"
        ]
        assert expected_metadata["source_archive"] == {
            "version_id": environment["PX057_H5_DEV_SOURCE_VERSION_ID"],
            "sha256": environment["PX057_H5_DEV_SOURCE_ARCHIVE_SHA256"],
        }
        assert expected_metadata["code"]["config_sha256"] == (
            preflight.config_sha256
        )
        assert expected_metadata["code"]["integrity_sha256"] == (
            preflight.integrity_sha256
        )
        assert evidence["code"] == expected_metadata["code"]
        assert evidence["code"] is not expected_metadata["code"]
        assert evidence["collection_verification"] is not verification
        assert evidence["collection_files"] is not verification["files"]
        return {"status": "PASS"}

    def write_bundle(*_args: Any, **_kwargs: Any) -> Path:
        calls.append("bundle")
        return model_dir / "bundle"

    monkeypatch.setattr(cloud, "run_development_pilot", run_pilot)
    monkeypatch.setattr(integrity, "verify_scientific_collection", verify_scientific)
    monkeypatch.setattr(integrity, "verify_cloud_evidence", verify_cloud)
    monkeypatch.setattr(cloud, "write_model_bundle", write_bundle)

    evidence = cloud.execute(
        environment,
        staged_archive=archive,
        staged_entry=ROOT / cloud.ENTRY,
        repo_dir=repo,
        model_dir=model_dir,
    )

    assert evidence["status"] == "PASS"
    assert calls == ["runner", "scientific_integrity", "cloud_integrity", "bundle"]


def test_execute_rejects_changed_source_bytes_before_evidence_or_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    changed_source = tmp_path / "changed-source.jsonl"
    changed_source.write_bytes(
        (ROOT / cloud.H4_CALIBRATION_SOURCES["cell1_llama31_gsm8k"]["path"])
        .read_bytes()
        .replace(b'"gold_answer":"16"', b'"gold_answer":"17"', 1)
    )
    environment, preflight, archive, repo, model_dir = make_execute_fixture(
        tmp_path,
        monkeypatch,
        source_path=changed_source,
    )
    calls: list[str] = []

    def run_pilot(*_args: Any, **_kwargs: Any) -> None:
        calls.append("runner")
        preflight.output_dir.mkdir()
        for name in cloud.COLLECTION_FILES:
            (preflight.output_dir / name).write_bytes(b"\n")

    monkeypatch.setattr(cloud, "run_development_pilot", run_pilot)
    monkeypatch.setattr(
        integrity,
        "verify_cloud_evidence",
        lambda *_args, **_kwargs: calls.append("cloud_integrity"),
    )
    monkeypatch.setattr(
        cloud,
        "write_model_bundle",
        lambda *_args, **_kwargs: calls.append("bundle"),
    )

    with pytest.raises(ValueError, match="pinned source manifest SHA-256 mismatch"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=ROOT / cloud.ENTRY,
            repo_dir=repo,
            model_dir=model_dir,
        )

    assert calls == ["runner"]


def test_execute_rejects_changed_integrity_code_hash_before_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment, preflight, archive, repo, model_dir = make_execute_fixture(
        tmp_path, monkeypatch
    )
    verification = synthetic_collection_verification(preflight)
    calls: list[str] = []
    original_verify_cloud = integrity.verify_cloud_evidence

    monkeypatch.setattr(cloud, "run_development_pilot", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        integrity,
        "verify_scientific_collection",
        lambda *_args, **_kwargs: verification,
    )

    def tamper_then_verify(
        evidence: dict[str, Any], **kwargs: Any
    ) -> dict[str, Any]:
        calls.append("cloud_integrity")
        evidence["code"]["integrity_sha256"] = "0" * 64
        return original_verify_cloud(evidence, **kwargs)

    monkeypatch.setattr(integrity, "verify_cloud_evidence", tamper_then_verify)
    monkeypatch.setattr(
        cloud,
        "write_model_bundle",
        lambda *_args, **_kwargs: calls.append("bundle"),
    )

    with pytest.raises(ValueError, match="identity/code/image/source mismatch"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=ROOT / cloud.ENTRY,
            repo_dir=repo,
            model_dir=model_dir,
        )

    assert calls == ["cloud_integrity"]


def test_execute_rehashes_integrity_verifier_after_runner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment, _preflight, archive, repo, model_dir = make_execute_fixture(
        tmp_path, monkeypatch
    )
    calls: list[str] = []

    def change_integrity_after_collection(*_args: Any, **_kwargs: Any) -> None:
        calls.append("runner")
        (repo / cloud.INTEGRITY).write_text(
            "# changed after preflight\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        cloud,
        "run_development_pilot",
        change_integrity_after_collection,
    )
    monkeypatch.setattr(
        integrity,
        "verify_scientific_collection",
        lambda *_args, **_kwargs: calls.append("scientific_integrity"),
    )
    monkeypatch.setattr(
        cloud,
        "write_model_bundle",
        lambda *_args, **_kwargs: calls.append("bundle"),
    )

    with pytest.raises(ValueError, match="post-collection pinned code/config changed"):
        cloud.execute(
            environment,
            staged_archive=archive,
            staged_entry=ROOT / cloud.ENTRY,
            repo_dir=repo,
            model_dir=model_dir,
        )

    assert calls == ["runner"]
