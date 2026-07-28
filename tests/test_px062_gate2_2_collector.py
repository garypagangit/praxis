import hashlib
import json

import pytest

from scripts.run_px062_gate2_2_models import (
    _allowed_next_tokens,
    canonical_json_sha256,
    contextual_repair_messages,
    decoded_completion_record,
    decontextualized_repair_messages,
    direct_messages,
    option_lookup,
    render_catalog,
    strict_initial_parse,
    structured_responses,
    validate_frozen_inputs,
    validate_environment,
    validate_option_map,
    validate_sources,
)


def config():
    return {
        "expected_tasks": 1,
        "expected_registry_names": 2,
        "message_templates": {
            "open_system": "open-system",
            "open_user": "task={task}",
            "structured_system": "structured-system",
            "direct_names_user": "task={task}\nnames={catalog}",
            "direct_catalog_user": "task={task}\ncatalog={catalog}",
            "contextual_repair_user": "repair={catalog}",
            "decontextualized_task_placeholder": "TASK WITHHELD",
        },
    }


def option_map():
    return [
        {"id": "S001", "skill": "beta"},
        {"id": "S002", "skill": None},
        {"id": "S003", "skill": "alpha"},
    ]


def test_initial_parser_preserves_gate21_exactness_failure():
    names = {"alpha", "beta"}
    assert strict_initial_parse("alpha", names)["status"] == "valid_skill"
    assert strict_initial_parse("NONE", names)["status"] == "explicit_none"
    for raw in ("Alpha", "`alpha`", "The answer is alpha", "alpha\nextra", ""):
        assert strict_initial_parse(raw, names)["status"] == "invalid"


def test_option_map_must_be_closed_world_and_include_none_once():
    validate_option_map(option_map(), {"alpha", "beta"})
    broken = option_map()
    broken[-1] = {"id": "S003", "skill": "beta"}
    with pytest.raises(ValueError, match="frozen registry"):
        validate_option_map(broken, {"alpha", "beta"})


def test_structured_responses_are_exact_json_local_ids():
    responses = structured_responses(option_map())
    assert responses == {
        '{"choice":"S001"}': "S001",
        '{"choice":"S002"}': "S002",
        '{"choice":"S003"}': "S003",
    }
    assert option_lookup(option_map())["S002"] is None


def test_catalog_arms_share_order_but_only_c_has_descriptions():
    descriptions = {"alpha": "Alpha description", "beta": "Beta description"}
    names = render_catalog(option_map(), descriptions, include_descriptions=False)
    full = render_catalog(option_map(), descriptions, include_descriptions=True)
    assert [line.split(":", 1)[0] for line in names.splitlines()] == [
        line.split(":", 1)[0] for line in full.splitlines()
    ]
    assert "Alpha description" not in names
    assert "Alpha description" in full


def test_contextual_branch_keeps_exact_initial_conversation():
    cfg = config()
    initial_messages = [
        {"role": "system", "content": "open-system"},
        {"role": "user", "content": "task=do work"},
    ]
    raw = "I recommend alpha-pro."
    contextual = contextual_repair_messages(cfg, initial_messages, raw, "catalog")
    decontextual = decontextualized_repair_messages(cfg, raw, "catalog")
    assert contextual[:2] == initial_messages
    assert contextual[2] == {"role": "assistant", "content": raw}
    assert "do work" not in json.dumps(decontextual)
    assert [message["role"] for message in contextual] == [
        "system", "user", "assistant", "user"
    ]
    assert [message["role"] for message in decontextual] == [
        "system", "user", "assistant", "user"
    ]
    assert decontextual[1]["content"] == "TASK WITHHELD"
    assert decontextual[2] == {"role": "assistant", "content": raw}
    assert decontextual[3] == contextual[3]
    assert decontextual[0] == initial_messages[0]


class _FakeTokenizer:
    def __init__(self, decoded):
        self.decoded = decoded

    def decode(self, token_ids, **kwargs):
        assert kwargs == {
            "skip_special_tokens": True,
            "clean_up_tokenization_spaces": False,
        }
        return self.decoded


