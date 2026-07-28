from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import scripts.adjudicate_px062_gate2_2 as v1_adjudicator
import scripts.build_px062_gate2_2_bundle as v1_bundle
import scripts.fetch_px062_gate2_2_results as v1_fetch
import scripts.launch_px062_gate2_2_registered as v1_launcher
import scripts.register_px062_gate2_2_fetch as v1_fetch_registrar
import scripts.register_px062_gate2_2_launch as v1_registrar
import scripts.adjudicate_px062_gate2_2_v11 as adjudicator
import scripts.build_px062_gate2_2_v11_bundle as bundle
import scripts.check_px062_gate2_2_v11_tokenizer_conformance as conformance
import scripts.fetch_px062_gate2_2_v11_results as fetcher
import scripts.launch_px062_gate2_2_v11_registered as launcher
import scripts.px062_gate2_2_v11_contract as contract
import scripts.register_px062_gate2_2_v11_fetch as fetch_registrar
import scripts.register_px062_gate2_2_v11_launch as registrar


ROOT = Path(__file__).resolve().parents[1]


def _frozen_case() -> tuple[dict, dict[str, bytes], dict]:
    inputs = {
        contract.TASKS_PATH: b'{"task_id":"t1"}\n',
        contract.ANSWER_KEY_PATH: b'{"task_id":"t1","expected_skill":null}\n',
        contract.CATALOG_PATH: b'{"entries":[]}\n',
        contract.BENCHMARK_MANIFEST_PATH: b'{"benchmark_status":"ready"}\n',
    }
    config = {
        "experiment_id": contract.EXPERIMENT_ID,
        "protocol_version": contract.PROTOCOL_VERSION,
        "status": contract.FINAL_CONFIG_STATUS,
        "collection_output_dir": contract.COLLECTION_OUTPUT_DIR,
        "frozen_inputs": {
            "tasks": contract.TASKS_PATH,
            "answer_key": contract.ANSWER_KEY_PATH,
            "registry_catalog": contract.CATALOG_PATH,
            "benchmark_manifest": contract.BENCHMARK_MANIFEST_PATH,
        },
        "source_integrity": {
            "tasks_sha256": hashlib.sha256(inputs[contract.TASKS_PATH]).hexdigest(),
            "answer_key_sha256": hashlib.sha256(
                inputs[contract.ANSWER_KEY_PATH]
            ).hexdigest(),
            "registry_catalog_sha256": hashlib.sha256(
                inputs[contract.CATALOG_PATH]
            ).hexdigest(),
            "benchmark_manifest_sha256": hashlib.sha256(
                inputs[contract.BENCHMARK_MANIFEST_PATH]
            ).hexdigest(),
        },
        "label_audit_protocol": {
            "runner_sha256": "a" * 64,
            "protocol_sha256": "b" * 64,
            "tests_sha256": "c" * 64,
        },
    }
    final_inputs = {
        name: {
            "sha256": hashlib.sha256(inputs[path]).hexdigest(),
            "bytes": len(inputs[path]),
        }
        for name, path in {
            "tasks.jsonl": contract.TASKS_PATH,
            "answer_key.jsonl": contract.ANSWER_KEY_PATH,
            "registry_catalog.json": contract.CATALOG_PATH,
            "benchmark_manifest.json": contract.BENCHMARK_MANIFEST_PATH,
        }.items()
    }
    resolution = {
        "status": contract.FINAL_RESOLUTION_STATUS,
        "all_labels_independently_agreed": True,
        "cross_audit_disagreement_task_ids": [],
        "audits": [{"slot": 1}, {"slot": 2}],
        "final_inputs": final_inputs,
    }
    return config, inputs, resolution


def test_current_v11_candidate_is_not_execution_ready():
    with pytest.raises(ValueError, match="not frozen"):
        contract.validate_label_freeze(ROOT)


def test_frozen_config_and_resolution_gate_is_strict():
    config, inputs, resolution = _frozen_case()
    contract.validate_frozen_config(config, input_bytes=inputs)
    contract.validate_final_resolution(resolution, inputs)

    drifted = json.loads(json.dumps(config))
    drifted["status"] = "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT"
    with pytest.raises(ValueError, match="not frozen"):
        contract.validate_frozen_config(drifted, input_bytes=inputs)
    resolution["cross_audit_disagreement_task_ids"] = ["t1"]
    with pytest.raises(ValueError, match="disagreements"):
        contract.validate_final_resolution(resolution, inputs)


def test_v11_bundle_is_answer_key_blind_and_uses_only_v11_inputs():
    assert contract.ANSWER_KEY_PATH not in bundle.ARCHIVE_MEMBERS
    assert set(bundle.ARCHIVE_MEMBERS) >= {
        contract.CONFIG_PATH,
        contract.TASKS_PATH,
        contract.CATALOG_PATH,
        contract.BENCHMARK_MANIFEST_PATH,
    }
    assert all("gate2_2_context_structured_20260728/frozen_inputs" not in path for path in bundle.ARCHIVE_MEMBERS)


