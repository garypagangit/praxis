#!/usr/bin/env python
"""Launch exactly the committed PX-062 Gate 2.2 v1.1 registration."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import launch_px062_gate2_2_registered as core
    from scripts.px062_gate2_2_v11_contract import (
        CONFIG_PATH,
        DEFAULT_JOB_NAME,
        ENTRYPOINT_PATH,
        MANIFEST_DIR,
        validate_label_freeze,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import launch_px062_gate2_2_registered as core  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        CONFIG_PATH,
        DEFAULT_JOB_NAME,
        ENTRYPOINT_PATH,
        MANIFEST_DIR,
        validate_label_freeze,
    )


DEFAULT_REGISTRATION = MANIFEST_DIR / "confirmatory_registration.json"
_CORE_LAUNCH = core.launch

sha256_bytes = core.sha256_bytes
validate_repository = core.validate_repository
validate_request = core.validate_request
validate_unversioned_source_binding = core.validate_unversioned_source_binding
find_training_job = core.find_training_job
validate_recoverable_job = core.validate_recoverable_job
validate_existing_receipt = core.validate_existing_receipt


@contextlib.contextmanager
def _bound_core() -> Iterator[None]:
    bindings = {
        "DEFAULT_REGISTRATION": DEFAULT_REGISTRATION,
        "EXPECTED_CONFIG": CONFIG_PATH,
        "EXPECTED_ENTRYPOINT": ENTRYPOINT_PATH,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        for name, value in bindings.items():
            setattr(core, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def launch(root: Path, profile: str, registration_path: Path) -> dict[str, Any]:
    root = root.resolve()
    resolved = (
        registration_path
        if registration_path.is_absolute()
        else root / registration_path
    ).resolve()
    if resolved != (root / DEFAULT_REGISTRATION).resolve():
        raise ValueError("v1.1 launch registration path differs from the frozen contract")
    registration = json.loads(resolved.read_text(encoding="utf-8"))
    if registration.get("job_name") != DEFAULT_JOB_NAME:
        raise ValueError("v1.1 launch registration job name drift")
    source_commit = registration.get("source_commit")
    if not isinstance(source_commit, str):
        raise ValueError("v1.1 launch registration source commit is missing")
    validate_label_freeze(root, source_commit=source_commit)
    with _bound_core():
        return _CORE_LAUNCH(root, profile, resolved)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipt = launch(root, args.profile, args.registration)
    print(
        json.dumps(
            {
                "job_name": receipt["training_job_name"],
                "status": receipt["status_at_receipt"],
                "source_version_id": receipt["source_version_id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
