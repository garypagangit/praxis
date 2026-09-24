from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from scripts import build_px062_gate2_2_v13_benchmark as builder
from scripts import finalize_px062_gate2_2_v13_labels as finalizer
from scripts import run_px062_gate2_2_v13_blind_audit as audit
from scripts.generate_px062_gate2_2_v1_3_construction import construction
from scripts.verify_px062_gate2_2_v13_label_audits import evaluate, verify


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_minimal_exact_evidence_inventory(
    root: Path,
    *,
    checkpoint: dict | None = None,
) -> tuple[dict, dict[int, Path]]:
    """Create one listed regular leaf in each canonical evidence directory."""

    artifacts: list[dict] = []
    leaves: dict[int, Path] = {}
    for slot in audit.AUDIT_SLOTS:
        directory = audit.output_paths(root, slot)["evidence"]
        directory.mkdir(parents=True, exist_ok=True)
        leaf = directory / "batch_01.prompt.txt"
        leaf.write_bytes(f"slot-{slot}\n".encode())
        leaves[slot] = leaf
        artifacts.append(
            {
                "role": f"slot_{slot}_batch_01_rendered_prompt",
                "path": leaf.relative_to(root).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        )
    return {
        "repository_checkpoint": checkpoint or {"head_commit": "a" * 40},
        "artifacts": artifacts,
    }, leaves


def _make_directory_link(link: Path, target: Path) -> str:
    """Create a directory symlink, or a Windows junction when unavailable."""

    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(target, link, target_is_directory=True)
        return "symlink"
    except (NotImplementedError, OSError) as symlink_error:
        if os.name == "nt":
            completed = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0:
                return "junction"
        pytest.skip(f"directory link creation is unsupported: {symlink_error}")


def _remove_directory_link(link: Path, kind: str) -> None:
    if not os.path.lexists(link):
        return
    if kind == "junction":
        os.rmdir(link)
    else:
        link.unlink()


def jsonl_bytes(rows: list[dict]) -> bytes:
    return b"".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        + b"\n"
        for row in rows
    )


def _copy_v12_pair_manifest(root: Path) -> Path:
    target = root / audit.V12_PAIR_MANIFEST_RELATIVE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(audit.ROOT / audit.V12_PAIR_MANIFEST_RELATIVE_PATH, target)
    return target


def _copy_checkpoint_tree(root: Path) -> None:
    for relative in audit.TRACKED_CHECKPOINT_PATHS:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(audit.ROOT / relative, target)


def _fake_current_git(root: Path, *args: str) -> str:
    branch = "agent/test-v13-hardening"
    head = "a" * 40
    if args == ("status", "--porcelain=v1", "--untracked-files=no"):
        return ""
    if args == ("rev-parse", "HEAD"):
        return head
    if args == ("symbolic-ref", "--quiet", "--short", "HEAD"):
        return branch
    if args == (
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    ):
        return f"origin/{branch}"
    if args == ("rev-parse", f"origin/{branch}"):
        return head
    if args == ("ls-remote", "--heads", "origin", f"refs/heads/{branch}"):
        return f"{head}\trefs/heads/{branch}"
    if len(args) == 4 and args[:3] == ("ls-files", "--error-unmatch", "--"):
        return args[3]
    if len(args) == 2 and args[0] == "rev-parse" and args[1].startswith("HEAD:"):
        return "b" + hashlib.sha256(args[1].encode()).hexdigest()[:39]
    if len(args) == 3 and args[:2] == ("hash-object", "--"):
        return "b" + hashlib.sha256(f"HEAD:{args[2]}".encode()).hexdigest()[:39]
    raise AssertionError(f"unexpected fake git invocation: {args}")


def _bind_fake_historical_git(
    monkeypatch: pytest.MonkeyPatch,
    checkpoint: dict,
    blobs: dict[str, bytes],
) -> None:
    blob_by_id = {
        record["head_blob"]: blobs[path]
        for path, record in checkpoint["tracked_files"].items()
    }

    def fake_git(root: Path, *args: str) -> str:
        if args == ("cat-file", "-e", f"{checkpoint['head_commit']}^{{commit}}"):
            return ""
        if args == ("rev-parse", "HEAD"):
            return checkpoint["head_commit"]
        if args == (
            "merge-base", "--is-ancestor", checkpoint["head_commit"],
            checkpoint["head_commit"],
        ):
            return ""
        prefix = f"{checkpoint['head_commit']}:"
        if len(args) == 2 and args[0] == "rev-parse" and args[1].startswith(prefix):
            path = args[1][len(prefix) :]
            return checkpoint["tracked_files"][path]["head_blob"]
        raise AssertionError(f"unexpected fake historical git invocation: {args}")

    def fake_bytes(root: Path, *args: str) -> bytes:
        assert args[:2] == ("cat-file", "blob")
        return blob_by_id[args[2]]

    monkeypatch.setattr(audit.core, "_git", fake_git)
    monkeypatch.setattr(audit.core, "_git_bytes", fake_bytes)


def _write_fake_codex_attempt(
    command: list[str],
    event_path: Path,
    stderr_path: Path,
    session_id: str,
    response: bytes,
) -> tuple[int, None]:
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
    return 0, None


def _write_verifier_fixture(
    directory: Path,
) -> tuple[Path, Path, Path, list[Path], list[dict], list[list[dict]]]:
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
        [
            {
                "task_id": answer["task_id"],
                "predicted_skill": answer["expected_skill"],
                "confidence": "high",
                "note": "The frozen catalog has exactly this fit or no applicable skill.",
            }
            for answer in answers
        ]
        for _ in range(4)
    ]
    tasks_path = directory / "tasks.jsonl"
    answers_path = directory / "answer_key.jsonl"
    catalog_path = directory / "registry_catalog.json"
    audit_paths = [directory / f"audit_{slot}.jsonl" for slot in (1, 2, 3, 4)]
    tasks_path.write_bytes(jsonl_bytes(tasks))
    answers_path.write_bytes(jsonl_bytes(answers))
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8", newline="\n")
    for path, rows in zip(audit_paths, predictions, strict=True):
        path.write_bytes(jsonl_bytes(rows))
    return tasks_path, answers_path, catalog_path, audit_paths, answers, predictions


