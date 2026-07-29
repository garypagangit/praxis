from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.freeze_px057_h4_holdout_transport import (
    EXPECTED_CELLS,
    FROZEN_SCIENCE_FIELDS,
    FREEZE_SCHEMA_VERSION,
    TRANSPORT_CONFIG_PATH,
    expected_freeze_inventory,
    require_clean_pushed_head,
    require_no_outcome_or_holdout_evidence,
    validate_config,
    validate_freeze_manifest,
    validate_freeze_manifest_schema,
    verify_binding,
    verify_calibration_evidence,
    verify_freeze_base_artifacts,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/px057_h4_holdout_transport_20260727.json"
EVIDENCE_COMMIT = "e27aafaa46967c85cb7f88517ef374e4ae8a3d73"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def run_git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def initialize_repo(repo: Path, *, branch: str = "experiment") -> None:
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "px057@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "PX057 Test"],
        cwd=repo,
        check=True,
    )


def synthetic_valid_freeze(config: dict) -> dict:
    head = "a" * 40
    inventory = expected_freeze_inventory(config)
    protected_paths = inventory["protected_artifacts"]["paths"]
    records = {
        path: {
            "path": path,
            "bytes": 1,
            "sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
            "git_blob": "b" * 40,
            "last_change_commit": "c" * 40,
            "verified_at_head": head,
        }
        for path in protected_paths
    }
    frozen = config["frozen_science"]
    for path_key, hash_key in FROZEN_SCIENCE_FIELDS.items():
        path = frozen[path_key]
        records[path]["sha256"] = frozen[hash_key]
    calibration_config = config["calibration_evidence"]
    calibration_cloud: dict[str, dict] = {}
    calibration_bundles: dict[str, dict[str, dict]] = {}
    for cell_id in sorted(EXPECTED_CELLS):
        binding = calibration_config["cloud_manifests"][cell_id]
        path = binding["path"]
        records[path].update(
            bytes=binding["bytes"],
            sha256=binding["sha256"],
            last_change_commit=EVIDENCE_COMMIT,
        )
        calibration_cloud[cell_id] = records[path]
        calibration_bundles[cell_id] = {}
        for name, binding in calibration_config["bundles"][cell_id].items():
            path = binding["path"]
            records[path].update(
                bytes=binding["bytes"],
                sha256=binding["sha256"],
                last_change_commit=EVIDENCE_COMMIT,
            )
            calibration_bundles[cell_id][name] = records[path]
    focused_tests = list(inventory["focused_tests"]["paths"])
    absence = {
        "status": "PASS",
        "absent_file_count": inventory["pre_outcome_absent_files"]["count"],
        "absent_files": list(inventory["pre_outcome_absent_files"]["paths"]),
        "empty_or_absent_directory_count": inventory[
            "pre_outcome_empty_or_absent_directories"
        ]["count"],
        "empty_or_absent_directories": list(
            inventory["pre_outcome_empty_or_absent_directories"]["paths"]
        ),
    }
    return {
        "transport_id": config["transport_id"],
        "experiment_id": config["experiment_id"],
        "manifest_schema_version": FREEZE_SCHEMA_VERSION,
        "stage": "H4_holdout_transport_freeze_determination",
        "status": "PASS",
        "scientific_data_generated": False,
        "scientific_payload_or_outcome_inspected": False,
        "freeze_base_commit": head,
        "repository": {
            "head": head,
            "branch": config["repository"]["branch"],
            "upstream_ref": f"origin/{config['repository']['branch']}",
            "upstream_head": head,
            "origin_url": config["repository"]["url"],
            "remote_head": head,
        },
        "config": records[TRANSPORT_CONFIG_PATH],
        "frozen_science": {
            path: records[path] for path in inventory["frozen_science"]["paths"]
        },
        "calibration_evidence": {
            "protected_fetch_commit": EVIDENCE_COMMIT,
            "protected_fetch_completed_before_transport_freeze": True,
            "payload_or_outcome_inspected_before_transport_freeze": False,
            "verification_method": calibration_config["verification_method"],
            "cloud_manifests": calibration_cloud,
            "bundles": calibration_bundles,
        },
        "inventory_contract": inventory,
        "pre_outcome_absence_checks": absence,
        "transport_artifacts": {
            path: records[path]
            for path in inventory["required_transport_files"]["paths"]
        },
        "authenticated_bootstrap_archive_members": {
            path: records[path] for path in inventory["archive_members"]["paths"]
        },
        "protected_artifacts": records,
        "focused_tests": {
            "status": "PASS",
            "test_files": focused_tests,
            "command": ["python", "-m", "pytest", *focused_tests, "-q"],
            "returncode": 0,
            "stdout": "12 passed in 1.00s",
        },
        "freeze_base_artifact_verification": {
            "status": "PASS",
            "freeze_base_commit": head,
            "protected_record_count": inventory["protected_artifacts"]["count"],
            "paths": inventory["protected_artifacts"]["paths"],
            "method": (
                "git_show_freeze_base_path_blob_bytes_sha256_and_exact_"
                "last_change_ancestry"
            ),
        },
        "rule": "synthetic closed-schema fixture",
    }