def test_exact_completion_bytes_are_untrimmed_and_independently_reconstructed():
    record = decoded_completion_record(
        _FakeTokenizer("  alpha\n"), _FakeTokenizer("  alpha\n"), [7, 8, 2]
    )
    assert record["raw_response"] == "  alpha\n"
    assert record["raw_response_bytes"] == len(b"  alpha\n")
    assert record["generated_token_ids"] == [7, 8, 2]
    assert record["tokenizer_reconstruction_verified"] is True


def test_empty_or_mismatched_completion_tokens_are_rejected():
    with pytest.raises(ValueError, match="no completion token IDs"):
        decoded_completion_record(_FakeTokenizer(""), _FakeTokenizer(""), [])
    with pytest.raises(ValueError, match="different bytes"):
        decoded_completion_record(_FakeTokenizer("alpha"), _FakeTokenizer("beta"), [7])


def test_names_and_catalog_direct_prompts_differ_only_by_template_payload():
    cfg = config()
    task = {"prompt": "do the thing"}
    names = direct_messages(cfg, task, "S001: alpha", include_descriptions=False)
    full = direct_messages(
        cfg, task, "S001: alpha — Alpha description", include_descriptions=True
    )
    assert names[0] == full[0]
    assert "do the thing" in names[1]["content"]
    assert "do the thing" in full[1]["content"]


def test_prefix_trie_never_allows_token_outside_choice_set():
    # Choices are token sequences [1,2] and [1,3].
    sequences = [(1, 2), (1, 3)]
    assert _allowed_next_tokens((), sequences, 99) == [1]
    assert _allowed_next_tokens((1,), sequences, 99) == [2, 3]
    assert _allowed_next_tokens((1, 2), sequences, 99) == [99]
    assert _allowed_next_tokens((7,), sequences, 99) == [99]


def test_frozen_task_file_must_be_answer_key_blind():
    cfg = config()
    catalog = {
        "entries": [
            {"name": "alpha", "description": "A"},
            {"name": "beta", "description": "B"},
        ]
    }
    task = {"task_id": "t1", "prompt": "work", "option_map": option_map()}
    validate_frozen_inputs(cfg, [task], catalog)
    task["expected_skill"] = "alpha"
    with pytest.raises(ValueError, match="answer-key"):
        validate_frozen_inputs(cfg, [task], catalog)


def test_canonical_hash_is_order_independent_for_object_keys():
    first = canonical_json_sha256({"b": 2, "a": 1})
    second = canonical_json_sha256({"a": 1, "b": 2})
    assert first == second
    assert first == hashlib.sha256(b'{"a":1,"b":2}').hexdigest()


def test_source_gate_binds_audited_manifest_without_exposing_answer_key(tmp_path):
    tasks = tmp_path / "tasks.jsonl"
    catalog = tmp_path / "catalog.json"
    manifest = tmp_path / "manifest.json"
    tasks.write_text("{}\n", encoding="utf-8")
    catalog.write_text("{}\n", encoding="utf-8")
    task_hash = hashlib.sha256(tasks.read_bytes()).hexdigest()
    catalog_hash = hashlib.sha256(catalog.read_bytes()).hexdigest()
    answer_hash = "a" * 64
    payload = {
        "benchmark_status": "AUDITED_CONFIRMATORY_INPUTS_READY_TO_FREEZE",
        "artifacts": {
            "tasks.jsonl": {"sha256": task_hash},
            "answer_key.jsonl": {"sha256": answer_hash},
            "registry_catalog.json": {"sha256": catalog_hash},
        },
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    cfg = {
        "source_integrity": {
            "tasks_sha256": task_hash,
            "answer_key_sha256": answer_hash,
            "registry_catalog_sha256": catalog_hash,
            "benchmark_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        }
    }
    validate_sources(cfg, tasks, catalog, manifest)
    payload["benchmark_status"] = "PENDING_AUDIT"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    cfg["source_integrity"]["benchmark_manifest_sha256"] = hashlib.sha256(
        manifest.read_bytes()
    ).hexdigest()
    with pytest.raises(ValueError, match="not independently audited"):
        validate_sources(cfg, tasks, catalog, manifest)


def test_runtime_environment_requires_frozen_numpy_version():
    cfg = {"dependency_versions": {"numpy": "1.26.4"}, "require_cuda": False}
    validate_environment(cfg, {"numpy": "1.26.4", "cuda_available": False})
    with pytest.raises(ValueError, match="numpy"):
        validate_environment(cfg, {"numpy": "2.4.6", "cuda_available": False})
