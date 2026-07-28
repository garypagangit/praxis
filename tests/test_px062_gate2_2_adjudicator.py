"""Contract fixtures and adversarial tests for the PX-062 Gate 2.2 adjudicator."""

from __future__ import annotations

from copy import deepcopy
import base64
import hashlib
import io
import json
import tarfile

import pytest

import scripts.adjudicate_px062_gate2_2 as adjudicator_module

from scripts.adjudicate_px062_gate2_2 import (
    A_FIELDS,
    EXPECTED_ARMS,
    FROZEN_MODEL_REVISIONS,
    FROZEN_DEPENDENCIES,
    FROZEN_GATES,
    STRUCTURED_FIELDS,
    TRACE_FIELDS,
    acquire_one_look_claim,
    adjudicate,
    canonical_json_sha256,
    complete_one_look_claim,
    holm_adjust,
    mark_one_look_outcome_read_started,
    one_sided_mcnemar,
    reconstructed_messages,
    read_jsonl,
    resolve_adjudication_paths,
    text_sha256,
    wilson_95,
    verify_registered_adjudicator,
    verify_registered_cloud_archives,
    verify_committed_adjudication_authorization,
    verify_sealed_evidence,
)
from scripts.register_px062_gate2_2_fetch import (
    DEFAULT_ADJUDICATION_AUTHORIZATION,
    DEFAULT_ADJUDICATION_CONSUMPTION,
    DEFAULT_ADJUDICATION_RESULT,
    DEFAULT_FETCH_RECEIPT,
)
from scripts.run_px062_gate2_2_models import (
    arm_a_messages as collector_arm_a_messages,
    contextual_repair_messages as collector_contextual_repair_messages,
    decontextualized_repair_messages as collector_decontextualized_repair_messages,
    direct_messages as collector_direct_messages,
    render_catalog as collector_render_catalog,
    strict_initial_parse as collector_strict_initial_parse,
    structured_responses as collector_structured_responses,
)


MODELS = list(FROZEN_MODEL_REVISIONS)
TYPE_COUNTS = {
    "available_intent": 344,
    "unavailable_intent": 344,
    "misleading_real": 172,
    "misleading_none": 172,
}


def fixture_config() -> dict:
    """Return the exact small-model/full-corpus preregistration contract.

    The fixture deliberately retains all 1,032 tasks and both model families so
    statistical and integrity behavior is tested at the registered denominators.
    """

    return {
        "experiment_id": "px062-g22-fixture",
        "protocol_version": "2.2.0",
        "status": "FROZEN_PREREGISTERED",
        "expected_registry_names": 43,
        "expected_tasks": 1032,
        "expected_traces": 2064,
        "expected_task_type_counts": TYPE_COUNTS,
        "expected_label_counts": {"registered_skill": 516, "none": 516},
        "arms": list(EXPECTED_ARMS),
        "models": MODELS,
        "model_revisions": dict(FROZEN_MODEL_REVISIONS),
        "dependency_versions": dict(FROZEN_DEPENDENCIES),
        "decoding": {
            "do_sample": False,
            "open_max_new_tokens": 32,
            "structured_decoder": (
                "greedy_prefix_trie_over_exact_local_id_json_choices"
            ),
            "structured_response_schema": '{"choice":"Snnn"}',
            "choice_count": 44,
        },
        "label_audit_protocol": {
            "runner_sha256": "a" * 64,
            "protocol_sha256": "b" * 64,
            "tests_sha256": "c" * 64,
            "fixture_binding": "validated-test-contract",
        },
        "message_templates": {
            "open_system": "open system",
            "open_user": "task={task}",
            "structured_system": "structured system",
            "direct_names_user": "task={task}\nnames={catalog}",
            "direct_catalog_user": "task={task}\ncatalog={catalog}",
            "contextual_repair_user": (
                'context repair; return exactly {{"choice":"Snnn"}}\n{catalog}'
            ),
            "decontextualized_task_placeholder": "TASK WITHHELD",
        },
        "source_integrity": {
            "tasks_sha256": "1" * 64,
            "answer_key_sha256": "2" * 64,
            "registry_catalog_sha256": "3" * 64,
            "benchmark_manifest_sha256": "4" * 64,
        },
        "gates": dict(FROZEN_GATES),
        "multiplicity": {
            "family": "fixture two-model D-E family",
            "method": "Holm",
            "family_size": 2,
        },
        "claim_boundary": "Clean-registry selection only; no execution or poison claim.",
    }


def artifact_hashes() -> dict[str, str]:
    return {
        "tasks_sha256": "1" * 64,
        "answer_key_sha256": "2" * 64,
        "registry_catalog_sha256": "3" * 64,
        "benchmark_manifest_sha256": "4" * 64,
    }


def registry_fixture() -> dict:
    return {
        "entries": [
            {"name": f"skill-{index:02d}", "description": f"description {index}"}
            for index in range(43)
        ]
    }


def option_map_for(task_index: int, names: list[str]) -> list[dict]:
    choices: list[str | None] = [*names, None]
    offset = task_index % len(choices)
    rotated = choices[offset:] + choices[:offset]
    return [
        {"id": f"S{position + 1:03d}", "skill": skill}
        for position, skill in enumerate(rotated)
    ]