def test_v13_frozen_hashes_projection_and_full_batches() -> None:
    assert digest(audit.TASKS_PATH) == audit.EXPECTED_TASKS_SHA256
    assert digest(audit.CATALOG_PATH) == audit.EXPECTED_CATALOG_SHA256
    tasks = audit.read_jsonl_bytes(audit.TASKS_PATH.read_bytes(), "v1.3 tasks")
    _, names, semantic_registry = audit.load_catalog(audit.CATALOG_PATH.read_bytes())
    audit.validate_tasks(tasks, names)
    batches = audit.make_batches(tasks)
    assert len(batches) == 43
    assert {len(batch) for batch in batches} == {24}
    projected = [
        row for batch in batches for row in audit.project_tasks_for_auditor(batch)
    ]
    assert len(projected) == 1032
    assert all(list(row) == ["task_id", "prompt"] for row in projected)
    prompt = audit.build_prompt(1, batches[0], semantic_registry).decode("utf-8")
    assert "option_map" not in prompt
    assert audit.SLOT_MODELS == {
        1: "gpt-5.6-sol",
        2: "gpt-5.6-terra",
        3: "gpt-5.6-sol",
        4: "gpt-5.6-terra",
    }


def test_v13_checkpoint_tracks_four_pass_sources() -> None:
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
        audit.BUILDER_RELATIVE_PATH.as_posix(),
        audit.BASE_BUILDER_RELATIVE_PATH.as_posix(),
        audit.V11_BUILDER_RELATIVE_PATH.as_posix(),
        audit.V11_RUNNER_RELATIVE_PATH.as_posix(),
        audit.VERIFIER_RELATIVE_PATH.as_posix(),
        audit.V11_VERIFIER_RELATIVE_PATH.as_posix(),
        audit.FINALIZER_RELATIVE_PATH.as_posix(),
        audit.V11_FINALIZER_RELATIVE_PATH.as_posix(),
        audit.V12_PAIR_MANIFEST_RELATIVE_PATH.as_posix(),
    } <= tracked
    assert builder.CHECKPOINT_TRACKED_PATHS == tuple(
        path.as_posix() for path in audit.TRACKED_CHECKPOINT_PATHS
    )
    assert builder.CANONICAL_AUDIT_MODELS == tuple(
        audit.SLOT_MODELS[slot] for slot in (1, 2, 3, 4)
    )


@pytest.mark.skipif(os.name != "nt", reason="Windows drive-relative path syntax")
def test_safe_path_rejects_windows_drive_relative_spelling(tmp_path: Path) -> None:
    with pytest.raises(audit.AuditError, match="canonical root-relative POSIX"):
        audit._safe_root_relative_path(tmp_path, "C:hostile.txt", "hostile evidence")


@pytest.mark.parametrize(
    "relative",
    audit.GOVERNANCE_EXECUTABLE_PATHS,
)
def test_current_checkpoint_rejects_governance_code_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: Path
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    checkpoint = audit.collect_repository_checkpoint(tmp_path)
    assert checkpoint["tracked_tree_clean"] is True
    target = tmp_path / relative
    target.write_bytes(target.read_bytes() + b"\n# hostile post-freeze mutation\n")
    with pytest.raises(audit.AuditError, match="label_audit_protocol anchors drift"):
        audit.collect_repository_checkpoint(tmp_path)


def test_current_checkpoint_rejects_hard_linked_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_checkpoint_tree(tmp_path)
    target = tmp_path / audit.RUNNER_RELATIVE_PATH
    alias = tmp_path / "hostile-runner-hardlink-alias.py"
    try:
        os.link(target, alias)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"hard-link creation is unsupported: {exc}")
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    with pytest.raises(audit.AuditError, match="hard-link count"):
        audit.collect_repository_checkpoint(tmp_path)


