from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.build_px062_gate2_2_benchmark import (
    AUDITED_LABEL_STATUS,
    ANSWER_FIELDS,
    AVAILABLE_PER_SKILL,
    CANONICAL_AUDIT_MODELS,
    CANONICAL_AUDIT_PAIR_MANIFEST_PATH,
    CANONICAL_AUDIT_PATHS,
    CANONICAL_AUDIT_SIDECAR_PATHS,
    CHECKPOINT_CONFIG_PATH,
    CHECKPOINT_PROTOCOL_PATH,
    CHECKPOINT_RUNNER_PATH,
    CHECKPOINT_TESTS_PATH,
    CHECKPOINT_TRACKED_PATHS,
    DEFAULT_PRIOR_TASKS,
    DEFAULT_REGISTRY_INVENTORY,
    DEFAULT_SEED_BANK,
    EXPECTED_NONE_LABELS,
    EXPECTED_REAL_LABELS,
    EXPECTED_SKILLS,
    EXPECTED_TASKS,
    LEXICAL_BALANCED_ACCURACY_LIMIT,
    LEXICAL_CV_SEED,
    MISLEADING_REAL_PER_SKILL,
    PENDING_LABEL_STATUS,
    OPTION_MAP_SALT,
    REPEATED_PHRASE_NONE_RECALL_LIMIT,
    ROOT,
    TASK_FIELDS,
    TASK_ID_NAMESPACE,
    attach_label_independent_option_maps,
    build_artifacts,
    build_candidates,
    canonical_json_bytes,
    canonical_jsonl_bytes,
    collection_task_fingerprint,
    evaluate_repeated_phrase_rule,
    load_registry,
    normalize_text,
    read_json,
    read_jsonl,
    sha256_bytes,
    validate_freshness,
    validate_canonical_pair_evidence,
    validate_label_governance,
    validate_no_catalog_copy,
    validate_no_canonical_answer_mentions,
    write_artifacts,
)
from scripts.finalize_px062_gate2_2_labels import (
    prepare_finalization,
    pretty_json_bytes,
)
from scripts.verify_px062_gate2_2_label_audits import verify as verify_label_audits


def parse_jsonl(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line]


@pytest.fixture(scope="module")
def frozen_files() -> dict[str, bytes]:
    return build_artifacts(
        root=ROOT,
        seed_bank_path=ROOT / DEFAULT_SEED_BANK,
        registry_path=ROOT / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=ROOT / DEFAULT_PRIOR_TASKS,
    )


@pytest.fixture(scope="module")
def synthetic_finalization_plan(tmp_path_factory, frozen_files):
    directory = tmp_path_factory.mktemp("px062-g22-label-finalization")
    candidate_dir = directory / "candidate"
    candidate_dir.mkdir()
    for name, raw in frozen_files.items():
        (candidate_dir / name).write_bytes(raw)
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    audit_raws = []
    for auditor in (1, 2):
        rows = [
            {
                "task_id": row["task_id"],
                "predicted_skill": row["expected_skill"],
                "confidence": "high" if auditor == 1 else "medium",
                "note": f"synthetic independent auditor {auditor}",
            }
            for row in answers
        ]
        audit_raws.append(canonical_jsonl_bytes(rows))
    checkpoint_candidate_raws = {
        CHECKPOINT_TRACKED_PATHS[0]: frozen_files["tasks.jsonl"],
        CHECKPOINT_TRACKED_PATHS[1]: frozen_files["registry_catalog.json"],
        CHECKPOINT_TRACKED_PATHS[2]: frozen_files["answer_key.jsonl"],
        CHECKPOINT_TRACKED_PATHS[3]: frozen_files["benchmark_manifest.json"],
    }
    tracked_files = {}
    for index, path in enumerate(CHECKPOINT_TRACKED_PATHS, 1):
        raw = checkpoint_candidate_raws.get(path, f"synthetic:{path}\n".encode())
        tracked_files[path] = {
            "head_blob": f"{index:040x}",
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
        }
    repository_checkpoint = {
        "schema_version": "px062-gate2.2-repository-checkpoint-v1",
        "head_commit": "a" * 40,
        "branch": "synthetic-checkpoint",
        "upstream_ref": "origin/synthetic-checkpoint",
        "upstream_commit": "a" * 40,
        "remote_ref": "refs/heads/synthetic-checkpoint",
        "remote_commit": "a" * 40,
        "tracked_tree_clean": True,
        "tracked_files": tracked_files,
        "config_sha256": tracked_files[CHECKPOINT_CONFIG_PATH]["sha256"],
        "source_integrity": {
            "tasks_sha256": sha256_bytes(frozen_files["tasks.jsonl"]),
            "answer_key_sha256": sha256_bytes(frozen_files["answer_key.jsonl"]),
            "registry_catalog_sha256": sha256_bytes(
                frozen_files["registry_catalog.json"]
            ),
            "benchmark_manifest_sha256": sha256_bytes(
                frozen_files["benchmark_manifest.json"]
            ),
        },
        "pending_answer_sha256": sha256_bytes(frozen_files["answer_key.jsonl"]),
        "answer_pending_rows": 1032,
        "seed_governance": {
            "required": 2,
            "completed": 0,
            "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
            "audit_1_status": "PENDING",
            "audit_2_status": "PENDING",
            "resolution_status": "PENDING",
        },
        "label_audit_protocol": {
            "codex_cli_version": "synthetic-codex-cli",
            "slot_models": {
                "1": CANONICAL_AUDIT_MODELS[0],
                "2": CANONICAL_AUDIT_MODELS[1],
            },
            "model_reasoning_effort": "high",
            "sampling_parameters": "synthetic model defaults",
            "batches_per_auditor": 43,
            "tasks_per_batch": 24,
            "stateless_ephemeral_sessions": True,
            "prompt_template_sha256": "b" * 64,
            "runner_sha256": tracked_files[CHECKPOINT_RUNNER_PATH]["sha256"],
            "protocol_sha256": tracked_files[CHECKPOINT_PROTOCOL_PATH]["sha256"],
            "tests_sha256": tracked_files[CHECKPOINT_TESTS_PATH]["sha256"],
            "model_facing_task_fields": ["task_id", "prompt"],
            "option_map_withheld_from_auditors": True,
            "exact_command_shape": "synthetic exact read-only command",
            "acceptance": "both sealed audits and the pending answer must agree",
        },
        "canonical_outputs": {
            str(slot): {
                "predictions": CANONICAL_AUDIT_PATHS[slot - 1],
                "sidecar": CANONICAL_AUDIT_SIDECAR_PATHS[slot - 1],
            }
            for slot in (1, 2)
        },
    }
    sidecar_raws = [
        pretty_json_bytes(
            {
                "slot": slot,
                "synthetic_trusted_fixture": True,
                "repository_checkpoint": repository_checkpoint,
            }
        )
        for slot in (1, 2)
    ]
    manifest_audits = [
        {
            "slot": slot,
            "model": CANONICAL_AUDIT_MODELS[slot - 1],
            "audit_id": f"synthetic-audit-{slot}",
            "accepted_session_ids": [
                f"synthetic-slot-{slot}-session-{index:02d}"
                for index in range(1, 44)
            ],
            "prediction_sha256": sha256_bytes(audit_raws[slot - 1]),
            "sidecar_sha256": sha256_bytes(sidecar_raws[slot - 1]),
        }
        for slot in (1, 2)
    ]
    pair_manifest = {
        "schema_version": "px062-gate2.2-label-audit-evidence-manifest-v1",
        "created_utc": "2026-07-28T12:00:00Z",
        "answer_key_contents_included": False,
        "pending_answer_checkpoint_hash_included": True,
        "repository_checkpoint": repository_checkpoint,
        "audits": manifest_audits,
        "global_session_ids": {
            "accepted_count": 86,
            "all_attempt_count": 86,
            "all_unique_and_cross_audit_disjoint": True,
        },
        "isolated_workdirs": {
            "attempt_count": 86,
            "all_unique": True,
        },
        "cross_audit_input_prompt_schema_hashes_match": True,
        "artifacts": [
            item
            for slot in (1, 2)
            for item in (
                {
                    "role": f"slot_{slot}_predictions",
                    "path": CANONICAL_AUDIT_PATHS[slot - 1],
                    "bytes": len(audit_raws[slot - 1]),
                    "sha256": sha256_bytes(audit_raws[slot - 1]),
                },
                {
                    "role": f"slot_{slot}_sidecar",
                    "path": CANONICAL_AUDIT_SIDECAR_PATHS[slot - 1],
                    "bytes": len(sidecar_raws[slot - 1]),
                    "sha256": sha256_bytes(sidecar_raws[slot - 1]),
                },
            )
        ],
    }
    pair_manifest_raw = pretty_json_bytes(pair_manifest)
    evidence_overrides = {
        CANONICAL_AUDIT_PATHS[0]: audit_raws[0],
        CANONICAL_AUDIT_PATHS[1]: audit_raws[1],
        CANONICAL_AUDIT_SIDECAR_PATHS[0]: sidecar_raws[0],
        CANONICAL_AUDIT_SIDECAR_PATHS[1]: sidecar_raws[1],
        CANONICAL_AUDIT_PAIR_MANIFEST_PATH: pair_manifest_raw,
    }
    verifier_calls = []

    def trusted_pair_verifier(root, *, write_manifest):
        verifier_calls.append((root, write_manifest))
        rebuilt = deepcopy(pair_manifest)
        rebuilt["created_utc"] = "2099-01-01T00:00:00Z"
        return rebuilt

    provisional_path = directory / "provisional_resolution.json"
    final_path = directory / "final_resolution.json"
    plan = prepare_finalization(
        root=ROOT,
        seed_bank_path=ROOT / DEFAULT_SEED_BANK,
        registry_path=ROOT / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=ROOT / DEFAULT_PRIOR_TASKS,
        candidate_dir=candidate_dir,
        provisional_resolution_path=provisional_path,
        final_resolution_path=final_path,
        evidence_overrides=evidence_overrides,
        pair_verifier=trusted_pair_verifier,
    )
    assert not provisional_path.exists()
    assert not final_path.exists()
    plan["_test_evidence_overrides"] = evidence_overrides
    plan["_test_pair_manifest"] = pair_manifest
    plan["_test_pair_verifier"] = trusted_pair_verifier
    plan["_test_pair_verifier_calls"] = verifier_calls
    return plan