def build_tasks_and_answers() -> tuple[list[dict], list[dict]]:
    names = [f"skill-{index:02d}" for index in range(43)]
    labels: list[tuple[str, str | None]] = []
    for name in names:
        labels.extend(("available_intent", name) for _ in range(8))
    labels.extend(("unavailable_intent", None) for _ in range(344))
    for name in names:
        labels.extend(("misleading_real", name) for _ in range(4))
    labels.extend(("misleading_none", None) for _ in range(172))
    assert len(labels) == 1032
    tasks: list[dict] = []
    answers: list[dict] = []
    for index, (task_type, expected) in enumerate(labels):
        task_id = f"task-{index:04d}"
        tasks.append(
            {
                "task_id": task_id,
                "prompt": f"unique scenario {index}",
                "option_map": option_map_for(index, names),
            }
        )
        answers.append(
            {
                "task_id": task_id,
                "task_type": task_type,
                "expected_skill": expected,
            }
        )
    return tasks, answers


def choice_id(option_map: list[dict], selection: str | None) -> str:
    return next(row["id"] for row in option_map if row["skill"] == selection)


def allowed_choices(option_map: list[dict]) -> list[str]:
    return sorted(
        f'{{"choice":"{row["id"]}"}}' for row in option_map
    )


def generated_structured_arm(
    *,
    messages: list[dict],
    option_map: list[dict],
    selection: str | None,
    source_initial_sha256: str | None,
) -> dict:
    local_id = choice_id(option_map, selection)
    raw = f'{{"choice":"{local_id}"}}'
    raw_bytes = raw.encode("utf-8")
    return {
        "triggered": True,
        "generated": True,
        "messages": messages,
        "messages_sha256": canonical_json_sha256(messages),
        "raw_response": raw,
        "raw_response_utf8_base64": base64.b64encode(raw_bytes).decode("ascii"),
        "raw_response_bytes": len(raw_bytes),
        "raw_response_sha256": text_sha256(raw),
        "generated_token_ids": list(raw_bytes),
        "tokenizer_reconstruction_verified": True,
        "decoder_escape": False,
        "choice_set_sha256": canonical_json_sha256(allowed_choices(option_map)),
        "choice_id": local_id,
        "selection": selection,
        "canonical_decision": (
            '{"skill":null}'
            if selection is None
            else f'{{"skill":"{selection}"}}'
        ),
        "source_initial_sha256": source_initial_sha256,
    }


def pass_through_arm(
    *, option_map: list[dict], selection: str | None, a_sha256: str
) -> dict:
    return {
        "triggered": False,
        "generated": False,
        "messages": None,
        "messages_sha256": None,
        "raw_response": None,
        "raw_response_utf8_base64": None,
        "raw_response_bytes": None,
        "raw_response_sha256": None,
        "generated_token_ids": [],
        "tokenizer_reconstruction_verified": None,
        "decoder_escape": False,
        "choice_set_sha256": canonical_json_sha256(allowed_choices(option_map)),
        "choice_id": None,
        "selection": selection,
        "canonical_decision": (
            '{"skill":null}'
            if selection is None
            else f'{{"skill":"{selection}"}}'
        ),
        "source_initial_sha256": a_sha256,
    }


def make_fixture(
    *,
    invalid_registered_events_per_model: int = 220,
    invalid_none_events_per_model: int = 110,
) -> dict:
    config = fixture_config()
    catalog = registry_fixture()
    descriptions = {row["name"]: row["description"] for row in catalog["entries"]}
    tasks, answers = build_tasks_and_answers()
    answer_by_id = {row["task_id"]: row for row in answers}
    real_ids = [row["task_id"] for row in answers if row["expected_skill"] is not None]
    none_ids = [row["task_id"] for row in answers if row["expected_skill"] is None]
    invalid_ids = set(
        real_ids[:invalid_registered_events_per_model]
        + none_ids[:invalid_none_events_per_model]
    )
    first_skill = catalog["entries"][0]["name"]
    traces: list[dict] = []
    for model_id in MODELS:
        for task in tasks:
            expected = answer_by_id[task["task_id"]]["expected_skill"]
            invalid = task["task_id"] in invalid_ids
            raw_a = f"invented-{task['task_id']}" if invalid else (
                "NONE" if expected is None else expected
            )
            a_status = "invalid" if invalid else (
                "explicit_none" if expected is None else "valid_skill"
            )
            a_candidate = raw_a if invalid or expected is not None else None
            a_selection = None if invalid else expected
            a_sha = text_sha256(raw_a)
            messages = reconstructed_messages(
                config, task, task["option_map"], descriptions, raw_a
            )
            arm_a = {
                "generated": True,
                "messages": messages["A_open_text"],
                "messages_sha256": canonical_json_sha256(messages["A_open_text"]),
                "raw_response": raw_a,
                "raw_response_utf8_base64": base64.b64encode(
                    raw_a.encode("utf-8")
                ).decode("ascii"),
                "raw_response_bytes": len(raw_a.encode("utf-8")),
                "raw_response_sha256": a_sha,
                "generated_token_ids": list(raw_a.encode("utf-8")),
                "tokenizer_reconstruction_verified": True,
                "parser_status": a_status,
                "parsed_candidate": a_candidate,
                "selection": a_selection,
            }
            arm_b = generated_structured_arm(
                messages=messages["B_structured_names"],
                option_map=task["option_map"],
                selection=expected,
                source_initial_sha256=None,
            )
            arm_c = generated_structured_arm(
                messages=messages["C_structured_catalog"],
                option_map=task["option_map"],
                selection=expected,
                source_initial_sha256=None,
            )
            if invalid:
                wrong_e = first_skill if expected is None else None
                arm_d = generated_structured_arm(
                    messages=messages["D_contextual_repair"],
                    option_map=task["option_map"],
                    selection=expected,
                    source_initial_sha256=a_sha,
                )
                arm_e = generated_structured_arm(
                    messages=messages["E_decontextualized_repair"],
                    option_map=task["option_map"],
                    selection=wrong_e,
                    source_initial_sha256=a_sha,
                )
            else:
                arm_d = pass_through_arm(
                    option_map=task["option_map"],
                    selection=a_selection,
                    a_sha256=a_sha,
                )
                arm_e = deepcopy(arm_d)
            traces.append(
                {
                    "experiment_id": config["experiment_id"],
                    "protocol_version": config["protocol_version"],
                    "task_id": task["task_id"],
                    "model_id": model_id,
                    "model_revision": config["model_revisions"][model_id],
                    "tokenizer_artifact_key": f"fixture-{model_id}",
                    "option_map": task["option_map"],
                    "option_map_sha256": canonical_json_sha256(task["option_map"]),
                    "arms": {
                        "A_open_text": arm_a,
                        "B_structured_names": arm_b,
                        "C_structured_catalog": arm_c,
                        "D_contextual_repair": arm_d,
                        "E_decontextualized_repair": arm_e,
                    },
                }
            )
    return {
        "config": config,
        "tasks": tasks,
        "answers": answers,
        "catalog": catalog,
        "traces": traces,
        "hashes": artifact_hashes(),
        "config_contract_sha256": (
            adjudicator_module.adjudication_config_contract_sha256(config)
        ),
    }