@pytest.mark.parametrize(
    "relative",
    audit.GOVERNANCE_EXECUTABLE_PATHS,
)
def test_historical_checkpoint_uses_recorded_governance_blobs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: Path
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    checkpoint = audit.collect_repository_checkpoint(tmp_path)
    blobs = {
        path.as_posix(): (tmp_path / path).read_bytes()
        for path in audit.TRACKED_CHECKPOINT_PATHS
    }
    logical = relative.as_posix()
    blobs[logical] += b"\n# hostile historical blob mutation\n"
    checkpoint = deepcopy(checkpoint)
    checkpoint["tracked_files"][logical]["bytes"] = len(blobs[logical])
    checkpoint["tracked_files"][logical]["sha256"] = audit.sha256_bytes(blobs[logical])
    _bind_fake_historical_git(monkeypatch, checkpoint, blobs)
    with pytest.raises(audit.AuditError, match="historical config audit-protocol anchors drift"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_historical_checkpoint_rejects_tampered_recorded_protocol_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    checkpoint = audit.collect_repository_checkpoint(tmp_path)
    blobs = {
        path.as_posix(): (tmp_path / path).read_bytes()
        for path in audit.TRACKED_CHECKPOINT_PATHS
    }
    hostile = deepcopy(checkpoint)
    hostile["label_audit_protocol"]["governance_code"]["builder"]["sha256"] = "0" * 64
    _bind_fake_historical_git(monkeypatch, hostile, blobs)
    with pytest.raises(audit.AuditError, match="checkpoint label_audit_protocol drift"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, hostile)


@pytest.mark.parametrize("relative", audit.GOVERNANCE_EXECUTABLE_PATHS)
def test_historical_checkpoint_rejects_mutated_current_executable_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: Path
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    checkpoint = audit.collect_repository_checkpoint(tmp_path)
    blobs = {
        path.as_posix(): (tmp_path / path).read_bytes()
        for path in audit.TRACKED_CHECKPOINT_PATHS
    }
    _bind_fake_historical_git(monkeypatch, checkpoint, blobs)
    target = tmp_path / relative
    target.write_bytes(target.read_bytes() + b"\n# hostile current-code mutation\n")
    with pytest.raises(audit.AuditError, match="current governance control differs"):
        audit.authenticate_historical_repository_checkpoint(tmp_path, checkpoint)


def test_sealed_v12_pair_manifest_authenticates_exact_86_id_blacklist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = (audit.ROOT / audit.V12_PAIR_MANIFEST_RELATIVE_PATH).read_bytes()
    parsed = audit._validate_v12_pair_manifest_raw(raw)
    assert len(parsed["session_ids"]) == 86
    assert parsed["evidence"] == {
        "path": audit.V12_PAIR_MANIFEST_RELATIVE_PATH.as_posix(),
        "sha256": audit.EXPECTED_V12_PAIR_MANIFEST_SHA256,
        "accepted_session_count": 86,
        "accepted_session_ids_sha256": (
            audit.EXPECTED_V12_ACCEPTED_SESSION_IDS_SHA256
        ),
    }
    with pytest.raises(audit.AuditError, match="hash drift"):
        audit._validate_v12_pair_manifest_raw(raw + b" ")

    hostile = json.loads(raw)
    hostile["audits"][1]["accepted_session_ids"][0] = hostile["audits"][0][
        "accepted_session_ids"
    ][0]
    hostile_raw = (
        json.dumps(hostile, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    monkeypatch.setattr(
        audit, "EXPECTED_V12_PAIR_MANIFEST_SHA256", audit.sha256_bytes(hostile_raw)
    )
    with pytest.raises(audit.AuditError, match="global session provenance drift"):
        audit._validate_v12_pair_manifest_raw(hostile_raw)


def test_complete_thread_id_extractor_recovers_multi_id_partial_log() -> None:
    raw = (
        b'{"type":"thread.started","thread_id":"fresh-a"}\r\n'
        b"\xff\xfe malformed bytes\n"
        b'{"type":"thread.started","thread_id":"sealed-b"}\n'
        b'{"type":"thread.started","thread_id":"fresh-a"}\n'
    )
    assert audit.extract_exposed_thread_ids(raw) == {"fresh-a", "sealed-b"}
    assert audit.extract_exposed_thread_id(raw) is None


@pytest.mark.parametrize("slot", audit.AUDIT_SLOTS)
def test_every_v13_slot_blacklists_all_v12_sessions(
    tmp_path: Path, slot: int
) -> None:
    _copy_v12_pair_manifest(tmp_path)
    expected = audit.v12_audit_blacklist(tmp_path)["session_ids"]
    assert len(expected) == 86
    assert expected <= audit.load_prior_session_ids(tmp_path, slot)


def test_existing_v13_sidecar_cannot_reuse_blacklisted_v12_session(
    tmp_path: Path,
) -> None:
    _copy_v12_pair_manifest(tmp_path)
    reused = sorted(audit.v12_audit_blacklist(tmp_path)["session_ids"])[0]
    sidecar = audit.output_paths(tmp_path, 2)["sidecar"]
    sidecar.parent.mkdir(parents=True, exist_ok=True)
    sidecar.write_text(
        json.dumps({"batches": [{"attempts": [{"session_id": reused}]}]}),
        encoding="utf-8",
    )
    with pytest.raises(audit.AuditError, match="blacklisted or prior"):
        audit.load_prior_session_ids(tmp_path, 1)


def test_runtime_rejects_multi_id_failed_attempt_containing_v12_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    monkeypatch.setitem(
        audit._RUN_AUDIT_V13.__globals__,
        "_codex_version",
        lambda executable: audit.EXPECTED_CODEX_VERSION,
    )
    sealed = sorted(audit.v12_audit_blacklist(tmp_path)["session_ids"])[0]
    calls = 0

    def fake_execute(*, command, prompt_raw, event_path, stderr_path, timeout_seconds):
        nonlocal calls
        calls += 1
        event_path.write_bytes(
            (
                '{"type":"thread.started","thread_id":"fresh-multi"}\n'
                + json.dumps(
                    {"type": "thread.started", "thread_id": sealed},
                    separators=(",", ":"),
                )
                + "\n"
            ).encode("utf-8")
        )
        stderr_path.write_bytes(b"")
        return 1, None

    monkeypatch.setitem(
        audit._RUN_AUDIT_V13.__globals__, "execute_attempt", fake_execute
    )
    with pytest.raises(audit.AuditError, match="reused or blacklisted"):
        audit.run_audit(1, root=tmp_path, codex_executable="codex")
    paths = audit.output_paths(tmp_path, 1)
    assert calls == 1
    assert not paths["audit"].exists()
    assert not paths["sidecar"].exists()
    assert not paths["manifest"].exists()


def test_slot_order_gap_fails_before_any_new_evidence_write(tmp_path: Path) -> None:
    _copy_v12_pair_manifest(tmp_path)
    with pytest.raises(audit.AuditError, match="predecessor slot 1"):
        audit.run_audit(2, root=tmp_path, codex_executable="must-not-run")
    paths = audit.output_paths(tmp_path, 2)
    assert not paths["audit"].exists()
    assert not paths["sidecar"].exists()
    assert not paths["evidence"].exists()
    assert not paths["manifest"].exists()


def test_slot_order_rejects_future_partial_and_manifest_states(
    tmp_path: Path,
) -> None:
    _copy_v12_pair_manifest(tmp_path)
    future = audit.output_paths(tmp_path, 3)["sidecar"]
    future.parent.mkdir(parents=True, exist_ok=True)
    future.write_text("{}", encoding="utf-8")
    with pytest.raises(audit.AuditError, match="successor slot 3"):
        audit.run_audit(1, root=tmp_path, codex_executable="must-not-run")
    assert not audit.output_paths(tmp_path, 1)["evidence"].exists()
    future.unlink()

    partial = audit.output_paths(tmp_path, 1)["audit"]
    partial.write_bytes(b"partial")
    with pytest.raises(audit.AuditError, match="predecessor slot 1"):
        audit.validate_slot_order(tmp_path, 2)
    partial.unlink()

    manifest = audit.output_paths(tmp_path, 1)["manifest"]
    manifest.write_text("{}", encoding="utf-8")
    with pytest.raises(audit.AuditError, match="consensus manifest already exists"):
        audit.validate_slot_order(tmp_path, 1)


def test_slot_order_accepts_only_contiguous_completed_predecessors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[int, dict | None]] = []
    for slot in (1, 2, 3):
        paths = audit.output_paths(tmp_path, slot)
        paths["audit"].parent.mkdir(parents=True, exist_ok=True)
        paths["audit"].touch()
        paths["sidecar"].touch()
        paths["evidence"].mkdir(parents=True)

    def complete(
        root: Path, slot: int, *, expected_checkpoint: dict | None = None
    ) -> set[str]:
        seen.append((slot, expected_checkpoint))
        return {f"fresh-slot-{slot}"}

    checkpoint = {"head_commit": "a" * 40}
    monkeypatch.setattr(audit, "validate_completed_predecessor_slot", complete)
    audit.validate_slot_order(tmp_path, 4, expected_checkpoint=checkpoint)
    assert seen == [(1, checkpoint), (2, checkpoint), (3, checkpoint)]


def test_successor_reconstructs_real_predecessor_and_rejects_forged_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    monkeypatch.setitem(
        audit._RUN_AUDIT_V13.__globals__,
        "_codex_version",
        lambda executable: audit.EXPECTED_CODEX_VERSION,
    )
    tasks = audit.read_jsonl_bytes(
        (tmp_path / audit.TRACKED_CHECKPOINT_PATHS[0]).read_bytes(), "v1.3 tasks"
    )
    call_count = 0

    def fake_execute(
        *, command, prompt_raw, event_path, stderr_path, timeout_seconds
    ):
        nonlocal call_count
        call_count += 1
        batch = tasks[(call_count - 1) * audit.BATCH_SIZE : call_count * audit.BATCH_SIZE]
        response = audit.canonical_json_bytes(
            {
                "rows": [
                    {
                        "task_id": row["task_id"],
                        "predicted_skill": None,
                        "confidence": "high",
                        "note": "No frozen registry entry is applicable.",
                    }
                    for row in batch
                ]
            }
        )
        return _write_fake_codex_attempt(
            command,
            event_path,
            stderr_path,
            f"fresh-v13-slot1-{call_count:02d}",
            response,
        )

    monkeypatch.setitem(
        audit._RUN_AUDIT_V13.__globals__, "execute_attempt", fake_execute
    )
    audit.run_audit(1, root=tmp_path, codex_executable="codex")
    sidecar_path = audit.output_paths(tmp_path, 1)["sidecar"]
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    checkpoint = sidecar["repository_checkpoint"]
    assert len(
        audit.validate_completed_predecessor_slot(
            tmp_path, 1, expected_checkpoint=checkpoint
        )
    ) == 43

    pristine_sidecar = deepcopy(sidecar)
    first_attempt = sidecar["batches"][0]["attempts"][0]
    event_path = tmp_path / first_attempt["event_log_path"]
    pristine_event = event_path.read_bytes()
    reused = sorted(audit.v12_audit_blacklist(tmp_path)["session_ids"])[0]
    event_path.write_bytes(
        pristine_event.replace(first_attempt["session_id"].encode(), reused.encode())
    )
    first_attempt["session_id"] = reused
    first_attempt["exposed_session_ids"] = [reused]
    first_attempt["event_log_sha256"] = digest(event_path)
    first_attempt["event_summary"]["session_id"] = reused
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(audit.AuditError, match="sealed v1.2 session ID"):
        audit.run_audit(2, root=tmp_path, codex_executable="must-not-run")
    assert not audit.output_paths(tmp_path, 2)["evidence"].exists()
    event_path.write_bytes(pristine_event)
    sidecar = pristine_sidecar
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    prompt_path = tmp_path / sidecar["batches"][0]["prompt_path"]
    prompt_path.write_bytes(prompt_path.read_bytes() + b"HOSTILE SELF-CONSISTENT EDIT\n")
    forged_hash = digest(prompt_path)
    sidecar["batches"][0]["prompt_sha256"] = forged_hash
    for attempt in sidecar["batches"][0]["attempts"]:
        attempt["prompt_sha256"] = forged_hash
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(audit.AuditError, match="batch 1 reconstruction drift"):
        audit.run_audit(2, root=tmp_path, codex_executable="must-not-run")
    successor = audit.output_paths(tmp_path, 2)
    assert not successor["audit"].exists()
    assert not successor["sidecar"].exists()
    assert not successor["evidence"].exists()


def test_balanced_consensus_accepts_one_dissent_and_preserves_it(tmp_path: Path) -> None:
    tasks, answers, catalog, audits, answer_rows, predictions = _write_verifier_fixture(
        tmp_path
    )
    predictions[0][0]["predicted_skill"] = "skill-00"
    audits[0].write_bytes(jsonl_bytes(predictions[0]))
    result = verify(tasks, answers, audits, catalog)
    assert result["all_labels_balanced_consensus_accepted"] is True
    assert result["accepted_rows"] == 1032
    assert result["single_dissent_rows"] == 1
    assert result["single_dissent_task_ids"] == [answer_rows[0]["task_id"]]
    assert result["unanimous_key_rows"] == 1031


def test_balanced_consensus_rejects_two_dissents_or_missing_slot(tmp_path: Path) -> None:
    tasks, answers, catalog, audits, _, predictions = _write_verifier_fixture(tmp_path)
    predictions[0][0]["predicted_skill"] = "skill-00"
    predictions[1][0]["predicted_skill"] = "skill-00"
    audits[0].write_bytes(jsonl_bytes(predictions[0]))
    audits[1].write_bytes(jsonl_bytes(predictions[1]))
    result = evaluate(tasks, answers, audits, catalog)
    assert result["all_labels_balanced_consensus_accepted"] is False
    assert result["rejected_rows"] == 1
    with pytest.raises(ValueError, match="balanced 3-of-4"):
        verify(tasks, answers, audits, catalog)
    with pytest.raises(ValueError, match="exactly four distinct"):
        verify(tasks, answers, audits[:3], catalog)


def test_finalizer_builds_four_slot_provisional_with_single_dissent(tmp_path: Path) -> None:
    tasks, answers, catalog, audits, _, predictions = _write_verifier_fixture(tmp_path)
    predictions[3][5]["predicted_skill"] = None
    audits[3].write_bytes(jsonl_bytes(predictions[3]))
    verification = verify(tasks, answers, audits, catalog)
    consensus = {
        "path": "v1.3/label_audit_evidence_manifest.json",
        "sha256": "a" * 64,
        "audits": [
            {
                "slot": slot,
                "model": audit.SLOT_MODELS[slot],
                "sidecar_sha256": f"{slot}" * 64,
                "accepted_session_ids": [
                    f"fresh-v13-s{slot}-{index}" for index in range(43)
                ],
            }
            for slot in (1, 2, 3, 4)
        ],
    }
    provisional = finalizer.build_provisional_resolution(
        verification=verification,
        candidate_tasks_path="v1.3/tasks.jsonl",
        candidate_answer_path="v1.3/answer_key.jsonl",
        audit_paths=list(builder.CANONICAL_AUDIT_PATHS),
        canonical_pair=consensus,
    )
    assert len(provisional["audits"]) == 4
    assert provisional["all_labels_balanced_consensus_accepted"] is True
    assert provisional["single_dissent_task_ids"] == ["task-0005"]
    assert provisional["rejected_task_ids"] == []


def test_consensus_manifest_write_reauthenticates_every_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    leaf = tmp_path / "raw" / "batch.events.jsonl"
    leaf.parent.mkdir(parents=True)
    leaf.write_bytes(b"sealed-before-verification\n")
    result = {
        "repository_checkpoint": {"head_commit": "a" * 40},
        "artifacts": [
            {
                "role": "slot_1_batch_01_attempt_1_events",
                "path": leaf.relative_to(tmp_path).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        ],
    }

    def verified_then_mutated(*args, **kwargs):
        leaf.write_bytes(b"hostile-mutation-after-verification\n")
        return result

    monkeypatch.setattr(audit, "_VERIFY_CONSENSUS_V13", verified_then_mutated)
    monkeypatch.setattr(
        audit, "collect_repository_checkpoint", lambda root: result["repository_checkpoint"]
    )
    with pytest.raises(audit.AuditError, match="changed before seal/write"):
        audit.verify_consensus(tmp_path, write_manifest=True)
    assert not audit.output_paths(tmp_path, 1)["manifest"].exists()


@pytest.mark.parametrize("verification_mode", ("current", "historical"))
@pytest.mark.parametrize("extra_kind", ("file", "directory"))
def test_consensus_rejects_unlisted_evidence_leaf_before_manifest_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    verification_mode: str,
    extra_kind: str,
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    artifacts: list[dict] = []
    for slot in audit.AUDIT_SLOTS:
        directory = audit.output_paths(tmp_path, slot)["evidence"]
        directory.mkdir(parents=True)
        leaf = directory / "batch_01.prompt.txt"
        leaf.write_bytes(f"slot-{slot}\n".encode())
        artifacts.append(
            {
                "role": f"slot_{slot}_batch_01_rendered_prompt",
                "path": leaf.relative_to(tmp_path).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        )
    extra = audit.output_paths(tmp_path, 3)["evidence"] / "unlisted"
    if extra_kind == "file":
        extra.write_bytes(b"hostile unlisted evidence\n")
    else:
        extra.mkdir()
    result = {"repository_checkpoint": checkpoint, "artifacts": artifacts}
    monkeypatch.setattr(audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result)
    monkeypatch.setattr(audit, "collect_repository_checkpoint", lambda root: checkpoint)
    if verification_mode == "historical":
        manifest_path = audit.output_paths(tmp_path, 1)["manifest"]
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"repository_checkpoint": checkpoint}), encoding="utf-8"
        )
        monkeypatch.setattr(
            audit, "authenticate_historical_repository_checkpoint", lambda *args: {}
        )
    with pytest.raises(
        audit.AuditError,
        match="evidence inventory contains an unlisted directory|evidence directory inventory drift",
    ):
        audit.verify_consensus(
            tmp_path,
            write_manifest=verification_mode == "current",
            verification_mode=verification_mode,
        )
    if verification_mode == "current":
        assert not audit.output_paths(tmp_path, 1)["manifest"].exists()


def test_consensus_rechecks_exact_inventory_after_checkpoint_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    artifacts: list[dict] = []
    for slot in audit.AUDIT_SLOTS:
        directory = audit.output_paths(tmp_path, slot)["evidence"]
        directory.mkdir(parents=True)
        leaf = directory / "batch_01.prompt.txt"
        leaf.write_bytes(f"slot-{slot}\n".encode())
        artifacts.append(
            {
                "role": f"slot_{slot}_batch_01_rendered_prompt",
                "path": leaf.relative_to(tmp_path).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        )
    result = {"repository_checkpoint": checkpoint, "artifacts": artifacts}
    monkeypatch.setattr(audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result)

    def checkpoint_then_mutate(root: Path) -> dict:
        extra = audit.output_paths(root, 2)["evidence"] / "late-unlisted.events.jsonl"
        extra.write_bytes(b"hostile late evidence\n")
        return checkpoint

    monkeypatch.setattr(audit, "collect_repository_checkpoint", checkpoint_then_mutate)
    with pytest.raises(audit.AuditError, match="evidence directory inventory drift"):
        audit.verify_consensus(tmp_path, write_manifest=True)
    assert not audit.output_paths(tmp_path, 1)["manifest"].exists()


def test_consensus_rejects_hard_link_alias_before_manifest_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    result, leaves = _write_minimal_exact_evidence_inventory(
        tmp_path, checkpoint=checkpoint
    )
    alias = leaves[1].with_name("batch_01.alias.txt")
    try:
        os.link(leaves[1], alias)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"hard-link creation is unsupported: {exc}")
    result["artifacts"].append(
        {
            "role": "slot_1_batch_01_distinct_alias_role",
            "path": alias.relative_to(tmp_path).as_posix(),
            "bytes": alias.stat().st_size,
            "sha256": digest(alias),
        }
    )
    monkeypatch.setattr(audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result)
    monkeypatch.setattr(audit, "collect_repository_checkpoint", lambda root: checkpoint)
    with pytest.raises(
        audit.AuditError, match="hard-link count|stable-file alias"
    ):
        audit.verify_consensus(tmp_path, write_manifest=True)
    assert not audit.output_paths(tmp_path, 1)["manifest"].exists()


def test_consensus_rejects_final_leaf_symlink_before_manifest_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    result, leaves = _write_minimal_exact_evidence_inventory(
        tmp_path, checkpoint=checkpoint
    )
    leaf = leaves[1]
    target = tmp_path / "real-slot-1-prompt.txt"
    target.write_bytes(leaf.read_bytes())
    leaf.unlink()
    try:
        os.symlink(target, leaf)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"file symlink creation is unsupported: {exc}")
    try:
        monkeypatch.setattr(
            audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result
        )
        monkeypatch.setattr(
            audit, "collect_repository_checkpoint", lambda root: checkpoint
        )
        with pytest.raises(audit.AuditError, match="symlink-like component"):
            audit.verify_consensus(tmp_path, write_manifest=True)
        assert not audit.output_paths(tmp_path, 1)["manifest"].exists()
    finally:
        if leaf.is_symlink():
            leaf.unlink()