def run_staged_label_verifier(
    directory: Path,
    plan: dict,
    *,
    audit_raws: list[bytes] | None = None,
    catalog_raw: bytes | None = None,
) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    tasks_path = directory / "tasks.jsonl"
    answer_path = directory / "answer_key.jsonl"
    catalog_path = directory / "registry_catalog.json"
    audit_paths = [directory / "audit_1.jsonl", directory / "audit_2.jsonl"]
    tasks_path.write_bytes(plan["candidate_files"]["tasks.jsonl"])
    answer_path.write_bytes(plan["candidate_files"]["answer_key.jsonl"])
    catalog_path.write_bytes(
        catalog_raw or plan["candidate_files"]["registry_catalog.json"]
    )
    raws = audit_raws or [
        plan["_test_evidence_overrides"][path] for path in CANONICAL_AUDIT_PATHS
    ]
    for path, raw in zip(audit_paths, raws, strict=True):
        path.write_bytes(raw)
    return verify_label_audits(tasks_path, answer_path, audit_paths, catalog_path)


def pair_candidate_inputs(plan: dict) -> dict[str, bytes]:
    return {
        "candidate_tasks_raw": plan["candidate_files"]["tasks.jsonl"],
        "candidate_answers_raw": plan["candidate_files"]["answer_key.jsonl"],
        "candidate_catalog_raw": plan["candidate_files"]["registry_catalog.json"],
        "candidate_manifest_raw": plan["candidate_files"]["benchmark_manifest.json"],
    }


def test_exact_1032_balance_and_per_skill_coverage(frozen_files):
    tasks = parse_jsonl(frozen_files["tasks.jsonl"])
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    catalog = json.loads(frozen_files["registry_catalog.json"])

    assert len(tasks) == len(answers) == EXPECTED_TASKS == 1032
    assert catalog["count"] == EXPECTED_SKILLS == 43
    assert len(set(catalog["names"])) == EXPECTED_SKILLS
    assert sum(row["expected_skill"] is not None for row in answers) == EXPECTED_REAL_LABELS
    assert sum(row["expected_skill"] is None for row in answers) == EXPECTED_NONE_LABELS

    types = Counter(row["task_type"] for row in answers)
    assert types == {
        "available_single_skill": 344,
        "unavailable_capability": 344,
        "misleading_name_real_skill": 172,
        "misleading_name_none": 172,
    }
    available = Counter(
        row["expected_skill"]
        for row in answers
        if row["task_type"] == "available_single_skill"
    )
    misleading_real = Counter(
        row["expected_skill"]
        for row in answers
        if row["task_type"] == "misleading_name_real_skill"
    )
    assert set(available) == set(catalog["names"])
    assert set(misleading_real) == set(catalog["names"])
    assert set(available.values()) == {AVAILABLE_PER_SKILL}
    assert set(misleading_real.values()) == {MISLEADING_REAL_PER_SKILL}


