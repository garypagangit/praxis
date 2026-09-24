from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import build_px062_gate2_2_v12_benchmark as builder
from scripts import finalize_px062_gate2_2_v12_labels as finalizer
from scripts import run_px062_gate2_2_v12_blind_audit as audit
from scripts.generate_px062_gate2_2_v1_2_construction import construction
from scripts.verify_px062_gate2_2_v12_label_audits import verify


PRESERVED_HASHES = {
    "scripts/build_px062_gate2_2_benchmark.py": "111f686080a75593594967b0aa5deebe58df8150dbd56bc1664bf4571022580f",
    "scripts/run_px062_gate2_2_blind_audit.py": "d8b3dc1e501a24c219e462ae19f2687aa20e1c730a10e951958dae4e413492ba",
    "scripts/verify_px062_gate2_2_label_audits.py": "df37dbd86c2827a451a139641e3f2aca2b0cc8dbb9bdda784bd47d9ed2b0d17a",
    "scripts/finalize_px062_gate2_2_labels.py": "be176a40327e131152d16270c587a6505dd9749dda99e9288f6d96e31d2d4467",
    "tests/test_px062_gate2_2_blind_audit.py": "4a3e451ab64093c033338536a27fc1c13aaccacb18fbbdff52eb7a46e9d8ffb6",
    "scripts/build_px062_gate2_2_v11_benchmark.py": "8006f1a16ee356b26fa214a42bdeb72f8213641a59d32e2899939d937e0261a3",
    "scripts/run_px062_gate2_2_v11_blind_audit.py": "9c63a20c0412102d5533fca9ef90b561311bfe44f74dfc203064c06e8dc532d1",
    "scripts/verify_px062_gate2_2_v11_label_audits.py": "64a723b952105bf4ec4bf3b4cf8a684fe3ca8fb5d79f0d7972f9814997fe4fc1",
    "scripts/finalize_px062_gate2_2_v11_labels.py": "493cf1d92bedf34b5e44ed600b65e33215dd1958d22fe1d4378931e3d75ba5d7",
    "tests/test_px062_gate2_2_v11_blind_audit.py": "eba6cac7b6a7c7f5ed28c97485d12ab7f895dbf4a019106c9740084e50b9cf26",
    "reports/coding_agent_skill_provenance/gate2_2_context_structured_v1_1_20260728/LABEL_AUDIT_PROTOCOL_V1_1_20260728.md": "dade0ff8e9e92953f376476fdb7adba4e6510b801df407f28638f36ee714b410",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b"\n"
        for row in rows
    )


def test_v1_and_v11_audit_pipelines_are_byte_exact() -> None:
    for relative, expected in PRESERVED_HASHES.items():
        assert digest(audit.ROOT / relative) == expected


def test_v12_frozen_hashes_projection_and_full_batches() -> None:
    tasks_raw = audit.TASKS_PATH.read_bytes()
    catalog_raw = audit.CATALOG_PATH.read_bytes()
    assert digest(audit.TASKS_PATH) == audit.EXPECTED_TASKS_SHA256
    assert digest(audit.CATALOG_PATH) == audit.EXPECTED_CATALOG_SHA256
    tasks = audit.read_jsonl_bytes(tasks_raw, "v1.2 tasks")
    _, names, semantic_registry = audit.load_catalog(catalog_raw)
    audit.validate_tasks(tasks, names)
    batches = audit.make_batches(tasks)
    assert len(batches) == 43
    assert {len(batch) for batch in batches} == {24}
    assert sum(map(len, batches)) == 1032
    projected = [
        row for batch in batches for row in audit.project_tasks_for_auditor(batch)
    ]
    assert all(list(row) == ["task_id", "prompt"] for row in projected)
    prompt = audit.build_prompt(1, batches[0], semantic_registry).decode("utf-8")
    assert "option_map" not in prompt
    assert "gate2_2_context_structured_v1_2_20260728" in audit.output_paths(
        audit.ROOT, 1
    )["audit"].as_posix()


def test_v12_checkpoint_tracks_wrapper_core_protocol_tests_and_inputs() -> None:
    tracked = {path.as_posix() for path in audit.TRACKED_CHECKPOINT_PATHS}
    assert {
        audit.RUNNER_RELATIVE_PATH.as_posix(),
        audit.CORE_RELATIVE_PATH.as_posix(),
        audit.PROTOCOL_RELATIVE_PATH.as_posix(),
        audit.TESTS_RELATIVE_PATH.as_posix(),
        audit.CONFIG_RELATIVE_PATH.as_posix(),
        audit.SEED_RELATIVE_PATH.as_posix(),
        audit.ANSWER_RELATIVE_PATH.as_posix(),
        audit.MANIFEST_RELATIVE_PATH.as_posix(),
    } <= tracked
    assert "gate2_2_context_structured_v1_1_20260728" not in "\n".join(tracked)
    assert builder.CHECKPOINT_TRACKED_PATHS == tuple(
        path.as_posix() for path in audit.TRACKED_CHECKPOINT_PATHS
    )