def test_consensus_rejects_linked_canonical_evidence_directory_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    evidence = audit.output_paths(tmp_path, 1)["evidence"]
    target = evidence.parent / "real-slot-1-evidence"
    target.mkdir(parents=True)
    link_kind = _make_directory_link(evidence, target)
    try:
        result, _ = _write_minimal_exact_evidence_inventory(
            tmp_path, checkpoint=checkpoint
        )
        monkeypatch.setattr(
            audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result
        )
        monkeypatch.setattr(
            audit, "collect_repository_checkpoint", lambda root: checkpoint
        )
        with pytest.raises(audit.AuditError, match="symlink-like component"):
            audit.verify_consensus(tmp_path, write_manifest=True)
        assert not audit.output_paths(tmp_path, 1)["manifest"].exists()
    finally:
        _remove_directory_link(evidence, link_kind)


def test_consensus_rejects_linked_intermediate_evidence_parent_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    evidence_parent = audit.output_paths(tmp_path, 1)["evidence"].parent
    target = evidence_parent.parent / "real-label-audits"
    target.mkdir(parents=True)
    link_kind = _make_directory_link(evidence_parent, target)
    try:
        result, _ = _write_minimal_exact_evidence_inventory(
            tmp_path, checkpoint=checkpoint
        )
        monkeypatch.setattr(
            audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result
        )
        monkeypatch.setattr(
            audit, "collect_repository_checkpoint", lambda root: checkpoint
        )
        with pytest.raises(audit.AuditError, match="symlink-like component"):
            audit.verify_consensus(tmp_path, write_manifest=True)
        assert not audit.output_paths(tmp_path, 1)["manifest"].exists()
    finally:
        _remove_directory_link(evidence_parent, link_kind)


