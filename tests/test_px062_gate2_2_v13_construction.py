from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter

import pytest

from scripts.generate_px062_gate2_2_v1_3_construction import (
    EXPECTED_V12_HASHES,
    REPLACEMENTS,
    ROOT,
    V11_GATE,
    V12_CONFIG,
    V12_FROZEN,
    V12_GATE,
    V13_CONFIG,
    V13_BASE_BUILDER,
    V13_BUILDER,
    V13_CORE_RUNNER,
    V13_FINALIZER,
    V13_FROZEN,
    V13_LINEAGE,
    V13_PROTOCOL,
    V13_RUNNER,
    V13_SEED,
    V13_TESTS,
    V13_V11_BUILDER,
    V13_V11_FINALIZER,
    V13_V11_RUNNER,
    V13_V11_VERIFIER,
    V13_VERIFIER,
    construction,
    verify_retained_option_map_rotation,
    verify_retained_row_stochasticity,
    verify_v12_conflicts,
)


def parse_jsonl(raw: bytes) -> list[dict]:
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


@pytest.fixture(scope="module")
def outputs() -> dict:
    return construction(ROOT)


def test_v12_sources_remain_byte_exact(outputs):
    assert outputs
    for relative, expected in EXPECTED_V12_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_source_audits_recompute_exact_nine_row_union():
    ledger = verify_v12_conflicts(ROOT)
    assert set(ledger) == {item.old_task_id for item in REPLACEMENTS}
    assert len(ledger) == len(REPLACEMENTS) == 9
    assert Counter(row["task_type"] for row in ledger.values()) == {
        "misleading_name_none": 3,
        "unavailable_capability": 3,
        "misleading_name_real_skill": 2,
        "available_single_skill": 1,
    }


def test_governance_redesign_is_bound_to_retained_row_stochasticity():
    evidence = verify_retained_row_stochasticity(ROOT)
    assert evidence["retained_prompts_compared"] == 1022
    assert (evidence["sol_changed_decisions"], evidence["terra_changed_decisions"]) == (2, 5)
    assert evidence["changed_decision_union"] == 7
    assert evidence["previously_unanimous_with_key_rows"] == 7
    assert evidence["all_changed_rows_were_previously_unanimous_with_key"] is True


def test_retained_stochasticity_recomputes_prior_unanimity_not_a_literal(
    tmp_path,
):
    relatives = (
        V11_GATE / "frozen_inputs/tasks.jsonl",
        V11_GATE / "frozen_inputs/answer_key.jsonl",
        V11_GATE / "label_audit_1_predictions.jsonl",
        V11_GATE / "label_audit_2_predictions.jsonl",
        V12_FROZEN / "tasks.jsonl",
        V12_FROZEN / "answer_key.jsonl",
        V12_GATE / "label_audit_1_predictions.jsonl",
        V12_GATE / "label_audit_2_predictions.jsonl",
    )
    for relative in relatives:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)

    def keyed(relative):
        return {
            row["task_id"]: row
            for row in parse_jsonl((tmp_path / relative).read_bytes())
        }

    old_sol = keyed(V11_GATE / "label_audit_1_predictions.jsonl")
    old_terra = keyed(V11_GATE / "label_audit_2_predictions.jsonl")
    new_sol = keyed(V12_GATE / "label_audit_1_predictions.jsonl")
    new_terra = keyed(V12_GATE / "label_audit_2_predictions.jsonl")
    terra_only_changed = sorted(
        task_id
        for task_id in set(old_terra).intersection(new_terra, old_sol, new_sol)
        if old_terra[task_id]["predicted_skill"]
        != new_terra[task_id]["predicted_skill"]
        and old_sol[task_id]["predicted_skill"]
        == new_sol[task_id]["predicted_skill"]
    )
    assert len(terra_only_changed) == 5
    target_id = terra_only_changed[0]
    old_value = old_sol[target_id]["predicted_skill"]
    hostile_value = None if old_value is not None else "plugin-creator"
    old_sol[target_id]["predicted_skill"] = hostile_value
    new_sol[target_id]["predicted_skill"] = hostile_value
    for relative, rows in (
        (V11_GATE / "label_audit_1_predictions.jsonl", old_sol.values()),
        (V12_GATE / "label_audit_1_predictions.jsonl", new_sol.values()),
    ):
        (tmp_path / relative).write_bytes(
            b"".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode()
                + b"\n"
                for row in rows
            )
        )
    with pytest.raises(ValueError, match="not all previously unanimous"):
        verify_retained_row_stochasticity(tmp_path)