def _write_verifier_fixture(directory: Path) -> tuple[Path, Path, Path, list[Path]]:
    names = [f"skill-{index:02d}" for index in range(43)]
    catalog = {
        "names": names,
        "entries": [
            {"name": name, "description": f"Description {index}"}
            for index, name in enumerate(names)
        ],
    }
    tasks = [{"task_id": f"task-{index:04d}", "prompt": "x"} for index in range(1032)]
    answers = [
        {
            "task_id": row["task_id"],
            "expected_skill": names[index % 43] if index % 2 else None,
        }
        for index, row in enumerate(tasks)
    ]
    predictions = [
        {
            "task_id": answer["task_id"],
            "predicted_skill": answer["expected_skill"],
            "confidence": "high",
            "note": "The frozen catalog has exactly this fit or no applicable skill.",
        }
        for answer in answers
    ]
    tasks_path = directory / "tasks.jsonl"
    answers_path = directory / "answer_key.jsonl"
    catalog_path = directory / "registry_catalog.json"
    audit_paths = [directory / "audit_1.jsonl", directory / "audit_2.jsonl"]
    tasks_path.write_bytes(jsonl_bytes(tasks))
    answers_path.write_bytes(jsonl_bytes(answers))
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8", newline="\n")
    for path in audit_paths:
        path.write_bytes(jsonl_bytes(predictions))
    return tasks_path, answers_path, catalog_path, audit_paths


def test_verifier_requires_two_fresh_full_unanimous_audits(tmp_path: Path) -> None:
    tasks, answers, catalog, audits = _write_verifier_fixture(tmp_path)
    result = verify(tasks, answers, audits, catalog)
    assert result["schema_version"] == (
        "px062-gate2.2-v1.2-label-audit-resolution-v1"
    )
    assert result["all_labels_independently_agreed"] is True
    assert [row["rows"] for row in result["audits"]] == [1032, 1032]
    with pytest.raises(ValueError, match="exactly two distinct"):
        verify(tasks, answers, [audits[0]], catalog)
    rows = [json.loads(line) for line in audits[1].read_text().splitlines()]
    rows[0]["predicted_skill"] = "skill-00"
    audits[1].write_bytes(jsonl_bytes(rows))
    with pytest.raises(ValueError, match="unanimously"):
        verify(tasks, answers, audits, catalog)


def test_finalizer_accepts_only_unanimous_v12_pair(tmp_path: Path) -> None:
    tasks, answers, catalog, audits = _write_verifier_fixture(tmp_path)
    verification = verify(tasks, answers, audits, catalog)
    pair = {
        "audits": [
            {
                "slot": slot,
                "model": audit.SLOT_MODELS[slot],
                "sidecar_sha256": f"{slot}" * 64,
                "accepted_session_ids": [f"fresh-v12-s{slot}-{index}" for index in range(43)],
            }
            for slot in (1, 2)
        ]
    }
    resolution = finalizer.build_provisional_resolution(
        verification=verification,
        candidate_tasks_path="v1.2/tasks.jsonl",
        candidate_answer_path="v1.2/answer_key.jsonl",
        audit_paths=list(builder.CANONICAL_AUDIT_PATHS),
        canonical_pair=pair,
    )
    assert resolution["all_labels_independently_agreed"] is True
    assert [row["rows"] for row in resolution["audits"]] == [1032, 1032]
    rejected = dict(verification)
    rejected["all_labels_independently_agreed"] = False
    with pytest.raises(ValueError, match="unanimous"):
        finalizer.build_provisional_resolution(
            verification=rejected,
            candidate_tasks_path="v1.2/tasks.jsonl",
            candidate_answer_path="v1.2/answer_key.jsonl",
            audit_paths=list(builder.CANONICAL_AUDIT_PATHS),
            canonical_pair=pair,
        )


def test_builder_and_generator_reproduce_pending_v12_bytes() -> None:
    files = builder.build_artifacts(
        root=builder.ROOT,
        seed_bank_path=builder.ROOT / builder.DEFAULT_SEED_BANK,
        registry_path=builder.ROOT / builder.DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=builder.ROOT / builder.DEFAULT_PRIOR_TASKS,
    )
    for name, raw in files.items():
        assert raw == (builder.ROOT / builder.DEFAULT_OUTPUT_DIR / name).read_bytes()
    outputs = construction(audit.ROOT)
    for path, raw in outputs.items():
        assert raw == (audit.ROOT / path).read_bytes()


def test_config_anchors_exact_v12_sources_protocol_runner_and_tests() -> None:
    config = json.loads((audit.ROOT / audit.CONFIG_RELATIVE_PATH).read_text())
    expected = audit.expected_label_audit_protocol_config(
        runner_sha256=digest(audit.ROOT / audit.RUNNER_RELATIVE_PATH),
        protocol_sha256=digest(audit.ROOT / audit.PROTOCOL_RELATIVE_PATH),
        tests_sha256=digest(audit.ROOT / audit.TESTS_RELATIVE_PATH),
    )
    assert config["experiment_id"] == (
        "px062-skill-selection-gate2-2-v1-2-20260728"
    )
    assert config["protocol_version"] == "2.2.2"
    assert config["label_audit_protocol"] == expected
    assert config["source_integrity"] == {
        "tasks_sha256": "e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16",
        "answer_key_sha256": "c9fb2c8be3ee200050f709a046109c42884aea741e980371837bd58f741f3913",
        "registry_catalog_sha256": "90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212",
        "benchmark_manifest_sha256": "93a126f0fed68d259caae32bd2a0eae8af4f656bbebdcda07dac880aa9e3eb57",
    }


def test_old_audits_cannot_be_used_as_v12_slots() -> None:
    assert all(
        "gate2_2_context_structured_v1_2_20260728" in path
        for path in builder.CANONICAL_AUDIT_PATHS
    )
    assert all("v1_1" not in path for path in builder.CANONICAL_AUDIT_PATHS)
    assert finalizer.CORE_DEPENDENCIES == (
        "scripts/finalize_px062_gate2_2_v11_labels.py",
        "scripts/build_px062_gate2_2_v12_benchmark.py",
        "scripts/verify_px062_gate2_2_v12_label_audits.py",
    )