def test_consensus_rechecks_checkpoint_after_final_inventory_before_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _copy_checkpoint_tree(tmp_path)
    monkeypatch.setattr(audit.core, "_git", _fake_current_git)
    checkpoint = audit.collect_repository_checkpoint(tmp_path)
    result, _ = _write_minimal_exact_evidence_inventory(
        tmp_path, checkpoint=checkpoint
    )
    monkeypatch.setattr(audit, "_VERIFY_CONSENSUS_V13", lambda *args, **kwargs: result)
    real_inventory_check = audit.reauthenticate_manifest_artifact_inventory
    inventory_calls = 0

    def inventory_then_mutate_control(root: Path, manifest: dict) -> None:
        nonlocal inventory_calls
        real_inventory_check(root, manifest)
        inventory_calls += 1
        if inventory_calls == 2:
            runner = root / audit.RUNNER_RELATIVE_PATH
            runner.write_bytes(runner.read_bytes() + b"\n# hostile late mutation\n")

    monkeypatch.setattr(
        audit,
        "reauthenticate_manifest_artifact_inventory",
        inventory_then_mutate_control,
    )
    with pytest.raises(
        audit.AuditError,
        match="label_audit_protocol anchors drift|changed after final inventory check",
    ):
        audit.verify_consensus(tmp_path, write_manifest=True)
    assert inventory_calls == 2
    assert not audit.output_paths(tmp_path, 1)["manifest"].exists()