def test_retained_projection_discloses_all_option_map_rotations(outputs):
    projection = verify_retained_option_map_rotation(
        ROOT, outputs[V13_FROZEN / "tasks.jsonl"]
    )
    assert projection == {
        "retained_prompt_ids": 1023,
        "retained_prompt_text_unchanged": 1023,
        "byte_identical_full_task_rows": 433,
        "option_map_rotated_rows": 590,
        "cyclic_rotation_offset_counts": {"1": 327, "2": 249, "3": 14},
        "reason": (
            "Label-independent option maps are assigned from corpus-wide sorted "
            "prompt rank; replacing nine prompts changes some retained ranks."
        ),
        "construction_algorithm_changed": False,
    }
    old = {
        row["task_id"]: row
        for row in parse_jsonl((ROOT / V12_FROZEN / "tasks.jsonl").read_bytes())
    }
    new = {
        row["task_id"]: row
        for row in parse_jsonl(outputs[V13_FROZEN / "tasks.jsonl"])
    }
    retained = set(old).intersection(new)
    assert len(retained) == 1023
    assert all(old[task_id]["prompt"] == new[task_id]["prompt"] for task_id in retained)
    assert sum(old[task_id] == new[task_id] for task_id in retained) == 433


def test_exact_1023_retained_and_nine_replaced_lineage(outputs):
    old_tasks = parse_jsonl((ROOT / V12_FROZEN / "tasks.jsonl").read_bytes())
    new_tasks = parse_jsonl(outputs[V13_FROZEN / "tasks.jsonl"])
    old_ids = {row["task_id"] for row in old_tasks}
    new_ids = {row["task_id"] for row in new_tasks}
    assert old_ids - new_ids == {row.old_task_id for row in REPLACEMENTS}
    assert new_ids - old_ids == {row.new_task_id for row in REPLACEMENTS}
    assert len(old_ids & new_ids) == 1023
    lineage = json.loads(outputs[V13_LINEAGE])
    assert lineage["status"] == "PROSPECTIVE_LABEL_AUDIT_INFORMED_TARGET_OUTCOME_BLIND"
    assert lineage["invariants"]["retained_prompt_ids"] == 1023
    assert lineage["invariants"]["replaced_prompt_ids"] == 9
    assert lineage["governance_redesign"]["policy"] == (
        "BALANCED_FOUR_PASS_3_OF_4_WITH_FAMILY_SUPPORT"
    )
    assert lineage["governance_redesign"]["target_model_outcomes_available"] is False
    assert lineage["retained_task_projection"]["option_map_rotated_rows"] == 590
    assert lineage["retained_task_projection"]["byte_identical_full_task_rows"] == 433


def test_intended_labels_task_types_and_pending_status_are_preserved(outputs):
    old_answers = {
        row["task_id"]: row
        for row in parse_jsonl((ROOT / V12_FROZEN / "answer_key.jsonl").read_bytes())
    }
    new_answers = {
        row["task_id"]: row
        for row in parse_jsonl(outputs[V13_FROZEN / "answer_key.jsonl"])
    }
    for replacement in REPLACEMENTS:
        old = old_answers[replacement.old_task_id]
        new = new_answers[replacement.new_task_id]
        assert (new["task_type"], new["expected_skill"]) == (
            old["task_type"],
            old["expected_skill"],
        )
    assert {row["label_audit_status"] for row in new_answers.values()} == {
        "PENDING_FOUR_PASS_BALANCED_CONSENSUS"
    }


def test_all_frozen_construction_gates_pass(outputs):
    tasks = parse_jsonl(outputs[V13_FROZEN / "tasks.jsonl"])
    answers = parse_jsonl(outputs[V13_FROZEN / "answer_key.jsonl"])
    catalog = json.loads(outputs[V13_FROZEN / "registry_catalog.json"])
    manifest = json.loads(outputs[V13_FROZEN / "benchmark_manifest.json"])
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
        "experiment_id": "px062-skill-selection-gate2-2-v1-3-20260728",
        "revision": "v1.3",
        "source_catalog_sha256": (
            "90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212"
        ),
        "registry_semantics_changed": False,
    }
    assert manifest["experiment_stage"] == "PX-062 Gate 2.2 v1.3"
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
    assert balance["construction"]["label_independent"] is True
    assert balance["construction"]["private_answer_fields_used"] == []