def run(bundle: dict) -> dict:
    class ByteTokenizer:
        def decode(self, token_ids, **kwargs):
            assert kwargs == {
                "skip_special_tokens": True,
                "clean_up_tokenization_spaces": False,
            }
            return bytes(token_ids).decode("utf-8")

    return adjudicate(
        bundle["config"],
        bundle["tasks"],
        bundle["answers"],
        bundle["catalog"],
        bundle["traces"],
        bundle["hashes"],
        {model: ByteTokenizer() for model in MODELS},
        {
            model: {
                "artifact_key": f"fixture-{model}",
                "revision": bundle["config"]["model_revisions"][model],
            }
            for model in MODELS
        },
        expected_config_contract_sha256=bundle["config_contract_sha256"],
    )


def replace_structured_selection(trace: dict, arm_name: str, selection: str | None) -> None:
    arm = trace["arms"][arm_name]
    local_id = choice_id(trace["option_map"], selection)
    raw = f'{{"choice":"{local_id}"}}'
    raw_bytes = raw.encode("utf-8")
    arm.update(
        {
            "raw_response": raw,
            "raw_response_utf8_base64": base64.b64encode(raw_bytes).decode("ascii"),
            "raw_response_bytes": len(raw_bytes),
            "raw_response_sha256": text_sha256(raw),
            "generated_token_ids": list(raw_bytes),
            "decoder_escape": False,
            "choice_id": local_id,
            "selection": selection,
            "canonical_decision": (
                '{"skill":null}'
                if selection is None
                else f'{{"skill":"{selection}"}}'
            ),
        }
    )


@pytest.fixture(scope="module")
def passing_bundle() -> dict:
    return make_fixture()


def test_complete_cross_model_fixture_is_bounded_efficacy_and_context_supported(
    passing_bundle,
):
    result = run(passing_bundle)
    assert result["integrity"]["pass"] is True
    assert result["determination"] == "PASS"
    assert result["result_classification"] == "BOUNDED_EFFICACY_PASS"
    assert (
        result["context_mechanism_determination"]
        == "CONTEXT_MECHANISM_SUPPORTED"
    )
    assert result["denominators"] == {
        "C_overall_per_model": 1032,
        "C_registered_targets_per_model": 516,
        "C_expected_NONE_per_model": 516,
        "D_expected_NONE_per_model": 516,
        "D_and_E_primary_recovery_per_model": (
            "observed A-invalid registered-target events; minimum 200"
        ),
        "D_and_E_all_A_invalid_diagnostic_per_model": (
            "all observed A-invalid events; diagnostic only"
        ),
    }
    for model_id in MODELS:
        assert result["metrics"][model_id]["A_invalid_events"]["numerator"] == 330
        assert result["metrics"][model_id]["A_invalid_registered_target_events"][
            "numerator"
        ] == 220
        by_type = result["metrics"][model_id]["A_invalid_events_by_task_type"]
        assert set(by_type) == set(TYPE_COUNTS)
        assert {
            task_type: item["numerator"] for task_type, item in by_type.items()
        } == {
            "available_intent": 220,
            "unavailable_intent": 110,
            "misleading_real": 0,
            "misleading_none": 0,
        }
        assert result["model_gates"][model_id]["primary_efficacy_pass"] is True
        assert result["model_gates"][model_id]["context_mechanism_pass"] is True


