#!/usr/bin/env python
"""Run one frozen, blinded PX-062 Gate 2.2 v1.2 label audit.

The mechanically qualified v1 engine remains the execution core.  This
wrapper binds it to the v1.2 corpus, checkpoint, evidence namespace, protocol,
and self-hashed runner without modifying v1 or v1.1.  All 1,032 rows are
audited in 43 fresh 24-row ephemeral sessions for each fixed model slot.
"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import run_px062_gate2_2_blind_audit as core
except ImportError:  # Direct ``python scripts/...`` execution.
    import run_px062_gate2_2_blind_audit as core  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
GATE_DIR = (
    ROOT
    / "reports"
    / "coding_agent_skill_provenance"
    / "gate2_2_context_structured_v1_2_20260728"
)
FROZEN_DIR = GATE_DIR / "frozen_inputs"
AUDIT_DIR = GATE_DIR / "label_audits"
TASKS_PATH = FROZEN_DIR / "tasks.jsonl"
CATALOG_PATH = FROZEN_DIR / "registry_catalog.json"

EXPECTED_TASKS_SHA256 = (
    "e9a4c387781b7299884d75ebbb59f3ba1dcd398599821fb586db95e02fabea16"
)
EXPECTED_CATALOG_SHA256 = (
    "90a6f8cd28a489a448fae49198fde3ff34514b2b4a2aab421f05314441523212"
)
EXPECTED_CODEX_VERSION = core.EXPECTED_CODEX_VERSION
EXPECTED_TASKS = core.EXPECTED_TASKS
BATCH_SIZE = core.BATCH_SIZE
EXPECTED_BATCHES = core.EXPECTED_BATCHES
ATTEMPT_TIMEOUT_SECONDS = core.ATTEMPT_TIMEOUT_SECONDS
TASK_ID_NAMESPACE = core.TASK_ID_NAMESPACE

CONFIG_RELATIVE_PATH = Path("configs/px062_skill_selection_gate2_2_v1_2_20260728.json")
ANSWER_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/frozen_inputs/answer_key.jsonl"
)
MANIFEST_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/frozen_inputs/benchmark_manifest.json"
)
SEED_RELATIVE_PATH = Path(
    "manifests/px062_gate2_2_v1_2_20260728/task_seed_bank.json"
)
PROTOCOL_RELATIVE_PATH = Path(
    "reports/coding_agent_skill_provenance/"
    "gate2_2_context_structured_v1_2_20260728/"
    "LABEL_AUDIT_PROTOCOL_V1_2_20260728.md"
)
RUNNER_RELATIVE_PATH = Path("scripts/run_px062_gate2_2_v12_blind_audit.py")
TESTS_RELATIVE_PATH = Path("tests/test_px062_gate2_2_v12_blind_audit.py")
CORE_RELATIVE_PATH = Path("scripts/run_px062_gate2_2_blind_audit.py")
TRACKED_CHECKPOINT_PATHS = (
    Path(
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_v1_2_20260728/frozen_inputs/tasks.jsonl"
    ),
    Path(
        "reports/coding_agent_skill_provenance/"
        "gate2_2_context_structured_v1_2_20260728/frozen_inputs/registry_catalog.json"
    ),
    ANSWER_RELATIVE_PATH,
    MANIFEST_RELATIVE_PATH,
    SEED_RELATIVE_PATH,
    CONFIG_RELATIVE_PATH,
    RUNNER_RELATIVE_PATH,
    CORE_RELATIVE_PATH,
    PROTOCOL_RELATIVE_PATH,
    TESTS_RELATIVE_PATH,
)

SLOT_MODELS = dict(core.SLOT_MODELS)
SLOT_STEMS = dict(core.SLOT_STEMS)
DISABLED_FEATURES = tuple(core.DISABLED_FEATURES)
CONFIG_EXACT_COMMAND_SHAPE = core.CONFIG_EXACT_COMMAND_SHAPE
PROMPT_TEMPLATE_VERSION = core.PROMPT_TEMPLATE_VERSION
PROMPT_TEMPLATE = core.PROMPT_TEMPLATE

AuditError = core.AuditError
EventPolicyError = core.EventPolicyError
sha256_bytes = core.sha256_bytes
sha256_file = core.sha256_file
strict_json_loads = core.strict_json_loads
read_expected_bytes = core.read_expected_bytes
read_jsonl_bytes = core.read_jsonl_bytes
load_catalog = core.load_catalog
validate_tasks = core.validate_tasks
canonical_json_bytes = core.canonical_json_bytes
task_id_for_prompt = core.task_id_for_prompt
make_batches = core.make_batches
project_tasks_for_auditor = core.project_tasks_for_auditor
build_prompt = core.build_prompt
build_output_schema = core.build_output_schema
validate_response = core.validate_response
validate_canonical_audit_rows = core.validate_canonical_audit_rows
build_command = core.build_command
validate_exact_recorded_command = core.validate_exact_recorded_command
inspect_event_log = core.inspect_event_log
extract_exposed_thread_id = core.extract_exposed_thread_id
execute_attempt = core.execute_attempt


def _v12_output_paths(root: Path, slot: int) -> dict[str, Path]:
    if slot not in SLOT_MODELS:
        raise AuditError("audit slot must be 1 or 2")
    gate_dir = (
        root
        / "reports"
        / "coding_agent_skill_provenance"
        / "gate2_2_context_structured_v1_2_20260728"
    )
    stem = SLOT_STEMS[slot]
    return {
        "audit": gate_dir / f"label_audit_{slot}_predictions.jsonl",
        "sidecar": gate_dir / f"label_audit_{slot}_run.json",
        "evidence": gate_dir / "label_audits" / f"{stem}.evidence",
        "other_sidecar": gate_dir / f"label_audit_{3 - slot}_run.json",
        "manifest": gate_dir / "label_audit_evidence_manifest.json",
    }


_CORE_BINDINGS: dict[str, Any] = {
    "ROOT": ROOT,
    "FROZEN_DIR": FROZEN_DIR,
    "AUDIT_DIR": AUDIT_DIR,
    "TASKS_PATH": TASKS_PATH,
    "CATALOG_PATH": CATALOG_PATH,
    "EXPECTED_TASKS_SHA256": EXPECTED_TASKS_SHA256,
    "EXPECTED_CATALOG_SHA256": EXPECTED_CATALOG_SHA256,
    "CONFIG_RELATIVE_PATH": CONFIG_RELATIVE_PATH,
    "ANSWER_RELATIVE_PATH": ANSWER_RELATIVE_PATH,
    "MANIFEST_RELATIVE_PATH": MANIFEST_RELATIVE_PATH,
    "SEED_RELATIVE_PATH": SEED_RELATIVE_PATH,
    "PROTOCOL_RELATIVE_PATH": PROTOCOL_RELATIVE_PATH,
    "RUNNER_RELATIVE_PATH": RUNNER_RELATIVE_PATH,
    "TESTS_RELATIVE_PATH": TESTS_RELATIVE_PATH,
    "TRACKED_CHECKPOINT_PATHS": TRACKED_CHECKPOINT_PATHS,
    "output_paths": _v12_output_paths,
}


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    """Temporarily bind the sealed core to the v1.2 namespace."""

    previous = {name: getattr(core, name) for name in _CORE_BINDINGS}
    try:
        for name, value in _CORE_BINDINGS.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def _derive_core_function(function: Any, expected_counts: dict[str, int]) -> Any:
    """Compile one sealed core function after an exact path-only migration."""

    source = inspect.getsource(function)
    replacements = {
        "gate2_2_context_structured_20260728": (
            "gate2_2_context_structured_v1_2_20260728"
        ),
        "LABEL_AUDIT_PROTOCOL_20260728.md": (
            "LABEL_AUDIT_PROTOCOL_V1_2_20260728.md"
        ),
        "run_px062_gate2_2_blind_audit.py": (
            "run_px062_gate2_2_v12_blind_audit.py"
        ),
    }
    for old, expected in expected_counts.items():
        if source.count(old) != expected:
            raise RuntimeError(
                f"sealed audit core {function.__name__} source shape drift: {old}"
            )
        source = source.replace(old, replacements[old])
    namespace = dict(core.__dict__)
    namespace.update(_CORE_BINDINGS)
    exec(compile(source, str(RUNNER_RELATIVE_PATH), "exec"), namespace)
    return namespace[function.__name__]


_RUN_AUDIT_V12 = _derive_core_function(
    core.run_audit,
    {
        "gate2_2_context_structured_20260728": 2,
        "LABEL_AUDIT_PROTOCOL_20260728.md": 1,
        "run_px062_gate2_2_blind_audit.py": 1,
    },
)
_VERIFY_PAIR_V12 = _derive_core_function(
    core.verify_pair,
    {
        "LABEL_AUDIT_PROTOCOL_20260728.md": 2,
        "run_px062_gate2_2_blind_audit.py": 2,
    },
)


def output_paths(root: Path, slot: int) -> dict[str, Path]:
    return _v12_output_paths(root, slot)


def expected_label_audit_protocol_config(
    *, runner_sha256: str, protocol_sha256: str, tests_sha256: str
) -> dict[str, Any]:
    with _bound_core():
        return core.expected_label_audit_protocol_config(
            runner_sha256=runner_sha256,
            protocol_sha256=protocol_sha256,
            tests_sha256=tests_sha256,
        )


def validate_pending_seed_governance(seed: dict[str, Any]) -> dict[str, Any]:
    with _bound_core():
        return core.validate_pending_seed_governance(seed)


def validate_git_checkpoint_state(**kwargs: str) -> None:
    return core.validate_git_checkpoint_state(**kwargs)


def collect_repository_checkpoint(root: Path = ROOT) -> dict[str, Any]:
    with _bound_core():
        return core.collect_repository_checkpoint(root)


def authenticate_historical_repository_checkpoint(
    root: Path, checkpoint: dict[str, Any]
) -> dict[str, bytes]:
    with _bound_core():
        return core.authenticate_historical_repository_checkpoint(root, checkpoint)


def verify_pair(
    root: Path = ROOT,
    *,
    write_manifest: bool = True,
    verification_mode: str = "current",
) -> dict[str, Any]:
    with _bound_core():
        return _VERIFY_PAIR_V12(
            root,
            write_manifest=write_manifest,
            verification_mode=verification_mode,
        )


def run_audit(
    slot: int,
    *,
    root: Path = ROOT,
    codex_executable: str | None = None,
) -> tuple[Path, Path]:
    with _bound_core():
        return _RUN_AUDIT_V12(
            slot,
            root=root,
            codex_executable=codex_executable,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--slot", type=int, choices=(1, 2))
    operation.add_argument("--verify-pair", action="store_true")
    args = parser.parse_args()
    if args.verify_pair:
        result = verify_pair(ROOT, write_manifest=True)
        manifest_path = output_paths(ROOT, 1)["manifest"]
        print(
            json.dumps(
                {
                    "manifest": manifest_path.relative_to(ROOT).as_posix(),
                    "manifest_sha256": sha256_file(manifest_path),
                    "accepted_session_count": result["global_session_ids"][
                        "accepted_count"
                    ],
                },
                sort_keys=True,
            )
        )
        return
    audit_path, sidecar_path = run_audit(args.slot)
    print(
        json.dumps(
            {
                "audit": audit_path.relative_to(ROOT).as_posix(),
                "sidecar": sidecar_path.relative_to(ROOT).as_posix(),
                "audit_sha256": sha256_file(audit_path),
                "sidecar_sha256": sha256_file(sidecar_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