def test_importing_wrappers_does_not_mutate_v1_module_contracts():
    assert v1_bundle.CONFIG.endswith("v1_0_20260728.json")
    assert v1_registrar.PREFIX.endswith("gate2-2-context-structured-20260728")
    assert v1_launcher.EXPECTED_CONFIG.endswith("v1_0_20260728.json")
    assert v1_fetch.CONFIG_PATH.endswith("v1_0_20260728.json")
    assert v1_fetch_registrar.ADJUDICATOR_PATH == "scripts/adjudicate_px062_gate2_2.py"
    assert v1_adjudicator.ADJUDICATOR_PATH == "scripts/adjudicate_px062_gate2_2.py"


def test_context_bindings_are_scoped_and_restored():
    original_prefix = v1_registrar.PREFIX
    original_fetch_prefix = v1_fetch.PX062_GATE22_PREFIX
    with registrar._bound_core():
        assert v1_registrar.PREFIX == contract.S3_PREFIX
        assert v1_fetch.PX062_GATE22_PREFIX == contract.S3_PREFIX
        assert v1_registrar.CONFIG == contract.CONFIG_PATH
    assert v1_registrar.PREFIX == original_prefix
    assert v1_fetch.PX062_GATE22_PREFIX == original_fetch_prefix

    with fetcher.bound_core():
        assert v1_fetch.CONFIG_PATH == contract.CONFIG_PATH
        assert v1_fetch.SOURCE_GIT_PATHS == fetcher.SOURCE_GIT_PATHS
    assert v1_fetch.CONFIG_PATH.endswith("v1_0_20260728.json")


def test_registrar_fails_before_delegation_or_aws(monkeypatch):
    delegated = []
    monkeypatch.setattr(
        registrar,
        "validate_label_freeze",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("freeze blocked")),
    )
    monkeypatch.setattr(registrar, "_CORE_REGISTER", lambda **kwargs: delegated.append(kwargs))
    with pytest.raises(ValueError, match="freeze blocked"):
        registrar.register(
            root=ROOT,
            profile="praxis-build",
            source_commit="a" * 40,
            job_name=contract.DEFAULT_JOB_NAME,
            bucket="bucket",
            region="us-east-1",
            role_arn="arn:role",
            image="image@sha256:" + "0" * 64,
        )
    assert delegated == []


def test_conformance_refuses_pending_labels_before_loading_models(tmp_path, monkeypatch):
    delegated = []
    monkeypatch.setattr(conformance.core, "run_check", lambda **kwargs: delegated.append(kwargs))
    with pytest.raises(ValueError, match="not frozen"):
        conformance.run_check(
            config_path=ROOT / contract.CONFIG_PATH,
            tasks_path=ROOT / contract.TASKS_PATH,
            catalog_path=ROOT / contract.CATALOG_PATH,
            output_path=tmp_path / "receipt.json",
            checked_at_utc="2026-07-28T20:00:00Z",
            local_files_only=True,
        )
    assert delegated == []
    assert not (tmp_path / "receipt.json").exists()


def test_all_cloud_defaults_are_v11_specific():
    assert registrar.DEFAULT_JOB_NAME == "px062-g22-v11-confirm1-20260728"
    assert registrar.MANIFEST_DIR == contract.MANIFEST_DIR
    assert launcher.DEFAULT_REGISTRATION.parent == contract.MANIFEST_DIR
    assert fetcher.DEFAULT_COMPLETION_REGISTRATION.parent == contract.MANIFEST_DIR
    assert fetcher.DEFAULT_DESTINATION == contract.SEALED_CONFIRMATION_DIR
    assert fetch_registrar.DEFAULT_ADJUDICATION_RESULT == contract.CONFIRMATORY_RESULT_PATH
    assert adjudicator.DEFAULT_REGISTRATION.parent == contract.MANIFEST_DIR


def test_v11_policies_are_least_prefix_scoped():
    expected_fragment = "gate2-2-context-structured-v1-1-20260728"
    old_fragment = "gate2-2-context-structured-20260728/"
    for relative in (
        contract.SAGEMAKER_POLICY_PATH,
        contract.OPERATOR_FETCH_POLICY_PATH,
    ):
        raw = (ROOT / relative).read_text(encoding="utf-8")
        policy = json.loads(raw)
        assert policy["Version"] == "2012-10-17"
        assert expected_fragment in raw
        assert old_fragment not in raw
        assert "arn:aws:s3:::*" not in raw


def test_post_conformance_pin_remains_an_explicit_blocker():
    assert registrar.EXPECTED_CONTEXT_HEADROOM is None
    assert (
        adjudicator.FROZEN_CONFIG_CONTRACT_SHA256
        == contract.EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256
    )