def test_fixture_exactly_matches_collector_schema_and_message_contract(passing_bundle):
    trace = passing_bundle["traces"][0]
    task = passing_bundle["tasks"][0]
    config = passing_bundle["config"]
    descriptions = {
        row["name"]: row["description"] for row in passing_bundle["catalog"]["entries"]
    }
    arm_a = trace["arms"]["A_open_text"]
    raw_a = arm_a["raw_response"]
    names_catalog = collector_render_catalog(
        task["option_map"], descriptions, include_descriptions=False
    )
    full_catalog = collector_render_catalog(
        task["option_map"], descriptions, include_descriptions=True
    )
    expected_a = collector_arm_a_messages(config, task)
    expected = {
        "A_open_text": expected_a,
        "B_structured_names": collector_direct_messages(
            config, task, names_catalog, include_descriptions=False
        ),
        "C_structured_catalog": collector_direct_messages(
            config, task, full_catalog, include_descriptions=True
        ),
        "D_contextual_repair": collector_contextual_repair_messages(
            config, expected_a, raw_a, full_catalog
        ),
        "E_decontextualized_repair": collector_decontextualized_repair_messages(
            config, raw_a, full_catalog
        ),
    }
    independent = reconstructed_messages(
        config, task, task["option_map"], descriptions, raw_a
    )
    assert independent == expected
    assert independent["D_contextual_repair"][0]["content"] == config[
        "message_templates"
    ]["open_system"]
    assert independent["E_decontextualized_repair"][0]["content"] == config[
        "message_templates"
    ]["open_system"]
    assert independent["D_contextual_repair"][0] == independent[
        "E_decontextualized_repair"
    ][0]
    assert [message["role"] for message in independent["D_contextual_repair"]] == [
        "system", "user", "assistant", "user"
    ]
    assert [message["role"] for message in independent["E_decontextualized_repair"]] == [
        "system", "user", "assistant", "user"
    ]
    assert independent["D_contextual_repair"][2:] == independent[
        "E_decontextualized_repair"
    ][2:]
    assert independent["D_contextual_repair"][1] != independent[
        "E_decontextualized_repair"
    ][1]
    assert set(trace) == TRACE_FIELDS
    assert set(arm_a) == A_FIELDS
    assert all(
        set(trace["arms"][arm_name]) == STRUCTURED_FIELDS
        for arm_name in EXPECTED_ARMS[1:]
    )
    collector_parse = collector_strict_initial_parse(
        raw_a, {row["name"] for row in passing_bundle["catalog"]["entries"]}
    )
    assert collector_parse == {
        "status": arm_a["parser_status"],
        "candidate": arm_a["parsed_candidate"],
        "selection": arm_a["selection"],
    }
    allowed = collector_structured_responses(task["option_map"])
    for arm_name in ("B_structured_names", "C_structured_catalog"):
        assert trace["arms"][arm_name]["raw_response"] in allowed


def test_wilson_and_mcnemar_conventions_are_frozen():
    assert wilson_95(0, 516)[1] < 0.01
    assert wilson_95(516, 516)[0] > 0.99
    assert one_sided_mcnemar(0, 0) == 1.0
    assert one_sided_mcnemar(10, 0) == pytest.approx(1 / 1024)
    adjusted = holm_adjust({"a": 0.01, "b": 0.04})
    assert adjusted == {"a": 0.02, "b": 0.04}


@pytest.mark.parametrize(
    "mutation,error_fragment",
    [
        (lambda bundle: bundle["traces"].pop(), "trace count"),
        (
            lambda bundle: bundle["traces"].append(deepcopy(bundle["traces"][0])),
            "duplicate trace key",
        ),
        (
            lambda bundle: bundle["traces"][0].__setitem__("model_revision", "drift"),
            "model revision mismatch",
        ),
        (
            lambda bundle: bundle["hashes"].__setitem__("tasks_sha256", "9" * 64),
            "source hash mismatch",
        ),
        (
            lambda bundle: bundle["config"]["dependency_versions"].__setitem__(
                "numpy", "2.4.6"
            ),
            "dependency versions",
        ),
    ],
)
def test_completeness_identity_and_source_defects_are_invalid(
    passing_bundle, mutation, error_fragment
):
    bundle = deepcopy(passing_bundle)
    mutation(bundle)
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any(error_fragment in error for error in result["integrity"]["errors"])


def test_message_hash_and_reconstruction_are_independently_verified(passing_bundle):
    bundle = deepcopy(passing_bundle)
    arm = bundle["traces"][0]["arms"]["D_contextual_repair"]
    arm["messages"][-1]["content"] += " tampered"
    arm["messages_sha256"] = canonical_json_sha256(arm["messages"])
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any("messages differ from reconstruction" in error for error in result["integrity"]["errors"])


def test_repair_branch_must_bind_exact_A_response_bytes(passing_bundle):
    bundle = deepcopy(passing_bundle)
    bundle["traces"][0]["arms"]["E_decontextualized_repair"][
        "source_initial_sha256"
    ] = "0" * 64
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any("exact A response" in error for error in result["integrity"]["errors"])


@pytest.mark.parametrize("token_ids", [[], [255], [0, 159, 146, 150]])
def test_empty_or_arbitrary_generated_token_ids_are_invalid(passing_bundle, token_ids):
    bundle = deepcopy(passing_bundle)
    bundle["traces"][0]["arms"]["A_open_text"]["generated_token_ids"] = token_ids
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any(
        "token IDs" in error or "reconstruction failed" in error
        for error in result["integrity"]["errors"]
    )


