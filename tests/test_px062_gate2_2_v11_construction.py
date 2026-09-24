from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest

from scripts.generate_px062_gate2_2_v1_1_construction import (
    EXPECTED_V1_HASHES,
    REPLACEMENTS,
    ROOT,
    V1_CONFIG,
    V1_FROZEN,
    V1_1_CONFIG,
    V1_1_FROZEN,
    V1_1_LINEAGE,
    V1_1_SEED,
    construction,
)


def parse_jsonl(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


@pytest.fixture(scope="module")
def outputs() -> dict:
    return construction(ROOT)


def test_v1_sources_are_byte_exact_and_target_artifacts_are_new(outputs):
    for relative, expected in EXPECTED_V1_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    source_hashes = {
        name: EXPECTED_V1_HASHES[(V1_FROZEN / name).as_posix()]
        for name in ("tasks.jsonl", "answer_key.jsonl", "registry_catalog.json")
    }
    for name, source_hash in source_hashes.items():
        assert hashlib.sha256(outputs[V1_1_FROZEN / name]).hexdigest() != source_hash


def test_exact_999_retained_and_33_replaced_lineage(outputs):
    old_tasks = parse_jsonl((ROOT / V1_FROZEN / "tasks.jsonl").read_bytes())
    new_tasks = parse_jsonl(outputs[V1_1_FROZEN / "tasks.jsonl"])
    old_ids = {row["task_id"] for row in old_tasks}
    new_ids = {row["task_id"] for row in new_tasks}
    expected_old = {row.old_task_id for row in REPLACEMENTS}
    expected_new = {row.new_task_id for row in REPLACEMENTS}
    assert len(REPLACEMENTS) == len(expected_old) == len(expected_new) == 33
    assert len(old_ids & new_ids) == 999
    assert old_ids - new_ids == expected_old
    assert new_ids - old_ids == expected_new
    lineage = json.loads(outputs[V1_1_LINEAGE])
    assert lineage["status"] == (
        "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND"
    )
    assert {
        (row["old_task_id"], row["new_task_id"])
        for row in lineage["replacements"]
    } == {(row.old_task_id, row.new_task_id) for row in REPLACEMENTS}
    assert lineage["invariants"]["retained_prompt_ids"] == 999
    assert lineage["invariants"]["replaced_prompt_ids"] == 33


def test_labels_task_types_and_all_construction_gates(outputs):
    tasks = parse_jsonl(outputs[V1_1_FROZEN / "tasks.jsonl"])
    answers = parse_jsonl(outputs[V1_1_FROZEN / "answer_key.jsonl"])
    catalog = json.loads(outputs[V1_1_FROZEN / "registry_catalog.json"])
    manifest = json.loads(outputs[V1_1_FROZEN / "benchmark_manifest.json"])
    assert len(tasks) == len(answers) == 1032
    assert len({row["task_id"] for row in tasks}) == 1032
    assert len({row["prompt"].casefold() for row in tasks}) == 1032
    assert [row["task_id"] for row in tasks] == [row["task_id"] for row in answers]
    assert {row["label_audit_status"] for row in answers} == {
        "PENDING_TWO_INDEPENDENT_AUDITS"
    }
    assert catalog["count"] == len(catalog["names"]) == 43
    assert catalog["benchmark_identity"]["registry_semantics_changed"] is False
    expected_options = {*catalog["names"], None}
    assert all(
        len(row["option_map"]) == 44
        and {option["skill"] for option in row["option_map"]} == expected_options
        for row in tasks
    )
    assert sum(row["expected_skill"] is not None for row in answers) == 516
    assert sum(row["expected_skill"] is None for row in answers) == 516
    assert Counter(row["task_type"] for row in answers) == {
        "available_single_skill": 344,
        "unavailable_capability": 344,
        "misleading_name_real_skill": 172,
        "misleading_name_none": 172,
    }
    assert manifest["experiment_stage"] == "PX-062 Gate 2.2 v1.1"
    assert manifest["benchmark_status"] == "PROSPECTIVE_INPUTS_AWAITING_LABEL_AUDITS"
    assert manifest["freshness_against_gate2_1"]["new_task_id_overlap"] == 0
    assert manifest["freshness_against_gate2_1"]["new_prompt_overlap"] == 0
    assert manifest["catalog_copy_check"] == {
        "full_description_overlap": 0,
        "shared_contiguous_catalog_words_at_width_12": 0,
    }
    assert manifest["canonical_answer_mention_check"] == {
        "registered_requests_checked": 516,
        "exact_normalized_canonical_answer_mentions": 0,
    }
    lexical = manifest["anti_lexical_leakage"]["shallow_grouped_classifier"]
    assert lexical["passed"] is True
    assert lexical["balanced_accuracy"] < 0.85
    assert manifest["anti_lexical_leakage"]["repeated_phrase_rule"]["passed"] is True
    balance = manifest["option_map_balance"]
    assert (balance["per_choice_per_position_min"], balance["per_choice_per_position_max"]) == (23, 24)
    assert balance["by_observable_scaffold"]["direct"] == {
        "tasks": 688,
        "per_choice_per_position_min": 15,
        "per_choice_per_position_max": 16,
    }
    assert balance["by_observable_scaffold"]["misleading"] == {
        "tasks": 344,
        "per_choice_per_position_min": 7,
        "per_choice_per_position_max": 8,
    }
    assert balance["construction"]["label_independent"] is True
    assert balance["construction"]["private_answer_fields_used"] == []
    assert manifest["collection_task_identity"]["label_independent"] is True
    assert manifest["collection_task_identity"]["private_answer_fields_used"] == []


def test_scientific_contract_is_unchanged_except_versioned_lineage(outputs):
    old = json.loads((ROOT / V1_CONFIG).read_text(encoding="utf-8"))
    new = json.loads(outputs[V1_1_CONFIG])
    assert new["experiment_id"] == "px062-skill-selection-gate2-2-v1-1-20260728"
    assert new["protocol_version"] == "2.2.1"
    assert new["parent_experiment_id"] == old["experiment_id"]
    assert new["revision_lineage"]["basis"] == (
        "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND"
    )
    assert new["revision_lineage"]["target_model_outcomes_available_at_revision"] is False
    for field in (
        "registry_source_commit",
        "expected_registry_names",
        "expected_tasks",
        "expected_traces",
        "expected_task_type_counts",
        "expected_label_counts",
        "corpus_construction_gates",
        "arms",
        "models",
        "model_revisions",
        "dependency_versions",
        "decoding",
        "message_templates",
        "gates",
        "multiplicity",
        "decision_rule",
        "claim_boundary",
    ):
        assert new[field] == old[field]
    assert new["label_audit_protocol"]["acceptance"] == old[
        "label_audit_protocol"
    ]["acceptance"]


def test_generator_is_byte_deterministic(outputs):
    assert construction(ROOT) == outputs
    assert json.loads(outputs[V1_1_SEED])["revision_lineage"] == {
        "revision": "v1.1",
        "source_experiment_id": "px062-skill-selection-gate2-2-v1-0-20260728",
        "source_tasks_sha256": "37c77a9eaa12a4102419591aa554f736494aff85a3e252fd284a20b95094bebc",
        "source_invalidation": (
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/label_audit_invalidation.json"
        ),
        "source_invalidation_sha256": "3c0a3d83877ea2eb5b8fc829e92cd9661b72ac5cf8c016ae145a5fd3dd3a9e42",
        "basis": "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND",
        "replaced_prompt_ids": 33,
        "retained_prompt_ids": 999,
    }