def test_finalizer_reauthenticates_complete_inventory_before_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    candidate_files = {
        name: f"pending-{name}\n".encode("utf-8") for name in finalizer.FROZEN_NAMES
    }
    for name, raw in candidate_files.items():
        (candidate_dir / name).write_bytes(raw)
    seed = tmp_path / "seed.json"
    seed.write_bytes(b"pending-seed\n")
    leaf = tmp_path / "raw" / "batch.stderr.txt"
    leaf.parent.mkdir()
    leaf.write_bytes(b"sealed stderr\n")
    manifest = {
        "artifacts": [
            {
                "role": "slot_4_batch_43_attempt_1_stderr",
                "path": leaf.relative_to(tmp_path).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        ]
    }
    manifest_path = tmp_path / builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plan = {
        "root": tmp_path,
        "seed_bank_path": seed,
        "candidate_dir": candidate_dir,
        "provisional_resolution_path": tmp_path / "provisional.json",
        "final_resolution_path": tmp_path / "final.json",
        "candidate_seed_sha256": digest(seed),
        "candidate_files": candidate_files,
        "sealed_evidence_hashes": {
            builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH: digest(manifest_path)
        },
    }
    monkeypatch.setattr(
        builder,
        "_historical_consensus_verifier",
        lambda root, write_manifest=False: manifest,
    )
    leaf.write_bytes(b"hostile leaf mutation after plan\n")
    with pytest.raises(ValueError, match="raw consensus-manifest artifact changed"):
        finalizer.apply_finalization(plan)
    assert seed.read_bytes() == b"pending-seed\n"
    assert not plan["provisional_resolution_path"].exists()
    assert not plan["final_resolution_path"].exists()
    for name, raw in candidate_files.items():
        assert (candidate_dir / name).read_bytes() == raw


def test_finalizer_rejects_hard_link_alias_before_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    candidate_files = {
        name: f"pending-{name}\n".encode("utf-8") for name in finalizer.FROZEN_NAMES
    }
    for name, raw in candidate_files.items():
        (candidate_dir / name).write_bytes(raw)
    seed = tmp_path / "seed.json"
    seed.write_bytes(b"pending-seed\n")
    manifest, leaves = _write_minimal_exact_evidence_inventory(tmp_path)
    alias = leaves[2].with_name("batch_01.distinct-role-alias.txt")
    try:
        os.link(leaves[2], alias)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"hard-link creation is unsupported: {exc}")
    manifest["artifacts"].append(
        {
            "role": "slot_2_batch_01_distinct_alias_role",
            "path": alias.relative_to(tmp_path).as_posix(),
            "bytes": alias.stat().st_size,
            "sha256": digest(alias),
        }
    )
    manifest_path = tmp_path / builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plan = {
        "root": tmp_path,
        "seed_bank_path": seed,
        "candidate_dir": candidate_dir,
        "provisional_resolution_path": tmp_path / "provisional.json",
        "final_resolution_path": tmp_path / "final.json",
        "candidate_seed_sha256": digest(seed),
        "candidate_files": candidate_files,
        "sealed_evidence_hashes": {
            builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH: digest(manifest_path)
        },
    }
    monkeypatch.setattr(
        builder,
        "_historical_consensus_verifier",
        lambda root, write_manifest=False: manifest,
    )
    with pytest.raises(
        ValueError, match="raw consensus-manifest artifact changed"
    ):
        finalizer.apply_finalization(plan)
    assert seed.read_bytes() == b"pending-seed\n"
    assert not plan["provisional_resolution_path"].exists()
    assert not plan["final_resolution_path"].exists()
    for name, raw in candidate_files.items():
        assert (candidate_dir / name).read_bytes() == raw