def test_collection_tasks_are_blinded_and_answer_key_is_separate(frozen_files):
    tasks = parse_jsonl(frozen_files["tasks.jsonl"])
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    assert all(set(row) == TASK_FIELDS for row in tasks)
    assert all(set(row) == ANSWER_FIELDS for row in answers)
    assert [row["task_id"] for row in tasks] == [row["task_id"] for row in answers]
    forbidden = {
        "expected_skill",
        "task_type",
        "presented_nonexistent_name",
        "seed_fingerprint",
        "label_audit_status",
    }
    assert all(not (set(row) & forbidden) for row in tasks)
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["collection_blinding"] == {
        "answer_key_must_be_excluded_from_model_collection_bundle": True,
        "tasks_file_contains_labels": False,
    }
    assert {row["label_audit_status"] for row in answers} == {
        "PENDING_TWO_INDEPENDENT_AUDITS"
    }


def test_option_maps_are_complete_deterministic_and_position_balanced(frozen_files):
    tasks = parse_jsonl(frozen_files["tasks.jsonl"])
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    catalog = json.loads(frozen_files["registry_catalog.json"])
    expected_values = {*catalog["names"], None}
    expected_ids = [f"S{position:03d}" for position in range(1, 45)]
    positions = {value: Counter() for value in expected_values}
    scaffold_positions = {
        scaffold: {value: Counter() for value in expected_values}
        for scaffold in ("direct", "misleading")
    }

    for task in tasks:
        scaffold = (
            "direct" if task["prompt"].startswith("User request: ") else "misleading"
        )
        option_map = task["option_map"]
        assert [item["id"] for item in option_map] == expected_ids
        assert {item["skill"] for item in option_map} == expected_values
        assert all(set(item) == {"id", "skill"} for item in option_map)
        for position, item in enumerate(option_map, 1):
            positions[item["skill"]][position] += 1
            scaffold_positions[scaffold][item["skill"]][position] += 1

    assert {
        count for per_choice in positions.values() for count in per_choice.values()
    } == {23, 24}
    assert all(set(per_choice) == set(range(1, 45)) for per_choice in positions.values())
    assert {
        count
        for per_choice in scaffold_positions["direct"].values()
        for count in per_choice.values()
    } == {15, 16}
    assert {
        count
        for per_choice in scaffold_positions["misleading"].values()
        for count in per_choice.values()
    } == {7, 8}
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["option_map_balance"]["choice_count"] == 44
    assert manifest["option_map_balance"]["per_choice_per_position_min"] == 23
    assert manifest["option_map_balance"]["per_choice_per_position_max"] == 24
    assert manifest["option_map_balance"]["by_observable_scaffold"] == {
        "direct": {
            "tasks": 688,
            "per_choice_per_position_min": 15,
            "per_choice_per_position_max": 16,
        },
        "misleading": {
            "tasks": 344,
            "per_choice_per_position_min": 7,
            "per_choice_per_position_max": 8,
        },
    }
    construction = manifest["option_map_balance"]["construction"]
    assert construction["salt"] == OPTION_MAP_SALT
    assert construction["scaffold_rotation_offsets"] == {
        "direct": 0,
        "misleading": 28,
    }
    assert construction["private_answer_fields_used"] == []
    assert construction["label_independent"] is True

    correct_by_type = {
        task_type: Counter()
        for task_type in {
            "available_single_skill",
            "unavailable_capability",
            "misleading_name_real_skill",
            "misleading_name_none",
        }
    }
    correct_by_label = {"REGISTERED": Counter(), "NONE": Counter()}
    correct_overall = Counter()
    for task, answer in zip(tasks, answers, strict=True):
        position = next(
            index
            for index, item in enumerate(task["option_map"], 1)
            if item["skill"] == answer["expected_skill"]
        )
        correct_by_type[answer["task_type"]][position] += 1
        label = "NONE" if answer["expected_skill"] is None else "REGISTERED"
        correct_by_label[label][position] += 1
        correct_overall[position] += 1

    diagnostics = manifest["option_map_balance"]["correct_answer_positions"]
    labeled = lambda counter: {
        f"S{position:03d}": counter[position] for position in range(1, 45)
    }
    assert diagnostics["by_task_type"] == {
        task_type: labeled(counter)
        for task_type, counter in sorted(correct_by_type.items())
    }
    assert diagnostics["by_expected_label"] == {
        label: labeled(counter) for label, counter in sorted(correct_by_label.items())
    }
    assert diagnostics["overall"] == labeled(correct_overall)
    minimum_maximum = lambda counter: [
        min(counter[position] for position in range(1, 45)),
        max(counter[position] for position in range(1, 45)),
    ]
    assert diagnostics["by_task_type_min_max"] == {
        task_type: minimum_maximum(counter)
        for task_type, counter in sorted(correct_by_type.items())
    }
    assert diagnostics["by_expected_label_min_max"] == {
        label: minimum_maximum(counter)
        for label, counter in sorted(correct_by_label.items())
    }
    assert diagnostics["overall_min_max"] == minimum_maximum(correct_overall)
    assert diagnostics["diagnostic_only_not_used_for_construction_or_acceptance"] is True
    assert diagnostics["overall_min_max"] != [23, 24]


def test_task_ids_and_option_maps_are_information_flow_independent_of_labels():
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    names, _, _ = load_registry(
        ROOT / DEFAULT_REGISTRY_INVENTORY, seed["registry_corpus"]
    )
    original = build_candidates(seed, names)
    perturbed = deepcopy(original)
    task_types = [
        "available_single_skill",
        "unavailable_capability",
        "misleading_name_real_skill",
        "misleading_name_none",
    ]
    for index, row in enumerate(perturbed):
        row["expected_skill"] = (
            names[(index + 17) % len(names)] if index % 3 else None
        )
        row["task_type"] = task_types[(index + 1) % len(task_types)]
        row["seed_fingerprint"] = "f" * 64
        row["_within_group_index"] = 999

    original_tasks = [
        {"task_id": row["task_id"], "prompt": row["prompt"]} for row in original
    ]
    perturbed_tasks = [
        {"task_id": row["task_id"], "prompt": row["prompt"]} for row in perturbed
    ]
    original_metadata = attach_label_independent_option_maps(original_tasks, names)
    perturbed_metadata = attach_label_independent_option_maps(perturbed_tasks, names)
    assert canonical_jsonl_bytes(original_tasks) == canonical_jsonl_bytes(
        perturbed_tasks
    )
    assert original_metadata == perturbed_metadata
    assert all(
        row["task_id"] == f"g22-{collection_task_fingerprint(row['prompt'])[:20]}"
        for row in original
    )
    with pytest.raises(ValueError, match="only task_id and prompt"):
        attach_label_independent_option_maps(deepcopy(original), names)


def test_registry_catalog_has_one_nonempty_canonical_description_per_name(frozen_files):
    catalog = json.loads(frozen_files["registry_catalog.json"])
    assert len(catalog["entries"]) == 43
    assert [entry["name"] for entry in catalog["entries"]] == catalog["names"]
    assert all(set(entry) == {"name", "description", "source_paths"} for entry in catalog["entries"])
    assert all(entry["description"].strip() for entry in catalog["entries"])
    assert all(entry["source_paths"] for entry in catalog["entries"])


