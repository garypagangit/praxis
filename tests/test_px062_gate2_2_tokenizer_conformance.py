import hashlib
from copy import deepcopy

import pytest

import scripts.check_px062_gate2_2_tokenizer_conformance as checker


def fixture_config():
    return {
        "expected_registry_names": 2,
        "expected_tasks": 1,
        "decoding": {
            "open_max_new_tokens": 32,
            "choice_count": 3,
            "structured_response_schema": '{"choice":"Snnn"}',
        },
        "message_templates": {
            "open_system": "open",
            "open_user": "task={task}",
            "structured_system": "structured",
            "direct_names_user": "task={task}\nnames={catalog}",
            "direct_catalog_user": "task={task}\ncatalog={catalog}",
            "contextual_repair_user": (
                'repair {catalog}; exactly {{"choice":"Snnn"}}'
            ),
            "decontextualized_task_placeholder": "TASK WITHHELD",
        },
    }


def fixture_task():
    return {
        "task_id": "t1",
        "prompt": "do alpha",
        "option_map": [
            {"id": "S001", "skill": "alpha"},
            {"id": "S002", "skill": None},
            {"id": "S003", "skill": "beta"},
        ],
    }


class FakeTokenizer:
    eos_token_id = 2

    def __init__(self):
        self._decodes = {}
        self.decode_kwargs = []

    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        ids = list(range(10, 10 + len(text.split())))
        self._decodes[tuple(ids)] = text
        return ids

    def decode(self, ids, **kwargs):
        self.decode_kwargs.append(kwargs)
        return self._decodes[tuple(ids)]

    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        assert tokenize is False
        assert add_generation_prompt is True
        return "\n".join(f"{row['role']}:{row['content']}" for row in messages)

    def __call__(self, rendered, add_special_tokens=True):
        assert add_special_tokens is True
        return {"input_ids": list(rendered.encode("utf-8"))}


def test_exact_open_probe_uses_full_32_token_budget_and_clean_decode():
    tokenizer = FakeTokenizer()
    probe = checker.build_exact_open_response_probe(tokenizer, 32)
    assert len(tokenizer.encode(probe, add_special_tokens=False)) == 32
    assert tokenizer.decode_kwargs[-1] == {
        "skip_special_tokens": True,
        "clean_up_tokenization_spaces": False,
    }


def test_choice_roundtrip_requires_clean_up_disabled_and_unique_sequences():
    tokenizer = FakeTokenizer()
    choices = ['{"choice":"S001"}', '{"choice":"S002"}']
    # FakeTokenizer's whitespace tokenizer aliases both choices.
    with pytest.raises(ValueError, match="share a token sequence"):
        checker.verify_choice_roundtrips(tokenizer, choices)
    assert all(
        call["clean_up_tokenization_spaces"] is False
        for call in tokenizer.decode_kwargs
    )


def test_exact_A_to_E_constructors_enforce_clean_context_ablation():
    messages = checker.construct_all_messages(
        fixture_config(),
        fixture_task(),
        {"alpha": "Alpha work", "beta": "Beta work"},
        "x " * 31 + "x",
    )
    assert tuple(messages) == checker.EXPECTED_ARMS
    assert [row["role"] for row in messages["D_contextual_repair"]] == [
        "system",
        "user",
        "assistant",
        "user",
    ]
    assert messages["D_contextual_repair"][2:] == messages[
        "E_decontextualized_repair"
    ][2:]
    assert messages["D_contextual_repair"][1] != messages[
        "E_decontextualized_repair"
    ][1]


def test_template_formatting_error_is_rejected_with_task_context():
    config = fixture_config()
    config["message_templates"]["contextual_repair_user"] = "{missing}"
    with pytest.raises(ValueError, match="formatting failed for t1"):
        checker.construct_all_messages(
            config,
            fixture_task(),
            {"alpha": "Alpha work", "beta": "Beta work"},
            "invalid",
        )


def test_protocol_rejects_replacement_task_hash_drift(tmp_path, monkeypatch):
    tasks = tmp_path / "tasks.jsonl"
    tasks.write_text("{}\n", encoding="utf-8")
    config = {
        "models": list(checker.EXPECTED_MODEL_REVISIONS),
        "model_revisions": checker.EXPECTED_MODEL_REVISIONS,
        "dependency_versions": checker.EXPECTED_DEPENDENCIES,
        "arms": list(checker.EXPECTED_ARMS),
        "decoding": {
            "open_max_new_tokens": 32,
            "choice_count": 44,
            "structured_response_schema": '{"choice":"Snnn"}',
        },
    }
    with pytest.raises(ValueError, match="replacement task hash drift"):
        checker.validate_protocol(config, tasks)
    monkeypatch.setattr(
        checker, "EXPECTED_TASKS_SHA256", hashlib.sha256(tasks.read_bytes()).hexdigest()
    )
    assert checker.validate_protocol(config, tasks)["tasks_sha256"] == hashlib.sha256(
        tasks.read_bytes()
    ).hexdigest()


def test_complete_dependency_contract_is_required(monkeypatch):
    expected = checker.EXPECTED_DEPENDENCIES
    monkeypatch.setattr(
        checker.importlib.metadata,
        "version",
        lambda package: expected[package],
    )
    assert checker.check_dependencies() == expected
    monkeypatch.setattr(
        checker.importlib.metadata,
        "version",
        lambda package: "0.0" if package == "torch" else expected[package],
    )
    with pytest.raises(ValueError, match="torch"):
        checker.check_dependencies()


def test_semantic_config_projection_excludes_only_postcheck_freeze_metadata():
    config = {
        "status": "REDESIGN_PENDING",
        "source_integrity": {"tasks_sha256": "PENDING"},
        "label_audit_protocol": {
            "runner_sha256": "old-runner",
            "protocol_sha256": "old-protocol",
            "tests_sha256": "old-tests",
            "prompt_template_sha256": "prompt",
        },
        "models": ["model-a"],
        "gates": {"accuracy": 0.75},
    }
    record = checker.semantic_config_projection_record(config)
    finalized = deepcopy(config)
    finalized["status"] = "FROZEN_PREREGISTERED"
    finalized["source_integrity"] = {"tasks_sha256": "a" * 64}
    finalized["label_audit_protocol"]["runner_sha256"] = "b" * 64
    finalized["label_audit_protocol"]["protocol_sha256"] = "c" * 64
    finalized["label_audit_protocol"]["tests_sha256"] = "d" * 64
    assert checker.semantic_config_projection_record(finalized) == record

    finalized["gates"]["accuracy"] = 0.76
    assert checker.semantic_config_projection_record(finalized) != record