def test_registered_config_binds_audit_hashes_and_protected_fetch() -> None:
    config = load_config()
    validate_config(config)
    frozen = config["frozen_science"]
    assert frozen == {
        "config_path": "configs/px057_h4_ltt_transfer_20260725.json",
        "config_sha256": "0df81f0bb86d60869424ba12156ccc306ce3df280d6cecd25857f98785d03317",
        "phase_a_freeze_path": "manifests/px057_h4_20260725/phase_a_freeze_v2.json",
        "phase_a_freeze_sha256": "e54e6aa573e42f4415d9a03bc129e25a96ba71d555ed631586364eca6aeaceff",
        "collector_path": "scripts/run_px057_h4_trace_collection.py",
        "collector_sha256": "e2472bc913114ab23e1ff2c70dc13d72a3b70c305c294951e4aada6045d9c64a",
        "common_path": "scripts/px057_h4_common.py",
        "common_sha256": "5e931441fada32e9e94a5eb6167597bc8def825796566190aab03257034df60f",
        "holdout_gate_path": "scripts/run_px057_h4_holdout_gate.py",
        "holdout_gate_sha256": "dbd85331717e4b99f485aa8a604d9fa15782a7670e726a19cc4c08845bc7ec70",
        "requirements_path": "requirements-px057-h4.txt",
        "requirements_sha256": "5aa1adf7ce4187838a9f2867c9e6919bb5b06e11f90d70194ab48fc09984d163",
        "calibration_evidence_commit": EVIDENCE_COMMIT,
    }
    evidence = config["calibration_evidence"]
    assert evidence["protected_fetch_commit"] == EVIDENCE_COMMIT
    assert evidence["protected_fetch_completed_before_transport_freeze"] is True
    assert evidence["payload_or_outcome_inspected_before_transport_freeze"] is False
    assert set(evidence["cloud_manifests"]) == EXPECTED_CELLS
    assert sum(len(files) for files in evidence["bundles"].values()) == 12


def test_bootstrap_and_collection_contract_are_complete() -> None:
    config = load_config()
    source = config["source"]
    lf_policy = "cloud_jobs/px057_h4_holdout_20260727/.gitattributes"
    assert {
        source["entrypoint"],
        source["calibration_entrypoint"],
        source["phase_a_entrypoint"],
    } <= set(source["archive_members"])
    assert {
        source["calibration_entrypoint"],
        source["phase_a_entrypoint"],
    } <= set(source["required_transport_files"])
    assert lf_policy in source["archive_members"]
    assert lf_policy in source["required_transport_files"]
    assert (ROOT / lf_policy).read_bytes() == b"* text eol=lf\n"
    assert config["freeze_schema_version"] == FREEZE_SCHEMA_VERSION
    assert config["aws"]["retry_strategy_omitted"] is True
    assert config["aws"]["enable_managed_spot_training"] is False
    assert config["collection"] == {
        "split": "holdout",
        "expected_traces": 300,
        "rounds": 8,
        "expected_generations": 2400,
        "files": [
            "selected_rows.jsonl",
            "reasoning_traces.jsonl",
            "raw_generations.jsonl",
            "collection_summary.json",
        ],
    }
    assert {
        cell["job_name"] for cell in config["cells"].values()
    } == {
        "px057-h4-hold-c1-r1-20260727",
        "px057-h4-hold-c2-r1-20260727",
        "px057-h4-hold-c3-r1-20260727",
    }
    inventory = expected_freeze_inventory(config)
    assert {name: value["count"] for name, value in inventory.items()} == {
        "frozen_science": 6,
        "calibration_cloud_manifests": 3,
        "calibration_bundle_files": 12,
        "calibration_evidence": 15,
        "required_transport_files": 11,
        "archive_members": 11,
        "protected_artifacts": 33,
        "focused_tests": 2,
        "pre_outcome_absent_files": 21,
        "pre_outcome_empty_or_absent_directories": 3,
    }