def test_ids_prompts_and_bogus_names_are_unique_and_fresh(frozen_files):
    tasks = parse_jsonl(frozen_files["tasks.jsonl"])
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    prior = read_jsonl(ROOT / DEFAULT_PRIOR_TASKS)
    assert len({row["task_id"] for row in tasks}) == EXPECTED_TASKS
    assert len({row["prompt"].casefold() for row in tasks}) == EXPECTED_TASKS
    bogus = {
        row["presented_nonexistent_name"]
        for row in answers
        if row["presented_nonexistent_name"] is not None
    }
    assert len(bogus) == 344
    prior_bogus = {
        row["presented_nonexistent_name"].casefold()
        for row in prior
        if row.get("presented_nonexistent_name")
    }
    assert not ({name.casefold() for name in bogus} & prior_bogus)
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    freshness = manifest["freshness_against_gate2_1"]
    assert freshness["new_task_id_overlap"] == 0
    assert freshness["new_prompt_overlap"] == 0
    assert freshness["new_bogus_name_overlap"] == 0


def test_deterministic_order_and_bytes(frozen_files):
    second = build_artifacts(
        root=ROOT,
        seed_bank_path=ROOT / DEFAULT_SEED_BANK,
        registry_path=ROOT / DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=ROOT / DEFAULT_PRIOR_TASKS,
    )
    assert second == frozen_files
    tasks = parse_jsonl(frozen_files["tasks.jsonl"])
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    pairs = list(zip(tasks, answers, strict=True))
    expected_order = sorted(
        pairs,
        key=lambda pair: hashlib.sha256(
            f"62022:{collection_task_fingerprint(pair[0]['prompt'])}".encode("utf-8")
        ).hexdigest(),
    )
    assert pairs == expected_order
    assert all(
        task["task_id"]
        == f"g22-{collection_task_fingerprint(task['prompt'])[:20]}"
        for task in tasks
    )
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["collection_task_identity"] == {
        "namespace": TASK_ID_NAMESPACE,
        "inputs": ["namespace", "full_prompt"],
        "private_answer_fields_used": [],
        "label_independent": True,
    }


def test_manifest_hashes_every_collection_input(frozen_files):
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    for name in ("tasks.jsonl", "answer_key.jsonl", "registry_catalog.json"):
        assert manifest["artifacts"][name] == {
            "bytes": len(frozen_files[name]),
            "sha256": sha256_bytes(frozen_files[name]),
        }
    assert manifest["counts"]["total"] == EXPECTED_TASKS
    assert manifest["counts"]["unique_presented_nonexistent_names"] == 344


def test_revised_seed_bank_is_prospectively_awaiting_two_label_audits(frozen_files):
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    governance = validate_label_governance(seed)
    assert governance["scenario_origin"] == "model-authored-and-curated"
    assert governance["required_independent_label_audits"] == 2
    assert governance["completed_independent_label_audits"] == 0
    assert governance["release_status"] == "AWAITING_INDEPENDENT_LABEL_AUDITS"
    assert governance["audit_1_status"] == "PENDING"
    assert governance["audit_2_status"] == "PENDING"
    assert governance["audit_resolution_status"] == "PENDING"
    assert not any(key.endswith("_sha256") for key in governance)
    assert "model-authored" in seed["authoring_note"]
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["schema_version"] == "px062-gate2.2-frozen-input-manifest-v2"
    assert manifest["benchmark_status"] == "PROSPECTIVE_INPUTS_AWAITING_LABEL_AUDITS"
    assert manifest["audit_bindings"] == {
        "mode": "PENDING",
        "completed_independent_label_audits": 0,
        "required_independent_label_audits": 2,
        "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
        "final_resolution": {
            "path": governance["audit_resolution"],
            "status": "PENDING",
            "sha256_embedded_in_frozen_inputs": False,
        },
    }


