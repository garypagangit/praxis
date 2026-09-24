#!/usr/bin/env python
"""Build the deterministic, answer-key-blind PX-062 Gate 2.2 v1.1 bundle."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import build_px062_gate2_2_bundle as core
    from scripts.px062_gate2_2_v11_contract import (
        ANSWER_KEY_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        ENTRYPOINT_PATH,
        REQUIREMENTS_GIT_PATH,
        TASKS_PATH,
        validate_frozen_config as validate_v11_config,
        validate_label_freeze,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import build_px062_gate2_2_bundle as core  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        ANSWER_KEY_PATH,
        BENCHMARK_MANIFEST_PATH,
        CATALOG_PATH,
        COLLECTOR_PATH,
        CONFIG_PATH,
        ENTRYPOINT_PATH,
        REQUIREMENTS_GIT_PATH,
        TASKS_PATH,
        validate_frozen_config as validate_v11_config,
        validate_label_freeze,
    )


ARCHIVE_MEMBERS = {
    CONFIG_PATH: CONFIG_PATH,
    TASKS_PATH: TASKS_PATH,
    CATALOG_PATH: CATALOG_PATH,
    BENCHMARK_MANIFEST_PATH: BENCHMARK_MANIFEST_PATH,
    COLLECTOR_PATH: COLLECTOR_PATH,
    ENTRYPOINT_PATH: ENTRYPOINT_PATH,
    "requirements.txt": REQUIREMENTS_GIT_PATH,
}

sha256_bytes = core.sha256_bytes
sha256_file = core.sha256_file
canonical_json_bytes = core.canonical_json_bytes
validate_source_commit = core.validate_source_commit
build_manifest = core.build_manifest
deterministic_archive = core.deterministic_archive


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    bindings = {
        "CONFIG": CONFIG_PATH,
        "TASKS": TASKS_PATH,
        "CATALOG": CATALOG_PATH,
        "BENCHMARK_MANIFEST": BENCHMARK_MANIFEST_PATH,
        "ANSWER_KEY": ANSWER_KEY_PATH,
        "COLLECTOR": COLLECTOR_PATH,
        "ENTRYPOINT": ENTRYPOINT_PATH,
        "REQUIREMENTS_SOURCE": REQUIREMENTS_GIT_PATH,
        "ARCHIVE_MEMBERS": ARCHIVE_MEMBERS,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        for name, value in bindings.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def validate_frozen_config(config: dict[str, Any]) -> None:
    core.validate_frozen_config(config)
    validate_v11_config(config)


def build(root: Path, source_commit: str, output: Path) -> dict[str, Any]:
    validate_label_freeze(root, source_commit=source_commit)
    with _bound_core():
        return core.build(root, source_commit, output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(json.dumps(build(root, args.source_commit, args.output), indent=2))


if __name__ == "__main__":
    main()