def test_calibration_verification_never_text_reads_scientific_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_config()
    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs):
        normalized = path.as_posix()
        if "/calibration/" in normalized:
            raise AssertionError(f"scientific payload was parsed: {normalized}")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    evidence = verify_calibration_evidence(ROOT, config)
    assert evidence["payload_or_outcome_inspected_before_transport_freeze"] is False
    assert sum(len(files) for files in evidence["bundles"].values()) == 12


def test_closed_freeze_schema_accepts_only_the_complete_exact_inventory() -> None:
    config = load_config()
    freeze = synthetic_valid_freeze(config)
    protected = validate_freeze_manifest_schema(config, freeze)
    assert len(protected) == 33
    assert set(protected) == set(
        expected_freeze_inventory(config)["protected_artifacts"]["paths"]
    )


def test_forged_pass_with_only_transport_and_science_records_is_rejected() -> None:
    config = load_config()
    freeze = synthetic_valid_freeze(config)
    retained = {
        TRANSPORT_CONFIG_PATH,
        *expected_freeze_inventory(config)["frozen_science"]["paths"],
    }
    freeze["protected_artifacts"] = {
        path: record
        for path, record in freeze["protected_artifacts"].items()
        if path in retained
    }
    with pytest.raises(ValueError, match="exact registered path set"):
        validate_freeze_manifest_schema(config, freeze)


def test_freeze_schema_rejects_missing_or_extra_category_records() -> None:
    config = load_config()
    missing = synthetic_valid_freeze(config)
    missing["calibration_evidence"]["bundles"]["cell1_llama31_gsm8k"].pop(
        "raw_generations.jsonl"
    )
    with pytest.raises(ValueError, match="bundle inventory is incomplete"):
        validate_freeze_manifest_schema(config, missing)

    extra = synthetic_valid_freeze(config)
    extra_record = copy.deepcopy(next(iter(extra["transport_artifacts"].values())))
    extra_record["path"] = "forged-extra.py"
    extra["transport_artifacts"]["forged-extra.py"] = extra_record
    with pytest.raises(ValueError, match="exact registered path set"):
        validate_freeze_manifest_schema(config, extra)


def test_freeze_schema_rejects_truncated_absence_or_skipped_tests() -> None:
    config = load_config()
    absence = synthetic_valid_freeze(config)
    absence["pre_outcome_absence_checks"]["absent_files"].pop()
    with pytest.raises(ValueError, match="absence inventory is incomplete"):
        validate_freeze_manifest_schema(config, absence)

    skipped = synthetic_valid_freeze(config)
    skipped["focused_tests"]["status"] = "SKIPPED"
    skipped["focused_tests"]["stdout"] = "2 skipped"
    with pytest.raises(ValueError, match="not executed successfully"):
        validate_freeze_manifest_schema(config, skipped)


def test_freeze_schema_rejects_repository_or_record_identity_ambiguity() -> None:
    config = load_config()
    repository = synthetic_valid_freeze(config)
    repository["repository"]["remote_head"] = "d" * 40
    with pytest.raises(ValueError, match="not self-consistent"):
        validate_freeze_manifest_schema(config, repository)

    record = synthetic_valid_freeze(config)
    path = record["inventory_contract"]["archive_members"]["paths"][0]
    record["authenticated_bootstrap_archive_members"][path]["path"] = "alias"
    with pytest.raises(ValueError, match="key/path mismatch"):
        validate_freeze_manifest_schema(config, record)