def test_completed_governance_preserves_tasks_catalog_and_label_semantics(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    candidate = plan["candidate_files"]
    completed = plan["completed_files"]
    assert completed["tasks.jsonl"] == candidate["tasks.jsonl"]
    assert completed["registry_catalog.json"] == candidate["registry_catalog.json"]

    candidate_answers = parse_jsonl(candidate["answer_key.jsonl"])
    completed_answers = parse_jsonl(completed["answer_key.jsonl"])
    assert [row["task_id"] for row in completed_answers] == [
        row["task_id"] for row in candidate_answers
    ]
    assert [row["expected_skill"] for row in completed_answers] == [
        row["expected_skill"] for row in candidate_answers
    ]
    assert [
        {key: value for key, value in row.items() if key != "label_audit_status"}
        for row in completed_answers
    ] == [
        {key: value for key, value in row.items() if key != "label_audit_status"}
        for row in candidate_answers
    ]
    assert {row["label_audit_status"] for row in candidate_answers} == {
        PENDING_LABEL_STATUS
    }
    assert {row["label_audit_status"] for row in completed_answers} == {
        AUDITED_LABEL_STATUS
    }

    candidate_manifest = json.loads(candidate["benchmark_manifest.json"])
    completed_manifest = json.loads(completed["benchmark_manifest.json"])
    assert candidate_manifest["benchmark_status"] == "PROSPECTIVE_INPUTS_AWAITING_LABEL_AUDITS"
    assert completed_manifest["benchmark_status"] == "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE"
    assert completed_manifest["label_governance"] == plan["completed_seed"][
        "label_governance"
    ]
    bindings = completed_manifest["audit_bindings"]
    assert bindings["mode"] == "COMPLETED"
    assert bindings["candidate_tasks_sha256"] == sha256_bytes(candidate["tasks.jsonl"])
    assert bindings["candidate_answer_key_sha256"] == sha256_bytes(
        candidate["answer_key.jsonl"]
    )
    assert len(bindings["audits"]) == 2
    assert bindings["canonical_pair_manifest"] == plan["canonical_pair_manifest"]
    checkpoint = bindings["canonical_pair_manifest"]["repository_checkpoint"]
    assert checkpoint["pending_answer_sha256"] == sha256_bytes(
        candidate["answer_key.jsonl"]
    )
    assert checkpoint["source_integrity"] == {
        "tasks_sha256": sha256_bytes(candidate["tasks.jsonl"]),
        "answer_key_sha256": sha256_bytes(candidate["answer_key.jsonl"]),
        "registry_catalog_sha256": sha256_bytes(candidate["registry_catalog.json"]),
        "benchmark_manifest_sha256": sha256_bytes(
            candidate["benchmark_manifest.json"]
        ),
    }
    assert checkpoint["head_commit"] == checkpoint["upstream_commit"] == checkpoint[
        "remote_commit"
    ]
    assert checkpoint["tracked_tree_clean"] is True
    assert checkpoint["config_sha256"] == checkpoint["tracked_files"][
        CHECKPOINT_CONFIG_PATH
    ]["sha256"]
    assert [audit["slot"] for audit in bindings["audits"]] == [1, 2]
    assert [audit["model"] for audit in bindings["audits"]] == list(
        CANONICAL_AUDIT_MODELS
    )
    assert [audit["sidecar_path"] for audit in bindings["audits"]] == list(
        CANONICAL_AUDIT_SIDECAR_PATHS
    )
    assert bindings["provisional_resolution"]["status"] == (
        "UNANIMOUS_VERIFIED_AGAINST_PENDING_CANDIDATE"
    )
    assert bindings["final_resolution"]["sha256_embedded_in_frozen_inputs"] is False
    governance = completed_manifest["label_governance"]
    assert governance["completed_independent_label_audits"] == 2
    assert governance["release_status"] == "AUDITED_READY_TO_FREEZE"
    assert governance["candidate_tasks_sha256"] == sha256_bytes(candidate["tasks.jsonl"])
    assert governance["candidate_answer_key_sha256"] == sha256_bytes(
        candidate["answer_key.jsonl"]
    )
    assert governance["audit_pair_manifest_path"] == CANONICAL_AUDIT_PAIR_MANIFEST_PATH
    assert governance["audit_pair_manifest_sha256"] == plan[
        "canonical_pair_manifest"
    ]["sha256"]
    assert governance["audit_1_sidecar_path"] == CANONICAL_AUDIT_SIDECAR_PATHS[0]
    assert governance["audit_2_sidecar_path"] == CANONICAL_AUDIT_SIDECAR_PATHS[1]
    assert plan["provisional_resolution"]["canonical_pair_manifest"] == plan[
        "canonical_pair_manifest"
    ]
    assert plan["final_resolution"]["canonical_pair_manifest"] == plan[
        "canonical_pair_manifest"
    ]
    assert plan["_test_pair_verifier_calls"]
    assert all(
        root == ROOT.resolve() and write_manifest is False
        for root, write_manifest in plan["_test_pair_verifier_calls"]
    )
    assert "final_resolution_sha256" not in governance
    assert "audit_resolution_sha256" not in governance


def test_completed_manifest_changes_only_governance_and_status_bindings(
    synthetic_finalization_plan,
):
    candidate = json.loads(
        synthetic_finalization_plan["candidate_files"]["benchmark_manifest.json"]
    )
    completed = json.loads(
        synthetic_finalization_plan["completed_files"]["benchmark_manifest.json"]
    )
    assert candidate["artifacts"]["tasks.jsonl"] == completed["artifacts"]["tasks.jsonl"]
    assert candidate["artifacts"]["registry_catalog.json"] == completed["artifacts"][
        "registry_catalog.json"
    ]
    assert candidate["artifacts"]["answer_key.jsonl"] != completed["artifacts"][
        "answer_key.jsonl"
    ]
    for payload in (candidate, completed):
        payload.pop("benchmark_status")
        payload.pop("label_governance")
        payload.pop("audit_bindings")
        payload["source_files"]["seed_bank"]["sha256"] = "GOVERNANCE_ONLY"
        payload["artifacts"]["answer_key.jsonl"] = "AUDIT_STATUS_ONLY"
    assert completed == candidate


def test_final_resolution_is_separate_and_rebinds_the_audited_answer(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    resolution = plan["final_resolution"]
    assert resolution["status"] == (
        "UNANIMOUS_REVERIFIED_AGAINST_AUDITED_FINAL_ANSWER"
    )
    assert resolution["all_labels_independently_agreed"] is True
    assert resolution["cross_audit_disagreement_task_ids"] == []
    assert resolution["answer_label_status"] == AUDITED_LABEL_STATUS
    assert resolution["final_inputs"]["answer_key.jsonl"]["sha256"] == sha256_bytes(
        plan["completed_files"]["answer_key.jsonl"]
    )
    governance_raw = json.dumps(plan["completed_seed"]["label_governance"])
    final_hash = sha256_bytes(plan["final_resolution_raw"])
    assert final_hash not in governance_raw
    assert "intentionally not embedded" in resolution["hash_cycle_boundary"]


def test_completed_builder_rejects_fake_hashes_and_unverified_evidence(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan

    def rebuild(seed, overrides):
        raw = pretty_json_bytes(seed)
        return build_artifacts(
            root=ROOT,
            seed_bank_path=ROOT / DEFAULT_SEED_BANK,
            registry_path=ROOT / DEFAULT_REGISTRY_INVENTORY,
            prior_tasks_path=ROOT / DEFAULT_PRIOR_TASKS,
            seed_bank_override=seed,
            seed_bank_raw_override=raw,
            candidate_checkpoint_manifest_raw_override=plan["candidate_files"][
                "benchmark_manifest.json"
            ],
            evidence_overrides=overrides,
            pair_verifier=plan["_test_pair_verifier"],
        )

    provisional_path = plan["completed_seed"]["label_governance"][
        "provisional_resolution_path"
    ]
    overrides = {
        **plan["_test_evidence_overrides"],
        provisional_path: plan["provisional_resolution_raw"],
    }
    fake_hash = deepcopy(plan["completed_seed"])
    fake_hash["label_governance"]["audit_1_predictions_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="prediction hash drift"):
        rebuild(fake_hash, overrides)

    fake_provisional = deepcopy(plan["provisional_resolution"])
    fake_provisional["status"] = "NOT_VERIFIED"
    fake_provisional_raw = pretty_json_bytes(fake_provisional)
    unverified = deepcopy(plan["completed_seed"])
    unverified["label_governance"]["provisional_resolution_sha256"] = sha256_bytes(
        fake_provisional_raw
    )
    with pytest.raises(ValueError, match="not verified"):
        rebuild(
            unverified,
            {**overrides, provisional_path: fake_provisional_raw},
        )

    cyclic = deepcopy(plan["completed_seed"])
    cyclic["label_governance"]["final_resolution_sha256"] = "1" * 64
    with pytest.raises(ValueError, match="schema drift"):
        rebuild(cyclic, overrides)


def test_canonical_pair_rejects_copies_answer_derived_files_and_forged_sidecars(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    governance = plan["completed_seed"]["label_governance"]
    original = plan["_test_evidence_overrides"]

    copied = dict(original)
    copied[CANONICAL_AUDIT_PATHS[1]] = copied[CANONICAL_AUDIT_PATHS[0]]
    with pytest.raises(ValueError, match="artifact bytes drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=copied,
            pair_verifier=plan["_test_pair_verifier"],
        )

    answer_derived_rows = [
        {
            "task_id": row["task_id"],
            "predicted_skill": row["expected_skill"],
            "confidence": "high",
            "note": "constructed directly from the sealed answer key",
        }
        for row in parse_jsonl(plan["candidate_files"]["answer_key.jsonl"])
    ]
    answer_derived = dict(original)
    answer_derived[CANONICAL_AUDIT_PATHS[0]] = canonical_jsonl_bytes(
        answer_derived_rows
    )
    with pytest.raises(ValueError, match="artifact bytes drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=answer_derived,
            pair_verifier=plan["_test_pair_verifier"],
        )

    forged_sidecar = dict(original)
    forged_sidecar[CANONICAL_AUDIT_SIDECAR_PATHS[0]] += b"forged"
    with pytest.raises(ValueError, match="artifact bytes drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=forged_sidecar,
            pair_verifier=plan["_test_pair_verifier"],
        )


def test_canonical_pair_rejects_swapped_slots_forged_manifest_and_paths(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    original_manifest = plan["_test_pair_manifest"]
    original_overrides = plan["_test_evidence_overrides"]

    swapped_manifest = deepcopy(original_manifest)
    swapped_manifest["audits"] = list(reversed(swapped_manifest["audits"]))
    swapped_manifest_raw = pretty_json_bytes(swapped_manifest)
    swapped_governance = deepcopy(plan["completed_seed"]["label_governance"])
    swapped_governance["audit_pair_manifest_sha256"] = sha256_bytes(
        swapped_manifest_raw
    )
    swapped_governance["audit_1_predictions_sha256"] = swapped_manifest["audits"][0][
        "prediction_sha256"
    ]
    swapped_governance["audit_2_predictions_sha256"] = swapped_manifest["audits"][1][
        "prediction_sha256"
    ]
    swapped_governance["audit_1_sidecar_sha256"] = swapped_manifest["audits"][0][
        "sidecar_sha256"
    ]
    swapped_governance["audit_2_sidecar_sha256"] = swapped_manifest["audits"][1][
        "sidecar_sha256"
    ]
    swapped_overrides = dict(original_overrides)
    swapped_overrides[CANONICAL_AUDIT_PAIR_MANIFEST_PATH] = swapped_manifest_raw

    def swapped_verifier(root, *, write_manifest):
        return deepcopy(swapped_manifest)

    with pytest.raises(ValueError, match="slot 1 model mapping drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=swapped_governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=swapped_overrides,
            pair_verifier=swapped_verifier,
        )

    forged_manifest = deepcopy(original_manifest)
    forged_manifest["answer_key_contents_included"] = True
    forged_manifest_raw = pretty_json_bytes(forged_manifest)
    forged_governance = deepcopy(plan["completed_seed"]["label_governance"])
    forged_governance["audit_pair_manifest_sha256"] = sha256_bytes(
        forged_manifest_raw
    )
    forged_overrides = dict(original_overrides)
    forged_overrides[CANONICAL_AUDIT_PAIR_MANIFEST_PATH] = forged_manifest_raw

    def forged_verifier(root, *, write_manifest):
        return deepcopy(forged_manifest)

    with pytest.raises(ValueError, match="policy drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=forged_governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=forged_overrides,
            pair_verifier=forged_verifier,
        )

    noncanonical = deepcopy(plan["completed_seed"])
    noncanonical["label_governance"]["audit_1_predictions_path"] = (
        "reports/arbitrary/copied_audit.jsonl"
    )
    with pytest.raises(ValueError, match="requires canonical path"):
        validate_label_governance(noncanonical)


def forged_checkpoint_case(plan: dict, mutate) -> tuple[dict, dict, object]:
    manifest = deepcopy(plan["_test_pair_manifest"])
    mutate(manifest["repository_checkpoint"])
    manifest_raw = pretty_json_bytes(manifest)
    governance = deepcopy(plan["completed_seed"]["label_governance"])
    governance["audit_pair_manifest_sha256"] = sha256_bytes(manifest_raw)
    overrides = dict(plan["_test_evidence_overrides"])
    overrides[CANONICAL_AUDIT_PAIR_MANIFEST_PATH] = manifest_raw

    def verifier(root, *, write_manifest):
        return deepcopy(manifest)

    return governance, overrides, verifier


def test_canonical_pair_rejects_forged_pending_answer_and_source_integrity(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    governance, overrides, verifier = forged_checkpoint_case(
        plan,
        lambda checkpoint: checkpoint.__setitem__("pending_answer_sha256", "f" * 64),
    )
    with pytest.raises(ValueError, match="pending answer hash mismatch"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=overrides,
            pair_verifier=verifier,
        )

    governance, overrides, verifier = forged_checkpoint_case(
        plan,
        lambda checkpoint: checkpoint["source_integrity"].__setitem__(
            "answer_key_sha256", "e" * 64
        ),
    )
    with pytest.raises(ValueError, match="source_integrity candidate binding drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=overrides,
            pair_verifier=verifier,
        )


def test_canonical_pair_rejects_forged_config_and_repository_commit_bindings(
    synthetic_finalization_plan,
):
    plan = synthetic_finalization_plan
    governance, overrides, verifier = forged_checkpoint_case(
        plan,
        lambda checkpoint: checkpoint.__setitem__("config_sha256", "d" * 64),
    )
    with pytest.raises(ValueError, match="config tracked-file binding drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=overrides,
            pair_verifier=verifier,
        )

    governance, overrides, verifier = forged_checkpoint_case(
        plan,
        lambda checkpoint: checkpoint.__setitem__("remote_commit", "c" * 40),
    )
    with pytest.raises(ValueError, match="not one clean pushed commit"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=overrides,
            pair_verifier=verifier,
        )

    governance, overrides, verifier = forged_checkpoint_case(
        plan,
        lambda checkpoint: checkpoint.__setitem__("tracked_tree_clean", False),
    )
    with pytest.raises(ValueError, match="not one clean pushed commit"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=governance,
            **pair_candidate_inputs(plan),
            evidence_overrides=overrides,
            pair_verifier=verifier,
        )


@pytest.mark.parametrize(
    "candidate_field",
    [
        "candidate_tasks_raw",
        "candidate_answers_raw",
        "candidate_catalog_raw",
        "candidate_manifest_raw",
    ],
)
def test_canonical_pair_rejects_candidate_file_checkpoint_mismatch(
    synthetic_finalization_plan, candidate_field
):
    plan = synthetic_finalization_plan
    candidate_inputs = pair_candidate_inputs(plan)
    candidate_inputs[candidate_field] += b"forged"
    with pytest.raises(ValueError, match="source_integrity candidate binding drift"):
        validate_canonical_pair_evidence(
            root=ROOT,
            governance=plan["completed_seed"]["label_governance"],
            **candidate_inputs,
            evidence_overrides=plan["_test_evidence_overrides"],
            pair_verifier=plan["_test_pair_verifier"],
        )


@pytest.mark.parametrize("invalid_prediction", ["NONE", "none", " pdf", "not-a-skill", []])
def test_strict_verifier_rejects_noncanonical_prediction_values(
    tmp_path, synthetic_finalization_plan, invalid_prediction
):
    plan = synthetic_finalization_plan
    rows = parse_jsonl(plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[0]])
    rows[0]["predicted_skill"] = invalid_prediction
    with pytest.raises(ValueError, match="JSON null or an exact catalog name"):
        run_staged_label_verifier(
            tmp_path,
            plan,
            audit_raws=[
                canonical_jsonl_bytes(rows),
                plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[1]],
            ],
        )


def test_strict_verifier_rejects_duplicate_keys_confidence_and_notes(
    tmp_path, synthetic_finalization_plan
):
    plan = synthetic_finalization_plan
    valid_1 = plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[0]]
    valid_2 = plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[1]]
    lines = valid_1.splitlines(keepends=True)
    lines[0] = b'{"task_id":"duplicate-key",' + lines[0][1:]
    with pytest.raises(ValueError, match="duplicate JSON key"):
        run_staged_label_verifier(
            tmp_path / "duplicate",
            plan,
            audit_raws=[b"".join(lines), valid_2],
        )

    for index, confidence in enumerate(("High", "unknown", None, [])):
        rows = parse_jsonl(valid_1)
        rows[0]["confidence"] = confidence
        with pytest.raises(ValueError, match="confidence is invalid"):
            run_staged_label_verifier(
                tmp_path / f"confidence-{index}",
                plan,
                audit_raws=[canonical_jsonl_bytes(rows), valid_2],
            )

    for index, note in enumerate(("", "x" * 161, "line\rbreak", "line\nbreak", 7)):
        rows = parse_jsonl(valid_1)
        rows[0]["note"] = note
        with pytest.raises(ValueError, match="note is invalid"):
            run_staged_label_verifier(
                tmp_path / f"note-{index}",
                plan,
                audit_raws=[canonical_jsonl_bytes(rows), valid_2],
            )


def test_strict_verifier_accepts_note_boundaries_and_rejects_catalog_junk(
    tmp_path, synthetic_finalization_plan
):
    plan = synthetic_finalization_plan
    rows_1 = parse_jsonl(
        plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[0]]
    )
    rows_2 = parse_jsonl(
        plan["_test_evidence_overrides"][CANONICAL_AUDIT_PATHS[1]]
    )
    rows_1[0]["note"] = "x"
    rows_2[0]["note"] = "y" * 160
    result = run_staged_label_verifier(
        tmp_path / "boundaries",
        plan,
        audit_raws=[canonical_jsonl_bytes(rows_1), canonical_jsonl_bytes(rows_2)],
    )
    assert result["all_labels_independently_agreed"] is True

    catalog = json.loads(plan["candidate_files"]["registry_catalog.json"])
    catalog["entries"].append("junk")
    with pytest.raises(ValueError, match="catalog names are invalid"):
        run_staged_label_verifier(
            tmp_path / "catalog-junk",
            plan,
            catalog_raw=canonical_json_bytes(catalog),
        )


def test_production_verifier_uses_canonical_slots_in_fixed_order(
    tmp_path, synthetic_finalization_plan
):
    plan = synthetic_finalization_plan
    gate_dir = (tmp_path / CANONICAL_AUDIT_PATHS[0]).parent
    frozen_dir = gate_dir / "frozen_inputs"
    frozen_dir.mkdir(parents=True)
    for name in ("tasks.jsonl", "answer_key.jsonl", "registry_catalog.json"):
        (frozen_dir / name).write_bytes(plan["candidate_files"][name])
    for logical_path in CANONICAL_AUDIT_PATHS:
        path = tmp_path / logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(plan["_test_evidence_overrides"][logical_path])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/verify_px062_gate2_2_label_audits.py"),
            "--root",
            str(tmp_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["audits"][0]["confidence_counts"] == {
        "high": 1032,
        "medium": 0,
        "low": 0,
    }
    assert payload["audits"][1]["confidence_counts"] == {
        "high": 0,
        "medium": 1032,
        "low": 0,
    }


@pytest.mark.parametrize(
    ("script", "arguments"),
    [
        ("finalize_px062_gate2_2_labels.py", ["--audit", "arbitrary.jsonl"]),
        ("verify_px062_gate2_2_label_audits.py", ["--audit", "arbitrary.jsonl"]),
        ("verify_px062_gate2_2_label_audits.py", ["--tasks", "arbitrary.jsonl"]),
        ("verify_px062_gate2_2_label_audits.py", ["--answer-key", "answer.jsonl"]),
    ],
)
def test_production_clis_reject_legacy_evidence_path_overrides(script, arguments):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_none_corpus_is_explicitly_authored_across_43_unsupported_domains():
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    assert "unavailable_request_frames" not in seed
    assert "misleading_request_frames" not in seed
    assert "unavailable_capabilities" not in seed
    domains = seed["unsupported_domains"]
    assert len(domains) == EXPECTED_SKILLS == 43
    assert len({row["slug"] for row in domains}) == 43
    assert len({normalize_text(row["domain"]) for row in domains}) == 43
    assert all(set(row) == {"slug", "domain", "requests", "misleading_scenarios"} for row in domains)
    assert all(len(row["requests"]) == AVAILABLE_PER_SKILL for row in domains)
    assert all(len(row["misleading_scenarios"]) == MISLEADING_REAL_PER_SKILL for row in domains)
    requests = [
        request
        for row in domains
        for request in [
            *row["requests"],
            *(scenario["request"] for scenario in row["misleading_scenarios"]),
        ]
    ]
    assert len(requests) == EXPECTED_NONE_LABELS == 516
    assert len({normalize_text(request) for request in requests}) == 516
    assert len({" ".join(normalize_text(request).split()[:4]) for request in requests}) == 516
    bogus = [
        scenario["suggested_skill"]
        for row in domains
        for scenario in row["misleading_scenarios"]
    ]
    assert len(bogus) == len(set(bogus)) == 172


def test_misleading_real_requests_are_additional_and_not_reused():
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    assert len(seed["skill_scenarios"]) == EXPECTED_SKILLS
    for row in seed["skill_scenarios"]:
        assert set(row) == {
            "skill",
            "misleading_alias_root",
            "requests",
            "misleading_requests",
        }
        assert len(row["requests"]) == AVAILABLE_PER_SKILL
        assert len(row["misleading_requests"]) == MISLEADING_REAL_PER_SKILL
        direct = {normalize_text(value) for value in row["requests"]}
        misleading = {normalize_text(value) for value in row["misleading_requests"]}
        assert len(direct) == 8
        assert len(misleading) == 4
        assert not direct & misleading


def test_registered_requests_never_embed_the_exact_canonical_answer(frozen_files):
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["canonical_answer_mention_check"] == {
        "registered_requests_checked": 516,
        "exact_normalized_canonical_answer_mentions": 0,
    }
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    names, _, _ = load_registry(
        ROOT / DEFAULT_REGISTRY_INVENTORY, seed["registry_corpus"]
    )
    candidates = build_candidates(seed, names)
    assert validate_no_canonical_answer_mentions(candidates) == {
        "registered_requests_checked": 516,
        "exact_normalized_canonical_answer_mentions": 0,
    }
    poisoned = deepcopy(candidates)
    row = next(item for item in poisoned if item["expected_skill"] is not None)
    row["_request"] = f"Use {row['expected_skill']} for this request."
    with pytest.raises(ValueError, match="canonical answer"):
        validate_no_canonical_answer_mentions(poisoned)


def test_prospective_lexical_leakage_gates_are_frozen_and_pass(frozen_files):
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    leakage = manifest["anti_lexical_leakage"]
    assert leakage["prospectively_frozen_before_model_collection"] is True
    shallow = leakage["shallow_grouped_classifier"]
    assert shallow["seed"] == LEXICAL_CV_SEED
    assert shallow["folds"] == 5
    assert shallow["balanced_accuracy_limit_exclusive"] == LEXICAL_BALANCED_ACCURACY_LIMIT == 0.85
    assert shallow["balanced_accuracy"] == 0.821705
    assert shallow["roc_auc"] == 0.904366
    assert shallow["balanced_accuracy"] < shallow["balanced_accuracy_limit_exclusive"]
    assert shallow["passed"] is True
    assert sum(fold["test_none"] for fold in shallow["fold_sizes"]) == 516
    assert sum(fold["test_registered"] for fold in shallow["fold_sizes"]) == 516
    phrase = leakage["repeated_phrase_rule"]
    assert phrase["none_recall_limit_exclusive"] == REPEATED_PHRASE_NONE_RECALL_LIMIT == 0.90
    assert phrase["rule_phrase_count"] == 0
    assert phrase["none_recall"] == 0.0
    assert phrase["passed"] is True


def test_old_repeated_none_frame_failure_is_rejected():
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    names, _, _ = load_registry(
        ROOT / DEFAULT_REGISTRY_INVENTORY, seed["registry_corpus"]
    )
    candidates = build_candidates(seed, names)
    for index, row in enumerate(
        item for item in candidates if item["expected_skill"] is None
    ):
        row["_request"] = (
            f"Coordinate live operational decisions for repeated frame {index % 12}."
        )
    with pytest.raises(ValueError, match="repeated NONE-only phrase rule"):
        evaluate_repeated_phrase_rule(candidates)


def test_every_answer_is_registry_name_or_none_and_bogus_is_nonexistent(frozen_files):
    answers = parse_jsonl(frozen_files["answer_key.jsonl"])
    catalog = json.loads(frozen_files["registry_catalog.json"])
    registry = set(catalog["names"])
    assert all(
        row["expected_skill"] is None or row["expected_skill"] in registry
        for row in answers
    )
    assert all(
        row["presented_nonexistent_name"] not in registry
        for row in answers
        if row["presented_nonexistent_name"] is not None
    )
    assert all(
        (row["task_type"].startswith("misleading_name_"))
        == (row["presented_nonexistent_name"] is not None)
        for row in answers
    )


def test_catalog_description_copy_guard_rejects_verbatim_material():
    inventory = read_jsonl(ROOT / DEFAULT_REGISTRY_INVENTORY)
    description = next(
        row["description"]
        for row in inventory
        if row.get("corpus") == "openai_skills" and row.get("description")
    )
    with pytest.raises(ValueError, match="catalog description"):
        validate_no_catalog_copy(
            [{"task_id": "copy", "prompt": f"User request: {description}"}],
            [description],
        )


def test_freshness_guard_rejects_prior_prompt_id_and_bogus_name():
    prior = read_jsonl(ROOT / DEFAULT_PRIOR_TASKS)
    near = next(row for row in prior if row.get("presented_nonexistent_name"))
    candidate = {
        "task_id": near["task_id"],
        "prompt": near["prompt"],
        "presented_nonexistent_name": near["presented_nonexistent_name"],
    }
    with pytest.raises(ValueError, match="freshness failure"):
        validate_freshness([candidate], prior)


def test_seed_validation_rejects_missing_skill_and_duplicate_requests():
    seed = read_json(ROOT / DEFAULT_SEED_BANK)
    names, _, _ = load_registry(
        ROOT / DEFAULT_REGISTRY_INVENTORY, seed["registry_corpus"]
    )
    missing = deepcopy(seed)
    missing["skill_scenarios"] = missing["skill_scenarios"][:-1]
    with pytest.raises(ValueError, match="coverage mismatch"):
        build_candidates(missing, names)

    duplicate = deepcopy(seed)
    duplicate["skill_scenarios"][0]["requests"][1] = duplicate[
        "skill_scenarios"
    ][0]["requests"][0]
    with pytest.raises(ValueError, match="duplicate requests"):
        build_candidates(duplicate, names)

    reused = deepcopy(seed)
    reused["skill_scenarios"][0]["misleading_requests"][0] = reused[
        "skill_scenarios"
    ][0]["requests"][0]
    with pytest.raises(ValueError, match="duplicate requests"):
        build_candidates(reused, names)

    framed = deepcopy(seed)
    framed["unavailable_request_frames"] = ["Perform {capability}."] * 8
    with pytest.raises(ValueError, match="authored requests, not shared frames"):
        build_candidates(framed, names)


def test_exclusive_atomic_writer_refuses_existing_destination(tmp_path, frozen_files):
    destination = tmp_path / "frozen_inputs"
    write_artifacts(destination, frozen_files)
    assert {path.name for path in destination.iterdir()} == set(frozen_files)
    assert all(path.read_bytes() == frozen_files[path.name] for path in destination.iterdir())
    with pytest.raises(FileExistsError):
        write_artifacts(destination, frozen_files)


def test_source_seed_and_prior_files_are_not_modified(frozen_files):
    manifest = json.loads(frozen_files["benchmark_manifest.json"])
    assert manifest["source_files"]["seed_bank"]["sha256"] == sha256_bytes(
        (ROOT / DEFAULT_SEED_BANK).read_bytes()
    )
    assert manifest["freshness_against_gate2_1"]["prior_tasks_sha256"] == sha256_bytes(
        (ROOT / DEFAULT_PRIOR_TASKS).read_bytes()
    )


def test_checked_in_pending_frozen_inputs_match_the_builder(frozen_files):
    destination = (
        ROOT
        / "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs"
    )
    assert {name: (destination / name).read_bytes() for name in frozen_files} == frozen_files
