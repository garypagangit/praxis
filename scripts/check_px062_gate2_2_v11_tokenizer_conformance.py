#!/usr/bin/env python
"""Run the versioned PX-062 Gate 2.2 v1.1 tokenizer conformance gate."""

from __future__ import annotations

import argparse
import contextlib
import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import check_px062_gate2_2_tokenizer_conformance as core
    from scripts.px062_gate2_2_v11_contract import (
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        CONFORMANCE_PATH,
        EXPECTED_TASKS_SHA256,
        TASKS_PATH,
        TOKENIZER_CHECKER_PATH,
        validate_label_freeze,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import check_px062_gate2_2_tokenizer_conformance as core  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        CONFORMANCE_PATH,
        EXPECTED_TASKS_SHA256,
        TASKS_PATH,
        TOKENIZER_CHECKER_PATH,
        validate_label_freeze,
    )


ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_SCHEMA = "px062-gate2.2-v1.1-tokenizer-conformance-v1"

# Pure helpers are safe to reuse directly.  The two functions that depend on
# corpus globals are wrapped below and never mutate v1 state outside a bounded
# context.
EXPECTED_MODEL_REVISIONS = core.EXPECTED_MODEL_REVISIONS
EXPECTED_DEPENDENCIES = core.EXPECTED_DEPENDENCIES
EXPECTED_ARMS = core.EXPECTED_ARMS
CONTEXT_WINDOW_TOKENS = core.CONTEXT_WINDOW_TOKENS
sha256_bytes = core.sha256_bytes
sha256_file = core.sha256_file
read_json = core.read_json
read_jsonl = core.read_jsonl
semantic_config_projection = core.semantic_config_projection
semantic_config_projection_record = core.semantic_config_projection_record
check_dependencies = core.check_dependencies
build_exact_open_response_probe = core.build_exact_open_response_probe
verify_choice_roundtrips = core.verify_choice_roundtrips
render_token_ids = core.render_token_ids
construct_all_messages = core.construct_all_messages
check_model = core.check_model


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    bindings = {
        "EXPECTED_TASKS_SHA256": EXPECTED_TASKS_SHA256,
        "COLLECTOR_SOURCE": ROOT / COLLECTOR_PATH,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        for name, value in bindings.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def validate_protocol(config: dict[str, Any], tasks_path: Path) -> dict[str, str]:
    with _bound_core():
        return core.validate_protocol(config, tasks_path)


def _require_canonical_path(path: Path, expected: str, label: str) -> Path:
    resolved = path.resolve()
    if resolved != (ROOT / expected).resolve():
        raise ValueError(f"v1.1 {label} path differs from the frozen contract")
    return resolved


def run_check(
    *,
    config_path: Path,
    tasks_path: Path,
    catalog_path: Path,
    output_path: Path,
    checked_at_utc: str,
    local_files_only: bool,
) -> dict[str, Any]:
    """Run only after unanimous label finalization and emit a v1.1 receipt."""

    config_path = _require_canonical_path(config_path, CONFIG_PATH, "config")
    tasks_path = _require_canonical_path(tasks_path, TASKS_PATH, "tasks")
    catalog_path = _require_canonical_path(
        catalog_path, CATALOG_PATH, "registry catalog"
    )
    try:
        checked = datetime.fromisoformat(checked_at_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("v1.1 conformance timestamp is invalid") from exc
    if (
        not checked_at_utc.endswith("Z")
        or checked.tzinfo is None
        or checked.utcoffset() != timezone.utc.utcoffset(checked)
    ):
        raise ValueError("v1.1 conformance timestamp must be UTC with a Z suffix")
    validate_label_freeze(ROOT)
    output_path = output_path.resolve()
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite conformance receipt: {output_path}")

    with tempfile.TemporaryDirectory(prefix="px062-g22-v11-conformance-") as temp:
        staging = Path(temp) / "core-receipt.json"
        with _bound_core():
            result = core.run_check(
                config_path=config_path,
                tasks_path=tasks_path,
                catalog_path=catalog_path,
                output_path=staging,
                checked_at_utc=checked_at_utc,
                local_files_only=local_files_only,
            )
    result = copy.deepcopy(result)
    result["schema_version"] = CONFORMANCE_SCHEMA
    result["checker"] = {
        "path": TOKENIZER_CHECKER_PATH,
        "sha256": sha256_file(Path(__file__)),
    }
    result["message_constructor_source"] = {
        "path": COLLECTOR_PATH,
        "sha256": sha256_file(ROOT / COLLECTOR_PATH),
    }
    result["interpretation"] = (
        "All frozen v1.1 tasks, task-local option maps/catalogs, and exact A-E "
        "messages conform under both pinned tokenizers and saved artifact "
        "reloads. This is implementation integrity evidence, not a semantic result."
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path(CONFIG_PATH))
    parser.add_argument("--tasks", type=Path, default=Path(TASKS_PATH))
    parser.add_argument("--registry-catalog", type=Path, default=Path(CATALOG_PATH))
    parser.add_argument("--output", type=Path, default=Path(CONFORMANCE_PATH))
    parser.add_argument("--checked-at-utc", required=True)
    parser.add_argument("--allow-network", action="store_true")
    args = parser.parse_args()
    result = run_check(
        config_path=args.config,
        tasks_path=args.tasks,
        catalog_path=args.registry_catalog,
        output_path=args.output,
        checked_at_utc=args.checked_at_utc,
        local_files_only=not args.allow_network,
    )
    print(
        json.dumps(
            {
                "models": [row["model_id"] for row in result["models"]],
                "pass": result["pass"],
                "tasks_sha256": result["tasks_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