def test_adjudicator_jsonl_reader_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "duplicate.jsonl"
    path.write_text('{"task_id":"a","task_id":"b"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read_jsonl(path)


def test_one_look_adjudicator_rejects_unregistered_self_mutation(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    script = root / "scripts" / "adjudicate_px062_gate2_2.py"
    script.parent.mkdir(parents=True)
    script.write_bytes(b"frozen adjudicator\n")
    registration_path = (
        root
        / "manifests"
        / "px062_gate2_2_20260728"
        / "confirmatory_registration.json"
    )
    registration_path.parent.mkdir(parents=True)
    registration_path.write_text(
        json.dumps(
            {
                "schema_version": "px062-gate2.2-launch-registration-v1",
                "frozen_evidence": {
                    "adjudicator": {
                        "path": "scripts/adjudicate_px062_gate2_2.py",
                        "sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                        "bytes": script.stat().st_size,
                        "included_in_collection_source_bundle": False,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(adjudicator_module, "__file__", str(script))
    _, record = verify_registered_adjudicator(root, registration_path)
    assert record["verified_before_outcome_read"] is True
    script.write_bytes(b"mutated adjudicator\n")
    with pytest.raises(ValueError, match="hash differs"):
        verify_registered_adjudicator(root, registration_path)


def test_adjudicator_rejects_post_fetch_trace_mutation(tmp_path):
    trace = tmp_path / "model_traces.jsonl"
    trace.write_bytes(b"sealed\n")
    receipt = tmp_path / "completion_fetch_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "px062-gate2.2-fetch-receipt-v1",
                "adjudication_run": False,
                "model_trace_structure_validated": True,
                "trace_summary_reconciled": True,
                "sealed_files": {
                    "model_traces.jsonl": {
                        "bytes": trace.stat().st_size,
                        "sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    verify_sealed_evidence(receipt, {"model_traces.jsonl": trace})
    trace.write_bytes(b"mutated\n")
    with pytest.raises(ValueError, match="differs from fetch seal"):
        verify_sealed_evidence(receipt, {"model_traces.jsonl": trace})


def test_A_parser_is_recomputed_not_trusted(passing_bundle):
    bundle = deepcopy(passing_bundle)
    bundle["traces"][0]["arms"]["A_open_text"]["parser_status"] = "valid_skill"
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any("parser status mismatch" in error for error in result["integrity"]["errors"])


def test_constrained_decoder_escape_is_integrity_failure(passing_bundle):
    bundle = deepcopy(passing_bundle)
    arm = bundle["traces"][0]["arms"]["C_structured_catalog"]
    arm.update(
        {
            "raw_response": "not-an-allowed-choice",
            "raw_response_sha256": text_sha256("not-an-allowed-choice"),
            "decoder_escape": True,
            "choice_id": None,
            "selection": None,
            "canonical_decision": '{"skill":null}',
        }
    )
    result = run(bundle)
    assert result["determination"] == "INVALID"
    assert any("constrained decoder escaped" in error for error in result["integrity"]["errors"])


def test_199_registered_A_invalid_events_is_not_evaluable_when_direct_gates_pass():
    result = run(make_fixture(invalid_registered_events_per_model=199))
    assert result["integrity"]["pass"] is True
    assert result["determination"] == "NOT_EVALUABLE"
    assert result["result_classification"] == "BOUNDED_SELECTOR_PASS"
    assert all(
        gates["direct_selector_pass"]
        and not gates["A_invalid_registered_event_sufficiency"]
        for gates in result["model_gates"].values()
    )


def test_D_NONE_harm_failure_remains_no_go_when_repair_power_is_insufficient():
    bundle = make_fixture(invalid_registered_events_per_model=199)
    none_ids = {
        row["task_id"] for row in bundle["answers"] if row["expected_skill"] is None
    }
    changed = 0
    for trace in bundle["traces"]:
        if (
            trace["model_id"] == MODELS[0]
            and trace["task_id"] in none_ids
            and trace["arms"]["D_contextual_repair"]["triggered"]
            and changed < 60
        ):
            replace_structured_selection(trace, "D_contextual_repair", "skill-00")
            changed += 1
    result = run(bundle)
    assert result["model_gates"][MODELS[0]][
        "A_invalid_registered_event_sufficiency"
    ] is False
    assert result["model_gates"][MODELS[0]]["D_NONE_wrong_existing_upper_pass"] is False
    assert result["determination"] == "CROSS_MODEL_NO_GO"


def test_direct_selector_semantic_failure_is_cross_model_fail(passing_bundle):
    bundle = deepcopy(passing_bundle)
    changed = 0
    for trace in bundle["traces"]:
        if trace["model_id"] != MODELS[0] or changed >= 300:
            continue
        answer = bundle["answers"][int(trace["task_id"].split("-")[1])]
        wrong = "skill-00" if answer["expected_skill"] is None else None
        replace_structured_selection(trace, "C_structured_catalog", wrong)
        changed += 1
    result = run(bundle)
    assert result["integrity"]["pass"] is True
    assert result["determination"] == "CROSS_MODEL_NO_GO"
    assert result["model_gates"][MODELS[0]]["direct_selector_pass"] is False


def test_C_wrong_existing_NONE_gate_cannot_be_hidden_by_high_overall_accuracy(
    passing_bundle,
):
    bundle = deepcopy(passing_bundle)
    none_ids = {
        row["task_id"] for row in bundle["answers"] if row["expected_skill"] is None
    }
    changed = 0
    for trace in bundle["traces"]:
        if (
            trace["model_id"] == MODELS[0]
            and trace["task_id"] in none_ids
            and changed < 60
        ):
            replace_structured_selection(trace, "C_structured_catalog", "skill-00")
            changed += 1
    result = run(bundle)
    metric = result["metrics"][MODELS[0]]["C_overall_accuracy"]
    assert metric["rate"] > 0.90
    assert result["model_gates"][MODELS[0]]["C_NONE_wrong_existing_upper_pass"] is False
    assert result["determination"] == "CROSS_MODEL_NO_GO"


def test_D_recovery_point_gate_is_enforced(passing_bundle):
    bundle = deepcopy(passing_bundle)
    answer_by_id = {row["task_id"]: row["expected_skill"] for row in bundle["answers"]}
    changed = 0
    for trace in bundle["traces"]:
        arm_a = trace["arms"]["A_open_text"]
        if (
            trace["model_id"] == MODELS[0]
            and arm_a["parser_status"] == "invalid"
            and answer_by_id[trace["task_id"]] is not None
            and changed < 100
        ):
            expected = answer_by_id[trace["task_id"]]
            wrong = "skill-00" if expected is None else None
            replace_structured_selection(trace, "D_contextual_repair", wrong)
            changed += 1
    result = run(bundle)
    assert result["integrity"]["pass"] is True
    assert result["metrics"][MODELS[0]][
        "D_registered_recovery_accuracy_on_A_invalid_registered"
    ]["rate"] < 0.60
    assert result["determination"] == "CROSS_MODEL_NO_GO"


def test_perfect_NONE_repairs_cannot_mask_failed_registered_recovery():
    bundle = make_fixture(
        invalid_registered_events_per_model=220,
        invalid_none_events_per_model=330,
    )
    answer_by_id = {row["task_id"]: row["expected_skill"] for row in bundle["answers"]}
    for trace in bundle["traces"]:
        if (
            trace["model_id"] == MODELS[0]
            and trace["arms"]["A_open_text"]["parser_status"] == "invalid"
            and answer_by_id[trace["task_id"]] is not None
        ):
            replace_structured_selection(trace, "D_contextual_repair", None)
    result = run(bundle)
    metrics = result["metrics"][MODELS[0]]
    # All 330 invalid NONE tasks are repaired correctly, making the old pooled
    # statistic look exactly adequate: 330 / (330 + 220) == .60.
    assert metrics["D_recovery_accuracy_on_all_A_invalid_diagnostic"]["rate"] == 0.60
    assert metrics[
        "D_registered_recovery_accuracy_on_A_invalid_registered"
    ]["rate"] == 0.0
    assert result["model_gates"][MODELS[0]][
        "D_registered_recovery_point_pass"
    ] is False
    assert result["determination"] == "CROSS_MODEL_NO_GO"


def test_D_minus_E_failure_does_not_erase_absolute_efficacy(passing_bundle):
    bundle = deepcopy(passing_bundle)
    answer_by_id = {row["task_id"]: row["expected_skill"] for row in bundle["answers"]}
    for trace in bundle["traces"]:
        if trace["model_id"] == MODELS[0] and trace["arms"]["A_open_text"][
            "parser_status"
        ] == "invalid":
            replace_structured_selection(
                trace,
                "E_decontextualized_repair",
                answer_by_id[trace["task_id"]],
            )
    result = run(bundle)
    paired = result["metrics"][MODELS[0]]["D_vs_E_registered_paired"]
    assert paired["accuracy_gain"] == 0.0
    assert paired["mcnemar_one_sided_p"] == 1.0
    assert paired["holm_adjusted_p"] == 1.0
    assert result["determination"] == "PASS"
    assert result["result_classification"] == "BOUNDED_EFFICACY_PASS"
    assert (
        result["context_mechanism_determination"]
        == "CONTEXT_MECHANISM_NOT_SUPPORTED"
    )


def test_D_NONE_harm_gate_is_enforced_separately(passing_bundle):
    bundle = deepcopy(passing_bundle)
    none_ids = {
        row["task_id"] for row in bundle["answers"] if row["expected_skill"] is None
    }
    changed = 0
    for trace in bundle["traces"]:
        if (
            trace["model_id"] == MODELS[0]
            and trace["task_id"] in none_ids
            and trace["arms"]["D_contextual_repair"]["triggered"]
            and changed < 60
        ):
            replace_structured_selection(trace, "D_contextual_repair", "skill-00")
            changed += 1
    result = run(bundle)
    assert changed == 60
    assert result["integrity"]["pass"] is True
    assert result["model_gates"][MODELS[0]]["D_NONE_wrong_existing_upper_pass"] is False
    assert result["determination"] == "CROSS_MODEL_NO_GO"


def test_config_contract_rejects_model_decoding_template_and_gate_drift():
    config = fixture_config()
    expected = adjudicator_module.adjudication_config_contract_sha256(config)
    mutations = []

    wrong_model = deepcopy(config)
    wrong_model["models"][0] = "attacker/model"
    mutations.append(wrong_model)

    wrong_revision = deepcopy(config)
    wrong_revision["model_revisions"][MODELS[0]] = "0" * 40
    mutations.append(wrong_revision)

    wrong_decoding = deepcopy(config)
    wrong_decoding["decoding"]["do_sample"] = True
    mutations.append(wrong_decoding)

    wrong_template = deepcopy(config)
    wrong_template["message_templates"]["open_system"] += " changed"
    mutations.append(wrong_template)

    wrong_gate = deepcopy(config)
    wrong_gate["gates"]["C_overall_accuracy_min"] = 0.74
    mutations.append(wrong_gate)

    for mutated in mutations:
        errors = adjudicator_module._config_errors(mutated, expected)
        assert errors
        assert any(
            "semantic contract" in error
            or "exact two frozen model" in error
            or "exact frozen model revisions" in error
            or "decoding contract" in error
            or "gates differ" in error
            for error in errors
        )


def minimal_one_look_authorization(root):
    authorization_path = root / DEFAULT_ADJUDICATION_AUTHORIZATION
    authorization_path.parent.mkdir(parents=True)
    authorization_path.write_text("registered authorization\n", encoding="utf-8")
    return authorization_path, {
        "canonical_result_path": DEFAULT_ADJUDICATION_RESULT.as_posix(),
        "consumption_marker_path": DEFAULT_ADJUDICATION_CONSUMPTION.as_posix(),
        "fetch_receipt": {"path": DEFAULT_FETCH_RECEIPT.as_posix()},
    }


def test_structural_path_errors_do_not_consume_one_look(tmp_path):
    authorization_path, authorization = minimal_one_look_authorization(tmp_path)
    marker = tmp_path / DEFAULT_ADJUDICATION_CONSUMPTION
    with pytest.raises(ValueError, match="alternative"):
        resolve_adjudication_paths(
            root=tmp_path,
            authorization=authorization,
            requested_output=tmp_path / "alternative-result.json",
            supplied_fetch_receipt=tmp_path / DEFAULT_FETCH_RECEIPT,
            supplied_inputs={},
        )
    assert not marker.exists()

    with pytest.raises(ValueError, match="canonical sealed file"):
        resolve_adjudication_paths(
            root=tmp_path,
            authorization=authorization,
            requested_output=tmp_path / DEFAULT_ADJUDICATION_RESULT,
            supplied_fetch_receipt=tmp_path / DEFAULT_FETCH_RECEIPT,
            supplied_inputs={"model_traces.jsonl": tmp_path / "wrong-traces.jsonl"},
        )
    assert not marker.exists()
    assert authorization_path.exists()


def test_adjudication_authorization_must_match_pushed_commit(tmp_path):
    authorization_path = tmp_path / DEFAULT_ADJUDICATION_AUTHORIZATION
    authorization_path.parent.mkdir(parents=True)
    authorization = {
        key: {} for key in adjudicator_module.ADJUDICATION_AUTHORIZATION_KEYS
    }
    authorization.update(
        {
            "schema_version": "px062-gate2.2-adjudication-authorization-v1",
            "one_look": {
                "allowed_adjudications": 1,
                "alternative_result_paths_allowed": False,
                "claim_must_precede_outcome_read": True,
                "started_claim_is_never_recoverable": True,
            },
        }
    )
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    raw = authorization_path.read_bytes()
    head = "a" * 40

    def blob_reader(root, commit, path):
        assert commit == head
        return raw

    state_reader = lambda root: {
        "head": head,
        "remote_refs": ["origin/test"],
    }
    _, record = verify_committed_adjudication_authorization(
        tmp_path,
        authorization_path,
        blob_reader=blob_reader,
        state_reader=state_reader,
    )
    assert record["authorization_commit"] == head
    authorization_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema drift|pushed HEAD"):
        verify_committed_adjudication_authorization(
            tmp_path,
            authorization_path,
            blob_reader=blob_reader,
            state_reader=state_reader,
        )


def test_one_look_claim_is_recoverable_only_before_outcome_boundary(tmp_path):
    authorization_path, authorization = minimal_one_look_authorization(tmp_path)
    output = tmp_path / DEFAULT_ADJUDICATION_RESULT
    output.parent.mkdir(parents=True, exist_ok=True)
    marker_path, claim = acquire_one_look_claim(
        root=tmp_path,
        authorization_path=authorization_path,
        authorization=authorization,
        requested_output=output,
        claimed_at_utc="2026-07-28T18:00:00Z",
    )
    with pytest.raises(FileExistsError, match="already claimed"):
        acquire_one_look_claim(
            root=tmp_path,
            authorization_path=authorization_path,
            authorization=authorization,
            requested_output=output,
        )
    marker_path, recovered = acquire_one_look_claim(
        root=tmp_path,
        authorization_path=authorization_path,
        authorization=authorization,
        requested_output=output,
        recover_pre_outcome=True,
        claimed_at_utc="2026-07-28T18:01:00Z",
    )
    assert recovered["claim_id"] == claim["claim_id"]
    assert recovered["recovery_count"] == 1
    started = mark_one_look_outcome_read_started(
        marker_path, recovered, started_at_utc="2026-07-28T18:02:00Z"
    )
    assert started["state"] == "OUTCOME_READ_STARTED"
    with pytest.raises(ValueError, match="not recoverable"):
        acquire_one_look_claim(
            root=tmp_path,
            authorization_path=authorization_path,
            authorization=authorization,
            requested_output=output,
            recover_pre_outcome=True,
        )
    output.write_text('{"determination":"PASS"}\n', encoding="utf-8")
    completed = complete_one_look_claim(
        marker_path,
        started,
        output,
        completed_at_utc="2026-07-28T18:03:00Z",
    )
    assert completed["state"] == "COMPLETED"
    assert completed["result_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()


def test_outcome_read_boundary_is_exclusive_and_fail_closed(tmp_path):
    authorization_path, authorization = minimal_one_look_authorization(tmp_path)
    output = tmp_path / DEFAULT_ADJUDICATION_RESULT
    output.parent.mkdir(parents=True, exist_ok=True)
    marker_path, claim = acquire_one_look_claim(
        root=tmp_path,
        authorization_path=authorization_path,
        authorization=authorization,
        requested_output=output,
    )
    boundary_path = marker_path.with_name(f"{marker_path.name}.outcome-read.lock")
    boundary_path.write_text("another process owns the boundary\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        mark_one_look_outcome_read_started(marker_path, claim)
    assert adjudicator_module.read_json(marker_path)["state"] == "CLAIMED_PRE_OUTCOME"


def make_gzip_tar(files, directories=()):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as handle:
        for directory in directories:
            info = tarfile.TarInfo(directory)
            info.type = tarfile.DIRTYPE
            info.size = 0
            handle.addfile(info)
        for name, raw in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            handle.addfile(info, io.BytesIO(raw))
    return buffer.getvalue()


def test_forged_traces_and_receipt_cannot_replace_aws_bound_output_archive(tmp_path):
    source_payloads = {
        "configs/px062_skill_selection_gate2_2_v1_0_20260728.json": b"config\n",
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl": b"tasks\n",
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json": b"catalog\n",
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json": b"benchmark\n",
    }
    bundle_manifest = b"bundle\n"
    source_archive_raw = make_gzip_tar(
        {**source_payloads, "bundle_manifest.json": bundle_manifest}
    )
    output_payloads = {
        "px062_gate2_2/frozen_config.json": source_payloads[
            "configs/px062_skill_selection_gate2_2_v1_0_20260728.json"
        ],
        "px062_gate2_2/source_bundle_manifest.json": bundle_manifest,
        "px062_gate2_2/collection_summary.json": b"summary\n",
        "px062_gate2_2/model_traces.jsonl": b"authentic trace\n",
        "px062_gate2_2/tokenizer_artifacts.tar.gz": b"tokenizer\n",
    }
    output_archive_raw = make_gzip_tar(
        output_payloads, directories=("px062_gate2_2",)
    )
    local_payloads = {
        "frozen_config.json": output_payloads["px062_gate2_2/frozen_config.json"],
        "tasks.jsonl": source_payloads[
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/frozen_inputs/tasks.jsonl"
        ],
        "answer_key.jsonl": b"answer\n",
        "registry_catalog.json": source_payloads[
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/frozen_inputs/registry_catalog.json"
        ],
        "benchmark_manifest.json": source_payloads[
            "reports/coding_agent_skill_provenance/"
            "gate2_2_context_structured_20260728/frozen_inputs/benchmark_manifest.json"
        ],
        "source_bundle_manifest.json": bundle_manifest,
        "collection_summary.json": output_payloads[
            "px062_gate2_2/collection_summary.json"
        ],
        "model_traces.jsonl": b"forged trace\n",
        "tokenizer_artifacts.tar.gz": output_payloads[
            "px062_gate2_2/tokenizer_artifacts.tar.gz"
        ],
        "source_artifact.tar.gz": source_archive_raw,
        "output_artifact.tar.gz": output_archive_raw,
    }
    inputs = {}
    for name, raw in local_payloads.items():
        path = tmp_path / name
        path.write_bytes(raw)
        inputs[name] = path
    source_sha = hashlib.sha256(source_archive_raw).hexdigest()
    output_sha = hashlib.sha256(output_archive_raw).hexdigest()
    def full_sha256_artifact(size: int, digest: str, version_id: str) -> dict:
        encoded = base64.b64encode(bytes.fromhex(digest)).decode()
        return {
            "bytes": size,
            "sha256": digest,
            "version_id": version_id,
            "checksum_algorithm": ["SHA256"],
            "checksum_type": "FULL_OBJECT",
            "checksums": {"ChecksumSHA256": encoded},
            "object_attributes_fingerprint": None,
            "checksum_verification": {
                "method": "LOCAL_FULL_OBJECT_RECOMPUTATION",
                "checksum_type": "FULL_OBJECT",
                "object_attributes_sha256": None,
                "algorithms": {
                    "SHA256": {
                        "field": "ChecksumSHA256",
                        "registered_value": encoded,
                        "local_value": encoded,
                        "parts_recomputed": 0,
                        "backend": "python-hashlib",
                    }
                },
            },
        }
    receipt = {
        "source_artifact": full_sha256_artifact(
            len(source_archive_raw), source_sha, "source-v1"
        ),
        "output_artifact": full_sha256_artifact(
            len(output_archive_raw), output_sha, "output-v1"
        ),
        # A forger can recompute this local receipt record, but not the member
        # inside the AWS-checksummed output archive.
        "sealed_files": {
            "model_traces.jsonl": {
                "bytes": inputs["model_traces.jsonl"].stat().st_size,
                "sha256": hashlib.sha256(
                    inputs["model_traces.jsonl"].read_bytes()
                ).hexdigest(),
            }
        },
    }
    launch = {
        "source_bundle": {
            "manifest": {
                "files": {
                    name: {
                        "bytes": len(raw),
                        "sha256": hashlib.sha256(raw).hexdigest(),
                    }
                    for name, raw in source_payloads.items()
                }
            }
        }
    }
    with pytest.raises(ValueError, match="sealed outcome differs"):
        verify_registered_cloud_archives(
            launch=launch, receipt=receipt, inputs=inputs
        )