def test_scientific_contract_is_unchanged_except_revision_and_label_governance(outputs):
    old = json.loads((ROOT / V12_CONFIG).read_text(encoding="utf-8"))
    new = json.loads(outputs[V13_CONFIG])
    assert new["experiment_id"] == "px062-skill-selection-gate2-2-v1-3-20260728"
    assert new["protocol_version"] == "2.2.3"
    assert new["parent_experiment_id"] == old["experiment_id"]
    assert new["revision_lineage"]["target_model_outcomes_available_at_revision"] is False
    assert new["revision_lineage"]["replaced_prompt_ids"] == 9
    assert new["revision_lineage"]["retained_prompt_ids"] == 1023
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


def test_four_fresh_full_audits_and_balanced_rule_are_mandatory(outputs):
    seed = json.loads(outputs[V13_SEED])
    config = json.loads(outputs[V13_CONFIG])
    governance = seed["label_governance"]
    assert governance["required_independent_label_audits"] == 4
    assert governance["completed_independent_label_audits"] == 0
    assert [governance[f"audit_{slot}_status"] for slot in (1, 2, 3, 4)] == [
        "PENDING"
    ] * 4
    assert governance["consensus_policy"]["minimum_key_votes"] == 3
    assert governance["consensus_policy"]["sol_slots"] == [1, 3]
    assert governance["consensus_policy"]["terra_slots"] == [2, 4]
    assert governance["consensus_policy"]["semantic_retry_permitted"] is False
    protocol = config["label_audit_protocol"]
    assert protocol["full_audit_passes"] == 4
    assert protocol["accepted_sessions_required"] == 172
    assert protocol["batches_per_auditor"] == 43
    assert protocol["tasks_per_batch"] == 24
    assert protocol["runner_sha256"] == hashlib.sha256((ROOT / V13_RUNNER).read_bytes()).hexdigest()
    assert protocol["tests_sha256"] == hashlib.sha256((ROOT / V13_TESTS).read_bytes()).hexdigest()
    assert protocol["slot_execution_order"] == [1, 2, 3, 4]
    assert protocol["prior_audit_session_blacklist"]["accepted_session_count"] == 86
    assert protocol["governance_code"] == {
        "runner_core": {
            "path": V13_CORE_RUNNER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_CORE_RUNNER).read_bytes()).hexdigest(),
        },
        "builder": {
            "path": V13_BUILDER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_BUILDER).read_bytes()).hexdigest(),
        },
        "builder_base": {
            "path": V13_BASE_BUILDER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_BASE_BUILDER).read_bytes()).hexdigest(),
        },
        "v11_builder": {
            "path": V13_V11_BUILDER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_V11_BUILDER).read_bytes()).hexdigest(),
        },
        "v11_runner": {
            "path": V13_V11_RUNNER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_V11_RUNNER).read_bytes()).hexdigest(),
        },
        "verifier": {
            "path": V13_VERIFIER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_VERIFIER).read_bytes()).hexdigest(),
        },
        "verifier_base": {
            "path": V13_V11_VERIFIER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_V11_VERIFIER).read_bytes()).hexdigest(),
        },
        "finalizer": {
            "path": V13_FINALIZER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_FINALIZER).read_bytes()).hexdigest(),
        },
        "finalizer_base": {
            "path": V13_V11_FINALIZER.as_posix(),
            "sha256": hashlib.sha256((ROOT / V13_V11_FINALIZER).read_bytes()).hexdigest(),
        },
    }
    assert config["retained_task_projection"]["option_map_rotated_rows"] == 590
    text = " ".join((ROOT / V13_PROTOCOL).read_text(encoding="utf-8").split())
    assert "at least three of four predictions equal the frozen answer" in text
    assert "There is no semantic retry" in text


def test_generator_is_byte_deterministic_and_matches_written_files(outputs):
    assert construction(ROOT) == outputs
    for path, raw in outputs.items():
        assert (ROOT / path).read_bytes() == raw