def test_finalizer_rechecks_current_controls_before_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    candidate_files = {
        name: f"pending-{name}\n".encode("utf-8") for name in finalizer.FROZEN_NAMES
    }
    for name, raw in candidate_files.items():
        (candidate_dir / name).write_bytes(raw)
    seed = tmp_path / "seed.json"
    seed.write_bytes(b"pending-seed\n")
    checkpoint = {"head_commit": "a" * 40}
    manifest = {"repository_checkpoint": checkpoint, "artifacts": []}
    manifest_path = tmp_path / builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plan = {
        "root": tmp_path,
        "seed_bank_path": seed,
        "candidate_dir": candidate_dir,
        "provisional_resolution_path": tmp_path / "provisional.json",
        "final_resolution_path": tmp_path / "final.json",
        "candidate_seed_sha256": digest(seed),
        "candidate_files": candidate_files,
        "sealed_evidence_hashes": {
            builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH: digest(manifest_path)
        },
    }
    monkeypatch.setattr(
        builder,
        "_historical_consensus_verifier",
        lambda root, write_manifest=False: manifest,
    )
    monkeypatch.setattr(
        audit, "reauthenticate_manifest_artifact_inventory", lambda *args: None
    )
    monkeypatch.setattr(
        audit,
        "authenticate_historical_repository_checkpoint",
        lambda *args: (_ for _ in ()).throw(
            audit.AuditError("current governance control differs")
        ),
    )
    with pytest.raises(ValueError, match="current governance controls differ"):
        finalizer.apply_finalization(plan)
    assert seed.read_bytes() == b"pending-seed\n"
    assert not plan["provisional_resolution_path"].exists()
    assert not plan["final_resolution_path"].exists()
    for name, raw in candidate_files.items():
        assert (candidate_dir / name).read_bytes() == raw


