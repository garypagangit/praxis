from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

import scripts.run_px062_gate2_2_blind_audit as audit


def make_catalog() -> dict:
    names = [f"skill-{index:02d}" for index in range(43)]
    return {
        "schema_version": "fixture",
        "names": names,
        "entries": [
            {
                "name": name,
                "description": f"Canonical description for {name}.",
                "source_paths": [f"skills/{name}/SKILL.md"],
            }
            for name in names
        ],
    }


def make_tasks(count: int, names: list[str]) -> list[dict]:
    options = [
        {"id": f"S{position:03d}", "skill": skill}
        for position, skill in enumerate([*names, None], 1)
    ]
    rows = []
    for index in range(count):
        prompt = f"Synthetic blinded request {index}"
        rows.append(
            {
                "task_id": audit.task_id_for_prompt(prompt),
                "prompt": prompt,
                "option_map": options,
            }
        )
    return rows


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(audit.canonical_json_bytes(row) + b"\n" for row in rows)


def test_frozen_partition_is_exactly_43_stateless_batches_of_24():
    rows = [{} for _ in range(1032)]
    batches = audit.make_batches(rows)
    assert len(batches) == 43
    assert {len(batch) for batch in batches} == {24}
    assert sum(map(len, batches)) == 1032


def test_task_id_formula_is_exact_and_mutation_is_rejected():
    catalog = make_catalog()
    tasks = make_tasks(1032, catalog["names"])
    prompt = tasks[0]["prompt"]
    expected = "g22-" + hashlib.sha256(
        (
            json.dumps(
                {
                    "namespace": "px062-gate2.2-collection-visible-prompt-v1",
                    "prompt": prompt,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    ).hexdigest()[:20]
    assert tasks[0]["task_id"] == expected
    tasks[0]["task_id"] = "g22-" + "0" * 20
    with pytest.raises(audit.AuditError, match="ID derivation drift"):
        audit.validate_tasks(tasks, catalog["names"])


def test_checked_in_all_1032_task_ids_match_builder_formula():
    tasks_raw = audit.read_expected_bytes(
        audit.TASKS_PATH, audit.EXPECTED_TASKS_SHA256, "frozen tasks"
    )
    catalog_raw = audit.read_expected_bytes(
        audit.CATALOG_PATH, audit.EXPECTED_CATALOG_SHA256, "registry catalog"
    )
    tasks = audit.read_jsonl_bytes(tasks_raw, "frozen tasks")
    _, names, _ = audit.load_catalog(catalog_raw)
    assert tasks[0]["task_id"] == "g22-5de3b03d8a6d5cbb40c9"
    assert audit.task_id_for_prompt(tasks[0]["prompt"]) == tasks[0]["task_id"]
    audit.validate_tasks(tasks, names)


def test_checked_in_real_seed_bank_passes_audit_governance_preflight():
    seed, _ = audit._strict_json_file(
        audit.ROOT / audit.SEED_RELATIVE_PATH, "checked-in task seed bank"
    )
    assert "label_governance" in seed
    assert "label_audit_governance" not in seed
    assert audit.validate_pending_seed_governance(seed) == {
        "required": 2,
        "completed": 0,
        "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
        "audit_1_status": "PENDING",
        "audit_2_status": "PENDING",
        "resolution_status": "PENDING",
    }


def test_git_checkpoint_rejects_dirty_and_unpushed_states():
    common = {
        "head": "a" * 40,
        "branch": "main",
        "upstream_ref": "origin/main",
        "upstream_commit": "a" * 40,
        "remote_commit": "a" * 40,
    }
    with pytest.raises(audit.AuditError, match="dirty"):
        audit.validate_git_checkpoint_state(tracked_status=" M scripts/x.py", **common)
    with pytest.raises(audit.AuditError, match="not exactly pushed"):
        audit.validate_git_checkpoint_state(
            tracked_status="", **{**common, "remote_commit": "b" * 40}
        )


def test_command_is_fail_closed_and_has_no_resume_or_model_fallback(tmp_path):
    command = audit.build_command(
        "codex",
        "gpt-5.6-sol",
        tmp_path / "empty",
        tmp_path / "schema.json",
        tmp_path / "last.json",
    )
    joined = " ".join(command)
    assert command[:2] == ["codex", "exec"]
    for flag in (
        "--ephemeral",
        "--ignore-user-config",
        "--ignore-rules",
        "--skip-git-repo-check",
        "--json",
    ):
        assert flag in command
    assert "--sandbox read-only" in joined
    assert '--model gpt-5.6-sol' in joined
    assert 'model_reasoning_effort="high"' in command
    assert "resume" not in command
    assert command[-1] == "-"
    for feature in audit.DISABLED_FEATURES:
        assert f"--disable {feature}" in joined


def test_dynamic_schema_freezes_batch_ids_catalog_and_null():
    catalog = make_catalog()
    tasks = make_tasks(24, catalog["names"])
    schema = audit.build_output_schema(tasks, catalog["names"])
    row = schema["properties"]["rows"]["items"]
    assert row["additionalProperties"] is False
    assert row["properties"]["task_id"]["enum"] == [task["task_id"] for task in tasks]
    assert row["properties"]["predicted_skill"]["enum"] == [*catalog["names"], None]
    assert set(row["required"]) == {"task_id", "predicted_skill", "confidence", "note"}


def test_model_facing_prompt_projection_excludes_option_map():
    catalog = make_catalog()
    tasks = make_tasks(24, catalog["names"])
    semantic = {
        "schema_version": "synthetic",
        "names": catalog["names"],
        "entries": [
            {"name": entry["name"], "description": entry["description"]}
            for entry in catalog["entries"]
        ],
    }
    prompt = audit.build_prompt(1, tasks, audit.canonical_json_bytes(semantic))
    assert b'"option_map"' not in prompt
    projected = audit.project_tasks_for_auditor(tasks)
    assert all(list(row) == ["task_id", "prompt"] for row in projected)
    assert audit.canonical_json_bytes(projected) in prompt
    assert b"ANSWER_KEY_SENTINEL_MUST_NOT_LEAK" not in prompt
    assert b"SEED_BANK_SENTINEL_MUST_NOT_LEAK" not in prompt


def test_timeout_is_frozen_and_not_a_run_audit_override():
    assert audit.ATTEMPT_TIMEOUT_SECONDS == 1800
    assert "timeout_seconds" not in inspect.signature(audit.run_audit).parameters


def test_checked_in_config_has_complete_audit_preflight_contract():
    config = json.loads(
        (audit.ROOT / audit.CONFIG_RELATIVE_PATH).read_text(encoding="utf-8")
    )
    protocol = config["label_audit_protocol"]
    assert set(protocol) == {
        "codex_cli_version",
        "slot_models",
        "model_reasoning_effort",
        "sampling_parameters",
        "batches_per_auditor",
        "tasks_per_batch",
        "stateless_ephemeral_sessions",
        "prompt_template_sha256",
        "runner_sha256",
        "protocol_sha256",
        "tests_sha256",
        "model_facing_task_fields",
        "option_map_withheld_from_auditors",
        "exact_command_shape",
        "acceptance",
    }
    assert protocol["codex_cli_version"] == audit.EXPECTED_CODEX_VERSION
    assert protocol["slot_models"] == {"1": "gpt-5.6-sol", "2": "gpt-5.6-terra"}
    assert protocol["model_reasoning_effort"] == "high"
    assert protocol["batches_per_auditor"] == 43
    assert protocol["tasks_per_batch"] == 24
    assert protocol["stateless_ephemeral_sessions"] is True
    assert protocol["model_facing_task_fields"] == ["task_id", "prompt"]
    assert protocol["option_map_withheld_from_auditors"] is True
    assert protocol["exact_command_shape"] == audit.CONFIG_EXACT_COMMAND_SHAPE
    assert protocol["acceptance"] == (
        "both sealed audits and the answer key must agree on all 1032 tasks"
    )
    for key in ("runner_sha256", "protocol_sha256", "tests_sha256"):
        assert len(protocol[key]) == 64
        int(protocol[key], 16)


def test_strict_json_rejects_duplicate_keys_and_string_none():
    with pytest.raises(audit.AuditError, match="duplicate JSON key"):
        audit.strict_json_loads('{"task_id":"a","task_id":"b"}')

    catalog = make_catalog()
    tasks = make_tasks(24, catalog["names"])
    rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    rows[0]["predicted_skill"] = "NONE"
    with pytest.raises(audit.AuditError, match="outside catalog"):
        audit.validate_response({"rows": rows}, tasks, set(catalog["names"]))


@pytest.mark.parametrize(
    "item_type",
    ["command_execution", "mcp_tool_call", "web_search", "computer_use", "tool_call"],
)
def test_event_guard_rejects_every_tool_command_web_and_mcp_item(item_type):
    events = (
        json.dumps({"type": "thread.started", "thread_id": "session-1"})
        + "\n"
        + json.dumps({"type": "item.completed", "item": {"type": item_type}})
        + "\n"
    ).encode()
    with pytest.raises(audit.EventPolicyError, match="forbidden tool"):
        audit.inspect_event_log(events, "gpt-5.6-sol")


def test_event_guard_accepts_messages_reasoning_usage_and_records_non_exposure():
    events = b"\n".join(
        [
            b'{"type":"thread.started","thread_id":"session-1"}',
            b'{"type":"turn.started"}',
            b'{"type":"item.completed","item":{"type":"reasoning","text":"private summary"}}',
            b'{"type":"item.completed","item":{"type":"agent_message","text":"{}"}}',
            b'{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}',
            b"",
        ]
    )
    summary = audit.inspect_event_log(events, "gpt-5.6-sol")
    assert summary["session_id"] == "session-1"
    assert summary["model_metadata_exposure"] == "not_exposed_by_codex_json"
    assert summary["reasoning_metadata_exposure"] == "not_exposed_by_codex_json"
    assert summary["has_error_event"] is False


def test_event_guard_rejects_nonfinal_agent_message_text():
    events = b"\n".join(
        [
            b'{"type":"thread.started","thread_id":"session-1"}',
            b'{"type":"turn.started"}',
            b'{"type":"item.updated","item":{"type":"agent_message","text":"partial"}}',
            b'{"type":"item.completed","item":{"type":"agent_message","text":"{}"}}',
            b'{"type":"turn.completed","usage":{}}',
            b"",
        ]
    )
    with pytest.raises(audit.EventPolicyError, match="non-final"):
        audit.inspect_event_log(events, "gpt-5.6-sol")


def test_invalid_event_log_still_records_one_exposed_thread_id():
    raw = (
        b'{"type":"thread.started","thread_id":"recover-me"}\n'
        b'{not-valid-json}\n'
    )
    assert audit.extract_exposed_thread_id(raw) == "recover-me"


def test_event_guard_fails_on_exposed_model_or_reasoning_downgrade():
    def complete_thread(metadata: str) -> bytes:
        return (
            f'{{"type":"thread.started","thread_id":"s",{metadata}}}\n'
            '{"type":"turn.started"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"{}"}}\n'
            '{"type":"turn.completed","usage":{}}\n'
        ).encode()

    wrong_model = complete_thread('"model":"fallback"')
    with pytest.raises(audit.EventPolicyError, match="model contradicts"):
        audit.inspect_event_log(wrong_model, "gpt-5.6-sol")
    wrong_effort = complete_thread('"reasoning_effort":"none"')
    with pytest.raises(audit.EventPolicyError, match="reasoning effort contradicts"):
        audit.inspect_event_log(wrong_effort, "gpt-5.6-sol")


def test_hash_is_checked_before_json_is_parsed(tmp_path):
    path = tmp_path / "tasks.jsonl"
    path.write_bytes(b"not json\n")
    with pytest.raises(audit.AuditError, match="SHA-256 mismatch"):
        audit.read_expected_bytes(path, "0" * 64, "frozen tasks")


def test_existing_canonical_or_sidecar_refuses_before_codex(tmp_path):
    paths = audit.output_paths(tmp_path, 1)
    paths["audit"].parent.mkdir(parents=True)
    paths["audit"].write_text("sealed\n", encoding="utf-8")
    with pytest.raises(audit.AuditError, match="refusing overwrite/resume"):
        audit.run_audit(1, root=tmp_path, codex_executable="codex")


def _prepare_fixture_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    catalog = make_catalog()
    tasks = make_tasks(2, catalog["names"])
    frozen = (
        tmp_path
        / "reports"
        / "coding_agent_skill_provenance"
        / "gate2_2_context_structured_20260728"
        / "frozen_inputs"
    )
    frozen.mkdir(parents=True)
    (frozen.parent / "LABEL_AUDIT_PROTOCOL_20260728.md").write_text(
        "synthetic protocol\n", encoding="utf-8"
    )
    runner = tmp_path / "scripts" / "run_px062_gate2_2_blind_audit.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# synthetic runner\n", encoding="utf-8")
    tasks_raw = jsonl_bytes(tasks)
    catalog_raw = audit.canonical_json_bytes(catalog)
    (frozen / "tasks.jsonl").write_bytes(tasks_raw)
    (frozen / "registry_catalog.json").write_bytes(catalog_raw)
    monkeypatch.setattr(audit, "EXPECTED_TASKS", 2)
    monkeypatch.setattr(audit, "BATCH_SIZE", 2)
    monkeypatch.setattr(audit, "EXPECTED_BATCHES", 1)
    monkeypatch.setattr(audit, "EXPECTED_TASKS_SHA256", hashlib.sha256(tasks_raw).hexdigest())
    monkeypatch.setattr(audit, "EXPECTED_CATALOG_SHA256", hashlib.sha256(catalog_raw).hexdigest())
    monkeypatch.setattr(audit, "_codex_version", lambda _: audit.EXPECTED_CODEX_VERSION)
    checkpoint = {
        "schema_version": "synthetic-checkpoint-v1",
        "head_commit": "a" * 40,
        "remote_commit": "a" * 40,
        "config_sha256": "b" * 64,
        "pending_answer_sha256": "c" * 64,
        "synthetic_answer_content": "ANSWER_KEY_SENTINEL_MUST_NOT_LEAK",
        "synthetic_seed_content": "SEED_BANK_SENTINEL_MUST_NOT_LEAK",
    }
    monkeypatch.setattr(audit, "collect_repository_checkpoint", lambda root: checkpoint)
    return catalog, tasks


def _historical_git_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    catalog, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    frozen = (
        tmp_path
        / "reports"
        / "coding_agent_skill_provenance"
        / "gate2_2_context_structured_20260728"
        / "frozen_inputs"
    )
    tasks_raw = (frozen / "tasks.jsonl").read_bytes()
    catalog_raw = (frozen / "registry_catalog.json").read_bytes()
    answer_raw = jsonl_bytes(
        [
            {
                "task_id": task["task_id"],
                "label_audit_status": "PENDING_TWO_INDEPENDENT_AUDITS",
            }
            for task in tasks
        ]
    )
    manifest_raw = b'{"schema_version":"synthetic"}\n'
    seed_raw = audit.canonical_json_bytes(
        {
            "label_governance": {
                "required_independent_label_audits": 2,
                "completed_independent_label_audits": 0,
                "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
                "audit_1_status": "PENDING",
                "audit_2_status": "PENDING",
                "audit_resolution_status": "PENDING",
            }
        }
    )
    runner_raw = (tmp_path / audit.RUNNER_RELATIVE_PATH).read_bytes()
    protocol_raw = (tmp_path / audit.PROTOCOL_RELATIVE_PATH).read_bytes()
    tests_raw = b"# synthetic historical tests\n"
    source_integrity = {
        "tasks_sha256": hashlib.sha256(tasks_raw).hexdigest(),
        "answer_key_sha256": hashlib.sha256(answer_raw).hexdigest(),
        "registry_catalog_sha256": hashlib.sha256(catalog_raw).hexdigest(),
        "benchmark_manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
    }
    protocol_config = audit.expected_label_audit_protocol_config(
        runner_sha256=hashlib.sha256(runner_raw).hexdigest(),
        protocol_sha256=hashlib.sha256(protocol_raw).hexdigest(),
        tests_sha256=hashlib.sha256(tests_raw).hexdigest(),
    )
    config_raw = audit.canonical_json_bytes(
        {
            "status": "REDESIGN_PENDING_FRESH_CORPUS_AND_DUAL_LABEL_AUDIT",
            "expected_tasks": len(tasks),
            "source_integrity": source_integrity,
            "label_audit_protocol": protocol_config,
        }
    )
    raw_by_path = {
        audit.TRACKED_CHECKPOINT_PATHS[0].as_posix(): tasks_raw,
        audit.TRACKED_CHECKPOINT_PATHS[1].as_posix(): catalog_raw,
        audit.ANSWER_RELATIVE_PATH.as_posix(): answer_raw,
        audit.MANIFEST_RELATIVE_PATH.as_posix(): manifest_raw,
        audit.SEED_RELATIVE_PATH.as_posix(): seed_raw,
        audit.CONFIG_RELATIVE_PATH.as_posix(): config_raw,
        audit.RUNNER_RELATIVE_PATH.as_posix(): runner_raw,
        audit.PROTOCOL_RELATIVE_PATH.as_posix(): protocol_raw,
        audit.TESTS_RELATIVE_PATH.as_posix(): tests_raw,
    }
    blob_by_path = {
        path: f"{index + 1:040x}" for index, path in enumerate(sorted(raw_by_path))
    }
    state = {
        "absent": False,
        "nonancestor": False,
        "raw_by_blob": {blob_by_path[path]: raw for path, raw in raw_by_path.items()},
        "blob_by_path": blob_by_path,
    }
    head = "a" * 40
    current_head = "b" * 40
    tracked_files = {
        path: {
            "head_blob": blob_by_path[path],
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
        for path, raw in raw_by_path.items()
    }
    checkpoint = {
        "schema_version": "px062-gate2.2-repository-checkpoint-v1",
        "head_commit": head,
        "branch": "main",
        "upstream_ref": "origin/main",
        "upstream_commit": head,
        "remote_ref": "refs/heads/main",
        "remote_commit": head,
        "tracked_tree_clean": True,
        "tracked_files": tracked_files,
        "config_sha256": hashlib.sha256(config_raw).hexdigest(),
        "source_integrity": source_integrity,
        "pending_answer_sha256": source_integrity["answer_key_sha256"],
        "answer_pending_rows": len(tasks),
        "seed_governance": {
            "required": 2,
            "completed": 0,
            "release_status": "AWAITING_INDEPENDENT_LABEL_AUDITS",
            "audit_1_status": "PENDING",
            "audit_2_status": "PENDING",
            "resolution_status": "PENDING",
        },
        "label_audit_protocol": protocol_config,
        "canonical_outputs": {
            str(slot): {
                "predictions": audit.output_paths(tmp_path, slot)["audit"]
                .relative_to(tmp_path)
                .as_posix(),
                "sidecar": audit.output_paths(tmp_path, slot)["sidecar"]
                .relative_to(tmp_path)
                .as_posix(),
            }
            for slot in (1, 2)
        },
    }

    def fake_git(root, *arguments):
        if arguments[:2] == ("cat-file", "-e"):
            if state["absent"]:
                raise audit.AuditError("missing")
            return ""
        if arguments == ("rev-parse", "HEAD"):
            return current_head
        if arguments[:2] == ("merge-base", "--is-ancestor"):
            if state["nonancestor"]:
                raise audit.AuditError("not ancestor")
            return ""
        if arguments[0] == "rev-parse" and arguments[1].startswith(f"{head}:"):
            return state["blob_by_path"][arguments[1].split(":", 1)[1]]
        raise AssertionError(f"unexpected git call: {arguments}")

    def fake_git_bytes(root, *arguments):
        assert arguments[:2] == ("cat-file", "blob")
        return state["raw_by_blob"][arguments[2]]

    monkeypatch.setattr(audit, "_git", fake_git)
    monkeypatch.setattr(audit, "_git_bytes", fake_git_bytes)
    return checkpoint, raw_by_path, state


def _replace_historical_blob(
    checkpoint: dict,
    state: dict,
    relative_path: Path,
    raw: bytes,
    blob_id: str,
) -> None:
    path = relative_path.as_posix()
    state["blob_by_path"][path] = blob_id
    state["raw_by_blob"][blob_id] = raw
    checkpoint["tracked_files"][path] = {
        "head_blob": blob_id,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def _write_fake_attempt(
    command: list[str],
    event_path: Path,
    stderr_path: Path,
    session_id: str,
    response: bytes,
    return_code: int,
):
    response_text = response.decode("utf-8")
    event_path.write_bytes(
        (
            "\n".join(
                [
                    json.dumps(
                        {"type": "thread.started", "thread_id": session_id},
                        separators=(",", ":"),
                    ),
                    '{"type":"turn.started"}',
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": response_text},
                        },
                        separators=(",", ":"),
                    ),
                    '{"type":"turn.completed","usage":{"input_tokens":1,"output_tokens":1}}',
                    "",
                ]
            )
        ).encode("utf-8")
    )
    stderr_path.write_bytes(b"")
    last_path = Path(command[command.index("--output-last-message") + 1])
    last_path.write_bytes(response)
    return return_code, None


def _run_fake_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    _, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    valid_rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    session_counter = 0

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        nonlocal session_counter
        session_counter += 1
        return _write_fake_attempt(
            command,
            event_path,
            stderr_path,
            f"pair-session-{session_counter}",
            audit.canonical_json_bytes({"rows": valid_rows}),
            0,
        )

    monkeypatch.setattr(audit, "execute_attempt", fake_execute)
    audit.run_audit(1, root=tmp_path, codex_executable="codex")
    audit.run_audit(2, root=tmp_path, codex_executable="codex")
    return tasks


def _read_sidecar(tmp_path: Path, slot: int) -> dict:
    return json.loads(
        audit.output_paths(tmp_path, slot)["sidecar"].read_text(encoding="utf-8")
    )


def _write_sidecar(tmp_path: Path, slot: int, value: dict) -> None:
    audit.output_paths(tmp_path, slot)["sidecar"].write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_one_invalid_json_retry_is_byte_identical_and_seals_evidence(tmp_path, monkeypatch):
    catalog, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    valid_rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    calls: list[tuple[bytes, bytes]] = []

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        attempt = len(calls) + 1
        schema_path = Path(command[command.index("--output-schema") + 1])
        calls.append((prompt_raw, schema_path.read_bytes()))
        response = b"{" if attempt == 1 else audit.canonical_json_bytes({"rows": valid_rows})
        return _write_fake_attempt(
            command, event_path, stderr_path, f"session-{attempt}", response, 0
        )

    monkeypatch.setattr(audit, "execute_attempt", fake_execute)
    audit_path, sidecar_path = audit.run_audit(1, root=tmp_path, codex_executable="codex")
    assert len(calls) == 2
    assert calls[0] == calls[1]
    assert all(b"ANSWER_KEY_SENTINEL_MUST_NOT_LEAK" not in prompt for prompt, _ in calls)
    assert all(b"SEED_BANK_SENTINEL_MUST_NOT_LEAK" not in prompt for prompt, _ in calls)
    assert audit_path.read_bytes() == jsonl_bytes(valid_rows)
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert sidecar["batches"][0]["accepted_attempt"] == 2
    assert sidecar["execution"]["attempt_timeout_seconds"] == audit.ATTEMPT_TIMEOUT_SECONDS
    assert all(
        item["timeout_seconds"] == audit.ATTEMPT_TIMEOUT_SECONDS
        for item in sidecar["batches"][0]["attempts"]
    )
    assert [item["session_id"] for item in sidecar["batches"][0]["attempts"]] == [
        "session-1",
        "session-2",
    ]


def test_divergent_valid_transport_retry_invalidates_run(tmp_path, monkeypatch):
    catalog, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    base_rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    call_count = 0

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        nonlocal call_count
        call_count += 1
        rows = [dict(row) for row in base_rows]
        if call_count == 2:
            rows[0]["predicted_skill"] = catalog["names"][0]
            rows[0]["note"] = "A different valid label after retry."
        return _write_fake_attempt(
            command,
            event_path,
            stderr_path,
            f"session-{call_count}",
            audit.canonical_json_bytes({"rows": rows}),
            1 if call_count == 1 else 0,
        )

    monkeypatch.setattr(audit, "execute_attempt", fake_execute)
    with pytest.raises(audit.AuditError, match="divergent valid responses"):
        audit.run_audit(1, root=tmp_path, codex_executable="codex")
    assert call_count == 2
    assert not audit.output_paths(tmp_path, 1)["audit"].exists()


def test_event_message_mismatch_is_fatal_and_never_retried(tmp_path, monkeypatch):
    _, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    valid_rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    calls = 0

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        nonlocal calls
        calls += 1
        result = _write_fake_attempt(
            command,
            event_path,
            stderr_path,
            "session-1",
            b'{"rows":[]}',
            0,
        )
        Path(command[command.index("--output-last-message") + 1]).write_bytes(
            audit.canonical_json_bytes({"rows": valid_rows})
        )
        return result

    monkeypatch.setattr(audit, "execute_attempt", fake_execute)
    with pytest.raises(audit.AuditError, match="does not exactly match"):
        audit.run_audit(1, root=tmp_path, codex_executable="codex")
    assert calls == 1


def test_session_ids_must_be_disjoint_from_other_audit_sidecar(tmp_path):
    path = tmp_path / "other.run.json"
    path.write_text(
        json.dumps(
            {
                "batches": [
                    {"attempts": [{"session_id": "s1"}, {"session_id": "s2"}]}
                ]
            }
        ),
        encoding="utf-8",
    )
    assert audit.load_other_session_ids(path) == {"s1", "s2"}


def test_pair_verifier_binds_stable_predictions_and_all_evidence(tmp_path, monkeypatch):
    _, tasks = _prepare_fixture_root(tmp_path, monkeypatch)
    valid_rows = [
        {
            "task_id": task["task_id"],
            "predicted_skill": None,
            "confidence": "high",
            "note": "No registered capability fits.",
        }
        for task in tasks
    ]
    session_counter = 0

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        nonlocal session_counter
        session_counter += 1
        return _write_fake_attempt(
            command,
            event_path,
            stderr_path,
            f"globally-unique-{session_counter}",
            audit.canonical_json_bytes({"rows": valid_rows}),
            0,
        )

    monkeypatch.setattr(audit, "execute_attempt", fake_execute)
    audit.run_audit(1, root=tmp_path, codex_executable="codex")
    audit.run_audit(2, root=tmp_path, codex_executable="codex")
    result = audit.verify_pair(tmp_path, write_manifest=True)
    paths = audit.output_paths(tmp_path, 1)
    assert paths["audit"].name == "label_audit_1_predictions.jsonl"
    assert paths["sidecar"].name == "label_audit_1_run.json"
    assert paths["manifest"].name == "label_audit_evidence_manifest.json"
    assert result["global_session_ids"] == {
        "accepted_count": 2,
        "all_attempt_count": 2,
        "all_unique_and_cross_audit_disjoint": True,
    }
    roles = {item["role"] for item in result["artifacts"]}
    assert {
        "slot_1_predictions",
        "slot_2_predictions",
        "slot_1_sidecar",
        "slot_2_sidecar",
        "frozen_protocol",
        "audit_runner",
        "frozen_tasks",
        "frozen_registry_catalog",
        "slot_1_batch_01_rendered_prompt",
        "slot_2_batch_01_rendered_prompt",
    } <= roles
    assert result["isolated_workdirs"] == {"attempt_count": 2, "all_unique": True}
    assert result["answer_key_contents_included"] is False
    assert result["pending_answer_checkpoint_hash_included"] is True
    assert result["repository_checkpoint"]["config_sha256"] == "b" * 64


def test_pair_verifier_rejects_answer_augmented_prompts_even_when_sidecars_agree(
    tmp_path, monkeypatch
):
    _run_fake_pair(tmp_path, monkeypatch)
    for slot in (1, 2):
        sidecar = _read_sidecar(tmp_path, slot)
        prompt_path = tmp_path / sidecar["batches"][0]["prompt_path"]
        poisoned = prompt_path.read_bytes() + b"\nANSWER_KEY_LEAK=synthetic-skill-00\n"
        prompt_path.write_bytes(poisoned)
        forged_hash = hashlib.sha256(poisoned).hexdigest()
        sidecar["batches"][0]["prompt_sha256"] = forged_hash
        for attempt in sidecar["batches"][0]["attempts"]:
            attempt["prompt_sha256"] = forged_hash
        _write_sidecar(tmp_path, slot, sidecar)
    with pytest.raises(audit.AuditError, match="rendered-prompt hash drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_forged_equal_task_batch_hashes(tmp_path, monkeypatch):
    _run_fake_pair(tmp_path, monkeypatch)
    for slot in (1, 2):
        sidecar = _read_sidecar(tmp_path, slot)
        sidecar["batches"][0]["task_ids_sha256"] = "f" * 64
        _write_sidecar(tmp_path, slot, sidecar)
    with pytest.raises(audit.AuditError, match="task-ID hash drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_identically_altered_dynamic_schemas(tmp_path, monkeypatch):
    _run_fake_pair(tmp_path, monkeypatch)
    for slot in (1, 2):
        sidecar = _read_sidecar(tmp_path, slot)
        batch = sidecar["batches"][0]
        for attempt in batch["attempts"]:
            schema_path = tmp_path / attempt["schema_path"]
            altered = schema_path.read_bytes() + b"\n"
            schema_path.write_bytes(altered)
            altered_hash = hashlib.sha256(altered).hexdigest()
            attempt["schema_sha256"] = altered_hash
            batch["schema_sha256"] = altered_hash
        _write_sidecar(tmp_path, slot, sidecar)
    with pytest.raises(audit.AuditError, match="dynamic-schema hash drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_missing_rendered_prompt(tmp_path, monkeypatch):
    _run_fake_pair(tmp_path, monkeypatch)
    sidecar = _read_sidecar(tmp_path, 1)
    (tmp_path / sidecar["batches"][0]["prompt_path"]).unlink()
    with pytest.raises(audit.AuditError, match="missing slot_1_batch_01_rendered_prompt"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_any_exact_command_order_or_extra_flag_drift(
    tmp_path, monkeypatch
):
    _run_fake_pair(tmp_path, monkeypatch)
    sidecar = _read_sidecar(tmp_path, 1)
    command = sidecar["batches"][0]["attempts"][0]["command"]
    command[-1:-1] = ["--enable", "shell_tool"]
    _write_sidecar(tmp_path, 1, sidecar)
    with pytest.raises(audit.AuditError, match="exact command shape/binding drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_synchronized_timeout_drift(tmp_path, monkeypatch):
    _run_fake_pair(tmp_path, monkeypatch)
    for slot in (1, 2):
        sidecar = _read_sidecar(tmp_path, slot)
        sidecar["execution"]["attempt_timeout_seconds"] = 999
        for attempt in sidecar["batches"][0]["attempts"]:
            attempt["timeout_seconds"] = 999
        _write_sidecar(tmp_path, slot, sidecar)
    with pytest.raises(audit.AuditError, match="execution contract drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_pair_verifier_rejects_forged_equal_repository_checkpoints(tmp_path, monkeypatch):
    _run_fake_pair(tmp_path, monkeypatch)
    for slot in (1, 2):
        sidecar = _read_sidecar(tmp_path, slot)
        sidecar["repository_checkpoint"]["config_sha256"] = "d" * 64
        _write_sidecar(tmp_path, slot, sidecar)
    with pytest.raises(audit.AuditError, match="repository checkpoint drift"):
        audit.verify_pair(tmp_path, write_manifest=False)


def test_historical_checkpoint_rejects_absent_commit(tmp_path, monkeypatch):
    checkpoint, _, state = _historical_git_fixture(tmp_path, monkeypatch)
    state["absent"] = True
    with pytest.raises(audit.AuditError, match="historical checkpoint commit is absent"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_checkpoint_rejects_blob_drift(tmp_path, monkeypatch):
    checkpoint, _, state = _historical_git_fixture(tmp_path, monkeypatch)
    tasks_path = audit.TRACKED_CHECKPOINT_PATHS[0].as_posix()
    tasks_blob = state["blob_by_path"][tasks_path]
    state["raw_by_blob"][tasks_blob] += b"forged"
    with pytest.raises(audit.AuditError, match="historical tracked blob bytes drift"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_checkpoint_rejects_nonancestor_commit(tmp_path, monkeypatch):
    checkpoint, _, state = _historical_git_fixture(tmp_path, monkeypatch)
    state["nonancestor"] = True
    with pytest.raises(
        audit.AuditError,
        match="historical checkpoint is not an ancestor of current HEAD",
    ):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_checkpoint_rejects_forged_finalized_config(tmp_path, monkeypatch):
    checkpoint, _, state = _historical_git_fixture(tmp_path, monkeypatch)
    config_path = audit.CONFIG_RELATIVE_PATH.as_posix()
    old_blob = state["blob_by_path"][config_path]
    config = audit._strict_json_bytes(state["raw_by_blob"][old_blob], "test config")
    config["status"] = "FINALIZED"
    forged_raw = audit.canonical_json_bytes(config)
    _replace_historical_blob(
        checkpoint,
        state,
        audit.CONFIG_RELATIVE_PATH,
        forged_raw,
        "e" * 40,
    )
    checkpoint["config_sha256"] = hashlib.sha256(forged_raw).hexdigest()
    with pytest.raises(audit.AuditError, match="historical audit config was not pending"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_checkpoint_rejects_forged_completed_answer(tmp_path, monkeypatch):
    checkpoint, raw_by_path, state = _historical_git_fixture(tmp_path, monkeypatch)
    tasks = audit.read_jsonl_bytes(
        raw_by_path[audit.TRACKED_CHECKPOINT_PATHS[0].as_posix()], "test tasks"
    )
    forged_answer_raw = jsonl_bytes(
        [
            {
                "task_id": task["task_id"],
                "label_audit_status": "COMPLETE_TWO_INDEPENDENT_AUDITS",
            }
            for task in tasks
        ]
    )
    _replace_historical_blob(
        checkpoint,
        state,
        audit.ANSWER_RELATIVE_PATH,
        forged_answer_raw,
        "d" * 40,
    )
    answer_sha = hashlib.sha256(forged_answer_raw).hexdigest()
    checkpoint["source_integrity"]["answer_key_sha256"] = answer_sha
    checkpoint["pending_answer_sha256"] = answer_sha

    config_path = audit.CONFIG_RELATIVE_PATH.as_posix()
    config_blob = state["blob_by_path"][config_path]
    config = audit._strict_json_bytes(state["raw_by_blob"][config_blob], "test config")
    config["source_integrity"]["answer_key_sha256"] = answer_sha
    forged_config_raw = audit.canonical_json_bytes(config)
    _replace_historical_blob(
        checkpoint,
        state,
        audit.CONFIG_RELATIVE_PATH,
        forged_config_raw,
        "c" * 40,
    )
    checkpoint["config_sha256"] = hashlib.sha256(forged_config_raw).hexdigest()
    with pytest.raises(
        audit.AuditError,
        match="historical answer key was not uniformly pending 0/2",
    ):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_pair_verification_succeeds_after_current_tree_finalization(
    tmp_path, monkeypatch
):
    _run_fake_pair(tmp_path, monkeypatch)
    sealed = audit.verify_pair(tmp_path, write_manifest=True)
    historical_blobs = {
        path.as_posix(): (tmp_path / path).read_bytes()
        for path in audit.TRACKED_CHECKPOINT_PATHS[:2]
    }

    finalized_files = {
        audit.CONFIG_RELATIVE_PATH: audit.canonical_json_bytes({"status": "FINALIZED"}),
        audit.ANSWER_RELATIVE_PATH: b'{"label_audit_status":"COMPLETE"}\n',
        audit.SEED_RELATIVE_PATH: audit.canonical_json_bytes(
            {"label_governance": {"completed_independent_label_audits": 2}}
        ),
    }
    for relative_path, raw in finalized_files.items():
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def fail_current_checkpoint(_root):
        raise AssertionError("historical mode must not collect current/remote state")

    def authenticate(_root, checkpoint):
        assert checkpoint == sealed["repository_checkpoint"]
        return historical_blobs

    monkeypatch.setattr(audit, "collect_repository_checkpoint", fail_current_checkpoint)
    monkeypatch.setattr(
        audit, "authenticate_historical_repository_checkpoint", authenticate
    )
    result = audit.verify_pair(
        tmp_path,
        write_manifest=False,
        verification_mode="historical",
    )
    manifest = json.loads(
        audit.output_paths(tmp_path, 1)["manifest"].read_text(encoding="utf-8")
    )
    assert result == manifest == sealed
