from __future__ import annotations

import hashlib
import json
from collections import Counter

import pytest

from scripts.generate_px062_gate2_2_v1_1_construction import EXPECTED_V1_HASHES
from scripts.generate_px062_gate2_2_v1_2_construction import (
    EXPECTED_V11_HASHES,
    REPLACEMENTS,
    ROOT,
    V11_CONFIG,
    V11_FROZEN,
    V12_CONFIG,
    V12_FROZEN,
    V12_LINEAGE,
    V12_PROTOCOL,
    V12_RUNNER,
    V12_SEED,
    V12_TESTS,
    construction,
    verify_v11_conflicts,
)


def parse_jsonl(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


@pytest.fixture(scope="module")
def outputs() -> dict:
    return construction(ROOT)


def test_v1_and_v11_sources_remain_byte_exact(outputs):
    assert outputs
    for relative, expected in EXPECTED_V1_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    for relative, expected in EXPECTED_V11_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_source_audits_recompute_exact_ten_row_union():
    ledger = verify_v11_conflicts(ROOT)
    assert set(ledger) == {item.old_task_id for item in REPLACEMENTS}
    assert len(ledger) == len(REPLACEMENTS) == 10
    assert Counter(row["task_type"] for row in ledger.values()) == {
        "misleading_name_none": 2,
        "unavailable_capability": 4,
        "misleading_name_real_skill": 3,
        "available_single_skill": 1,
    }


def test_exact_1022_retained_and_ten_replaced_lineage(outputs):
    old_tasks = parse_jsonl((ROOT / V11_FROZEN / "tasks.jsonl").read_bytes())
    new_tasks = parse_jsonl(outputs[V12_FROZEN / "tasks.jsonl"])
    old_ids = {row["task_id"] for row in old_tasks}
    new_ids = {row["task_id"] for row in new_tasks}
    expected_old = {row.old_task_id for row in REPLACEMENTS}
    expected_new = {row.new_task_id for row in REPLACEMENTS}
    assert len(expected_old) == len(expected_new) == 10
    assert len(old_ids & new_ids) == 1022
    assert old_ids - new_ids == expected_old
    assert new_ids - old_ids == expected_new
    lineage = json.loads(outputs[V12_LINEAGE])
    assert lineage["status"] == (
        "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND"
    )
    assert {
        (row["old_task_id"], row["new_task_id"])
        for row in lineage["replacements"]
    } == {(row.old_task_id, row.new_task_id) for row in REPLACEMENTS}
    assert lineage["invariants"]["retained_prompt_ids"] == 1022
    assert lineage["invariants"]["replaced_prompt_ids"] == 10
    assert lineage["invariants"]["new_prompt_ids"] == 10


def test_intended_labels_and_task_types_are_preserved(outputs):
    old_answers = {
        row["task_id"]: row
        for row in parse_jsonl((ROOT / V11_FROZEN / "answer_key.jsonl").read_bytes())
    }
    new_answers = {
        row["task_id"]: row
        for row in parse_jsonl(outputs[V12_FROZEN / "answer_key.jsonl"])
    }
    for replacement in REPLACEMENTS:
        old = old_answers[replacement.old_task_id]
        new = new_answers[replacement.new_task_id]
        assert (new["task_type"], new["expected_skill"]) == (
            old["task_type"],
            old["expected_skill"],
        )
    assert {row["label_audit_status"] for row in new_answers.values()} == {
        "PENDING_TWO_INDEPENDENT_AUDITS"
    }


def test_all_frozen_construction_gates_pass(outputs):
    tasks = parse_jsonl(outputs[V12_FROZEN / "tasks.jsonl"])
    answers = parse_jsonl(outputs[V12_FROZEN / "answer_key.jsonl"])
    catalog = json.loads(outputs[V12_FROZEN / "registry_catalog.json"])
    manifest = json.loads(outputs[V12_FROZEN / "benchmark_manifest.json"])
    assert len(tasks) == len(answers) == 1032
    assert len({row["task_id"] for row in tasks}) == 1032
    assert len({row["prompt"].casefold() for row in tasks}) == 1032
    assert [row["task_id"] for row in tasks] == [row["task_id"] for row in answers]
    assert sum(row["expected_skill"] is not None for row in answers) == 516
    assert sum(row["expected_skill"] is None for row in answers) == 516
    assert Counter(row["task_type"] for row in answers) == {
        "available_single_skill": 344,
        "unavailable_capability": 344,
        "misleading_name_real_skill": 172,
        "misleading_name_none": 172,
    }
    assert catalog["count"] == len(catalog["names"]) == 43
    assert catalog["benchmark_identity"] == {
        "experiment_id": "px062-skill-selection-gate2-2-v1-2-20260728",
        "revision": "v1.2",
        "source_catalog_sha256": (
            "d775221aaa2d0bb11ee7b25c2236a241970175d97726fc70f55e47ca6589acde"
        ),
        "registry_semantics_changed": False,
    }
    expected_options = {*catalog["names"], None}
    assert all(
        len(row["option_map"]) == 44
        and {option["skill"] for option in row["option_map"]} == expected_options
        for row in tasks
    )
    assert manifest["experiment_stage"] == "PX-062 Gate 2.2 v1.2"
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
    assert lexical["balanced_accuracy"] == 0.823643 < 0.85
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
    old = json.loads((ROOT / V11_CONFIG).read_text(encoding="utf-8"))
    new = json.loads(outputs[V12_CONFIG])
    assert new["experiment_id"] == "px062-skill-selection-gate2-2-v1-2-20260728"
    assert new["protocol_version"] == "2.2.2"
    assert new["parent_experiment_id"] == old["experiment_id"]
    assert new["revision_lineage"]["basis"] == (
        "LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND"
    )
    assert new["revision_lineage"]["target_model_outcomes_available_at_revision"] is False
    assert new["revision_lineage"]["replaced_prompt_ids"] == 10
    assert new["revision_lineage"]["retained_prompt_ids"] == 1022
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


def test_two_fresh_full_audits_are_mandatory_and_old_audits_forbidden(outputs):
    seed = json.loads(outputs[V12_SEED])
    config = json.loads(outputs[V12_CONFIG])
    governance = seed["label_governance"]
    assert governance["required_independent_label_audits"] == 2
    assert governance["completed_independent_label_audits"] == 0
    assert governance["audit_1_status"] == governance["audit_2_status"] == "PENDING"
    assert governance["audit_resolution_status"] == "PENDING"
    assert config["label_audit_protocol"]["batches_per_auditor"] == 43
    assert config["label_audit_protocol"]["tasks_per_batch"] == 24
    assert config["label_audit_protocol"]["acceptance"] == (
        "both sealed audits and the answer key must agree on all 1032 tasks"
    )
    assert config["label_audit_protocol"]["runner_sha256"] == hashlib.sha256(
        (ROOT / V12_RUNNER).read_bytes()
    ).hexdigest()
    assert config["label_audit_protocol"]["tests_sha256"] == hashlib.sha256(
        (ROOT / V12_TESTS).read_bytes()
    ).hexdigest()
    protocol = " ".join(
        (ROOT / V12_PROTOCOL).read_text(encoding="utf-8").split()
    )
    assert "two new complete blinded audits over all 1,032 rows" in protocol
    assert "forbidden as v1.2 acceptance decisions" in protocol


def test_generator_is_byte_deterministic_and_matches_written_files(outputs):
    assert construction(ROOT) == outputs
    for path, raw in outputs.items():
        assert (ROOT / path).read_bytes() == raw