def test_finalization_planning_rejects_current_control_drift_before_core(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = {"head_commit": "a" * 40}
    manifest_path = tmp_path / builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(
        json.dumps({"repository_checkpoint": checkpoint}), encoding="utf-8"
    )
    core_called = False

    def must_not_run(**kwargs):
        nonlocal core_called
        core_called = True
        raise AssertionError("qualified finalization core must not run")

    monkeypatch.setattr(finalizer, "_CORE_PREPARE", must_not_run)
    monkeypatch.setattr(
        audit,
        "authenticate_historical_repository_checkpoint",
        lambda *args: (_ for _ in ()).throw(
            audit.AuditError("current governance control differs")
        ),
    )
    with pytest.raises(ValueError, match="during finalization planning"):
        finalizer.prepare_finalization(root=tmp_path)
    assert core_called is False


def test_finalizer_rejects_unlisted_evidence_file_before_first_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate_dir = tmp_path / "candidate"
    candidate_dir.mkdir()
    candidate_files = {
        name: f"pending-{name}\n".encode("utf-8") for name in finalizer.FROZEN_NAMES
    }
    for name, raw in candidate_files.items():
        (candidate_dir / name).write_bytes(raw)
    seed = tmp_path / "seed.json"
    seed.write_bytes(b"pending-seed\n")
    artifacts: list[dict] = []
    for slot in audit.AUDIT_SLOTS:
        directory = audit.output_paths(tmp_path, slot)["evidence"]
        directory.mkdir(parents=True)
        leaf = directory / "batch_01.prompt.txt"
        leaf.write_bytes(f"slot-{slot}\n".encode())
        artifacts.append(
            {
                "role": f"slot_{slot}_batch_01_rendered_prompt",
                "path": leaf.relative_to(tmp_path).as_posix(),
                "bytes": leaf.stat().st_size,
                "sha256": digest(leaf),
            }
        )
    extra = audit.output_paths(tmp_path, 4)["evidence"] / "unlisted.stderr.txt"
    extra.write_bytes(b"hostile extra\n")
    manifest = {
        "repository_checkpoint": {"head_commit": "a" * 40},
        "artifacts": artifacts,
    }
    manifest_path = tmp_path / builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    plan = {
        "root": tmp_path,
        "seed_bank_path": seed,
        "candidate_dir": candidate_dir,
        "provisional_resolution_path": tmp_path / "provisional.json",
        "final_resolution_path": tmp_path / "final.json",
        "candidate_seed_sha256": digest(seed),
        "candidate_files": candidate_files,
        "sealed_evidence_hashes": {
            builder.CANONICAL_AUDIT_CONSENSUS_MANIFEST_PATH: digest(manifest_path)
        },
    }
    monkeypatch.setattr(
        builder,
        "_historical_consensus_verifier",
        lambda root, write_manifest=False: manifest,
    )
    with pytest.raises(ValueError, match="raw consensus-manifest artifact changed"):
        finalizer.apply_finalization(plan)
    assert seed.read_bytes() == b"pending-seed\n"
    assert not plan["provisional_resolution_path"].exists()
    assert not plan["final_resolution_path"].exists()
    for name, raw in candidate_files.items():
        assert (candidate_dir / name).read_bytes() == raw


def test_builder_and_generator_reproduce_pending_v13_bytes() -> None:
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


def test_config_anchors_exact_four_pass_protocol_runner_and_tests() -> None:
    config = json.loads((audit.ROOT / audit.CONFIG_RELATIVE_PATH).read_text())
    expected = audit.expected_label_audit_protocol_config(
        runner_sha256=digest(audit.ROOT / audit.RUNNER_RELATIVE_PATH),
        protocol_sha256=digest(audit.ROOT / audit.PROTOCOL_RELATIVE_PATH),
        tests_sha256=digest(audit.ROOT / audit.TESTS_RELATIVE_PATH),
        core_runner_sha256=digest(audit.ROOT / audit.CORE_RELATIVE_PATH),
        builder_sha256=digest(audit.ROOT / audit.BUILDER_RELATIVE_PATH),
        base_builder_sha256=digest(audit.ROOT / audit.BASE_BUILDER_RELATIVE_PATH),
        v11_builder_sha256=digest(audit.ROOT / audit.V11_BUILDER_RELATIVE_PATH),
        v11_runner_sha256=digest(audit.ROOT / audit.V11_RUNNER_RELATIVE_PATH),
        verifier_sha256=digest(audit.ROOT / audit.VERIFIER_RELATIVE_PATH),
        v11_verifier_sha256=digest(audit.ROOT / audit.V11_VERIFIER_RELATIVE_PATH),
        finalizer_sha256=digest(audit.ROOT / audit.FINALIZER_RELATIVE_PATH),
        v11_finalizer_sha256=digest(audit.ROOT / audit.V11_FINALIZER_RELATIVE_PATH),
    )
    assert config["experiment_id"] == "px062-skill-selection-gate2-2-v1-3-20260728"
    assert config["protocol_version"] == "2.2.3"
    assert config["label_audit_protocol"] == expected
    assert expected["full_audit_passes"] == 4
    assert expected["accepted_sessions_required"] == 172
    assert expected["single_dissent_tolerated"] is True
    assert expected["semantic_retry_permitted"] is False
    assert expected["slot_execution_order"] == [1, 2, 3, 4]
    assert expected["prior_audit_session_blacklist"] == audit.v12_blacklist_evidence(
        audit.ROOT
    )
    assert expected["governance_code"] == {
        "runner_core": {
            "path": audit.CORE_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.CORE_RELATIVE_PATH),
        },
        "builder": {
            "path": audit.BUILDER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.BUILDER_RELATIVE_PATH),
        },
        "builder_base": {
            "path": audit.BASE_BUILDER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.BASE_BUILDER_RELATIVE_PATH),
        },
        "v11_builder": {
            "path": audit.V11_BUILDER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.V11_BUILDER_RELATIVE_PATH),
        },
        "v11_runner": {
            "path": audit.V11_RUNNER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.V11_RUNNER_RELATIVE_PATH),
        },
        "verifier": {
            "path": audit.VERIFIER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.VERIFIER_RELATIVE_PATH),
        },
        "verifier_base": {
            "path": audit.V11_VERIFIER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.V11_VERIFIER_RELATIVE_PATH),
        },
        "finalizer": {
            "path": audit.FINALIZER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.FINALIZER_RELATIVE_PATH),
        },
        "finalizer_base": {
            "path": audit.V11_FINALIZER_RELATIVE_PATH.as_posix(),
            "sha256": digest(audit.ROOT / audit.V11_FINALIZER_RELATIVE_PATH),
        },
    }


def test_old_audits_cannot_fill_v13_slots() -> None:
    assert len(builder.CANONICAL_AUDIT_PATHS) == 4
    assert all("gate2_2_context_structured_v1_3_20260728" in path for path in builder.CANONICAL_AUDIT_PATHS)
    assert all("v1_2" not in path for path in builder.CANONICAL_AUDIT_PATHS)
    assert finalizer.CORE_DEPENDENCIES == (
        "scripts/finalize_px062_gate2_2_v11_labels.py",
        "scripts/build_px062_gate2_2_v13_benchmark.py",
        "scripts/build_px062_gate2_2_benchmark.py",
        "scripts/build_px062_gate2_2_v11_benchmark.py",
        "scripts/verify_px062_gate2_2_v13_label_audits.py",
        "scripts/verify_px062_gate2_2_v11_label_audits.py",
        "scripts/run_px062_gate2_2_v13_blind_audit.py",
        "scripts/run_px062_gate2_2_blind_audit.py",
        "scripts/run_px062_gate2_2_v11_blind_audit.py",
    )


def test_direct_script_finalizer_reaches_semantic_missing_evidence_path(
    tmp_path: Path,
) -> None:
    """Regression for v1.2's direct-script ``scripts`` import resolution bug."""

    temp_root = tmp_path / "synthetic-root"
    for relative in (
        builder.DEFAULT_SEED_BANK,
        builder.DEFAULT_REGISTRY_INVENTORY,
        builder.DEFAULT_PRIOR_TASKS,
        builder.SOURCE_TASKS_PATH,
    ):
        source = builder.ROOT / relative
        target = temp_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    candidate = builder.build_artifacts(
        root=temp_root,
        seed_bank_path=temp_root / builder.DEFAULT_SEED_BANK,
        registry_path=temp_root / builder.DEFAULT_REGISTRY_INVENTORY,
        prior_tasks_path=temp_root / builder.DEFAULT_PRIOR_TASKS,
    )
    candidate_dir = temp_root / builder.DEFAULT_OUTPUT_DIR
    candidate_dir.mkdir(parents=True)
    for name, raw in candidate.items():
        (candidate_dir / name).write_bytes(raw)
    completed = subprocess.run(
        [
            sys.executable,
            str(builder.ROOT / "scripts/finalize_px062_gate2_2_v13_labels.py"),
            "--root",
            str(temp_root),
        ],
        cwd=builder.ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=120,
    )
    assert completed.returncode != 0
    assert "missing canonical audit evidence" in completed.stderr
    assert "cannot import name" not in completed.stderr
    assert "audit runner is not yet frozen" not in completed.stderr
    assert "canonical blinded" not in completed.stderr