def test_exact_binding_rejects_worktree_tampering(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    initialize_repo(repo)
    artifact = repo / "artifact.bin"
    artifact.write_bytes(b"frozen\x00bytes\n")
    subprocess.run(["git", "add", "artifact.bin"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "freeze artifact"], cwd=repo, check=True)
    expected = hashlib.sha256(artifact.read_bytes()).hexdigest()
    verified = verify_binding(
        repo,
        {"path": "artifact.bin", "bytes": artifact.stat().st_size, "sha256": expected},
    )
    assert verified["sha256"] == expected

    artifact.write_bytes(b"changed\n")
    with pytest.raises(ValueError, match="differs from HEAD"):
        verify_binding(repo, {"path": "artifact.bin", "sha256": expected})


def test_freeze_base_rejects_transport_file_added_after_forged_old_base(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    initialize_repo(repo)
    seed = repo / "seed.txt"
    seed.write_text("pre-transport freeze base\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "old base"], cwd=repo, check=True)
    old_base = run_git(repo, "rev-parse", "HEAD")

    transport = repo / "scripts" / "post_base_transport.py"
    transport.parent.mkdir()
    transport.write_text("print('added later')\n", encoding="utf-8")
    subprocess.run(["git", "add", transport.relative_to(repo)], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "post-base transport"], cwd=repo, check=True
    )
    relative = transport.relative_to(repo).as_posix()
    content = transport.read_bytes()
    forged_record = {
        "path": relative,
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "git_blob": run_git(repo, "rev-parse", f"HEAD:{relative}"),
        "last_change_commit": run_git(
            repo, "log", "-1", "--format=%H", "--", relative
        ),
        "verified_at_head": old_base,
    }
    forged = {
        "freeze_base_commit": old_base,
        "protected_artifacts": {relative: forged_record},
    }
    with pytest.raises(ValueError, match="did not exist at freeze base"):
        verify_freeze_base_artifacts(repo, forged)


def test_absence_gate_rejects_ltt_and_holdout_evidence(tmp_path: Path) -> None:
    cells: dict[str, dict[str, str]] = {}
    for cell_id in sorted(EXPECTED_CELLS):
        base = f"evidence/{cell_id}"
        cells[cell_id] = {
            "ltt_determination": f"{base}/ltt_determination.json",
            "ltt_lock_manifest": f"{base}/ltt_lock.json",
            "launch_manifest": f"launches/{cell_id}.json",
            "cloud_manifest": f"cloud/{cell_id}.json",
            "manual_audit_blinded": f"{base}/manual_blinded.json",
            "manual_audit": f"{base}/manual.json",
            "holdout_determination": f"{base}/holdout_determination.json",
            "output_dir": f"{base}/holdout",
        }
    config = {"cells": cells}
    checks = require_no_outcome_or_holdout_evidence(tmp_path, config)
    assert len(checks["absent_files"]) == 21
    assert len(checks["empty_or_absent_directories"]) == 3

    ltt = tmp_path / cells["cell1_llama31_gsm8k"]["ltt_determination"]
    ltt.parent.mkdir(parents=True)
    ltt.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="LTT/holdout evidence exists"):
        require_no_outcome_or_holdout_evidence(tmp_path, config)


def test_clean_pushed_head_checks_live_remote_and_rejects_unpushed_commit(
    tmp_path: Path,
) -> None:
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    repo = tmp_path / "repo"
    branch = "agent/px057-h4-certified-transfer"
    initialize_repo(repo, branch=branch)
    tracked = repo / "tracked.txt"
    tracked.write_text("frozen\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repo, check=True)
    subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True)
    subprocess.run(["git", "push", "-q", "-u", "origin", branch], cwd=repo, check=True)
    registration = {"branch": branch, "url": str(remote)}
    state = require_clean_pushed_head(repo, registration)
    assert state["head"] == run_git(repo, "rev-parse", "HEAD")
    assert state["remote_head"] == state["head"]

    tracked.write_text("frozen\nnew commit\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "not pushed"], cwd=repo, check=True)
    with pytest.raises(ValueError, match="pushed upstream"):
        require_clean_pushed_head(repo, registration)


def test_config_rejects_posthoc_cell_or_retry_mutation() -> None:
    config = load_config()
    config["cells"].pop("cell3_llama31_arc")
    with pytest.raises(ValueError, match="three frozen H4 cells"):
        validate_config(config)

    config = load_config()
    config["rules"]["first_attempt_only"] = False
    with pytest.raises(ValueError, match="first-attempt-only"):
        validate_config(config)

    config = load_config()
    config["aws"]["retry_strategy_omitted"] = False
    with pytest.raises(ValueError, match="omit retry strategy"):
        validate_config(config)

    config = load_config()
    config["aws"]["enable_managed_spot_training"] = True
    with pytest.raises(ValueError, match="omit retry strategy"):
        validate_config(config)
