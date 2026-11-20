#!/usr/bin/env python
"""Register completed PX-062 Gate 2.2 v1.1 evidence before download."""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import fetch_px062_gate2_2_v11_results as v11_fetch
    from scripts import register_px062_gate2_2_fetch as core
    from scripts.px062_gate2_2_v11_contract import (
        ADJUDICATOR_PATH,
        CONFIRMATORY_RESULT_PATH,
        FETCH_REGISTRAR_PATH,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
        SEALED_CONFIRMATION_DIR,
        validate_label_freeze,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import fetch_px062_gate2_2_v11_results as v11_fetch  # type: ignore[no-redef]
    import register_px062_gate2_2_fetch as core  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        ADJUDICATOR_PATH,
        CONFIRMATORY_RESULT_PATH,
        FETCH_REGISTRAR_PATH,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
        SEALED_CONFIRMATION_DIR,
        validate_label_freeze,
    )


DEFAULT_LAUNCH_REGISTRATION = MANIFEST_DIR / "confirmatory_registration.json"
DEFAULT_LAUNCH_RECEIPT = MANIFEST_DIR / "launch_receipt.json"
DEFAULT_COMPLETION_REGISTRATION = MANIFEST_DIR / "completion_registration.json"
DEFAULT_FETCH_RECEIPT = SEALED_CONFIRMATION_DIR / "completion_fetch_receipt.json"
DEFAULT_ADJUDICATION_AUTHORIZATION = MANIFEST_DIR / "adjudication_authorization.json"
DEFAULT_ADJUDICATION_RESULT = CONFIRMATORY_RESULT_PATH
DEFAULT_ADJUDICATION_CONSUMPTION = MANIFEST_DIR / "adjudication_consumption.json"
FROZEN_EVIDENCE_CONTRACT = FROZEN_EVIDENCE_PATHS

_CORE_REGISTER_COMPLETION = core.register_completion
_CORE_REGISTER_AUTHORIZATION = core.register_adjudication_authorization

registered_artifact = core.registered_artifact
validate_launch_evidence = core.validate_launch_evidence


@contextlib.contextmanager
def bound_core() -> Iterator[None]:
    bindings = {
        "DEFAULT_LAUNCH_REGISTRATION": DEFAULT_LAUNCH_REGISTRATION,
        "DEFAULT_LAUNCH_RECEIPT": DEFAULT_LAUNCH_RECEIPT,
        "DEFAULT_COMPLETION_REGISTRATION": DEFAULT_COMPLETION_REGISTRATION,
        "DEFAULT_DESTINATION": v11_fetch.DEFAULT_DESTINATION,
        "DEFAULT_FETCH_RECEIPT": DEFAULT_FETCH_RECEIPT,
        "DEFAULT_ADJUDICATION_AUTHORIZATION": DEFAULT_ADJUDICATION_AUTHORIZATION,
        "DEFAULT_ADJUDICATION_RESULT": DEFAULT_ADJUDICATION_RESULT,
        "DEFAULT_ADJUDICATION_CONSUMPTION": DEFAULT_ADJUDICATION_CONSUMPTION,
        "ADJUDICATOR_PATH": ADJUDICATOR_PATH,
        "FROZEN_EVIDENCE_CONTRACT": FROZEN_EVIDENCE_CONTRACT,
        "ANSWER_KEY_PATH": v11_fetch.ANSWER_KEY_PATH,
        "PX062_GATE22_PREFIX": v11_fetch.S3_PREFIX,
        "FETCHER_PATH": v11_fetch.FETCHER_PATH,
        "FETCH_TEST_PATH": v11_fetch.EXECUTION_TEST_PATH,
        "REGISTRAR_PATH": FETCH_REGISTRAR_PATH,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        with v11_fetch.bound_core():
            for name, value in bindings.items():
                setattr(core, name, value)
            yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def _source_commit(root: Path, launch_path: Path) -> str:
    path = launch_path if launch_path.is_absolute() else root / launch_path
    launch = json.loads(path.read_text(encoding="utf-8"))
    value = launch.get("source_commit")
    if not isinstance(value, str):
        raise ValueError("v1.1 launch registration source commit is missing")
    return value


def register_completion(**kwargs: Any) -> dict[str, Any]:
    root = Path(kwargs["root"]).resolve()
    source_commit = _source_commit(root, Path(kwargs["launch_path"]))
    # Authenticate the label freeze before the first delegated AWS metadata call.
    validate_label_freeze(root, source_commit=source_commit)
    with bound_core():
        return _CORE_REGISTER_COMPLETION(**kwargs)


def register_adjudication_authorization(**kwargs: Any) -> dict[str, Any]:
    with bound_core():
        return _CORE_REGISTER_AUTHORIZATION(**kwargs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Metadata-only PX-062 Gate 2.2 v1.1 completion registration"
    )
    parser.add_argument("--profile", default="praxis-build")
    parser.add_argument(
        "--launch-registration", type=Path, default=DEFAULT_LAUNCH_REGISTRATION
    )
    parser.add_argument("--launch-receipt", type=Path, default=DEFAULT_LAUNCH_RECEIPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_COMPLETION_REGISTRATION)
    parser.add_argument(
        "--fetch-receipt",
        type=Path,
        help="Create the exclusive adjudication authorization from this sealed receipt",
    )
    parser.add_argument(
        "--authorization-output",
        type=Path,
        default=DEFAULT_ADJUDICATION_AUTHORIZATION,
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.fetch_receipt is not None:
        authorization = register_adjudication_authorization(
            root=root,
            fetch_receipt_path=args.fetch_receipt,
            completion_path=args.output,
            authorization_path=args.authorization_output,
        )
        print(
            json.dumps(
                {
                    "authorization": args.authorization_output.as_posix(),
                    "fetch_receipt_sha256": authorization["fetch_receipt"]["sha256"],
                    "status": "REGISTERED_NOT_ADJUDICATED",
                },
                indent=2,
            )
        )
        return
    completion = register_completion(
        root=root,
        profile=args.profile,
        launch_path=args.launch_registration,
        receipt_path=args.launch_receipt,
        completion_path=args.output,
    )
    print(
        json.dumps(
            {
                "job_name": completion["job"]["name"],
                "output_bytes": completion["output_artifact"]["bytes"],
                "output_version_id": completion["output_artifact"]["version_id"],
                "scientific_outputs_downloaded": completion[
                    "scientific_outputs_downloaded"
                ],
                "scientific_outputs_inspected": completion[
                    "scientific_outputs_inspected"
                ],
                "status": completion["job"]["status"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
