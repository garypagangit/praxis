#!/usr/bin/env python
"""Independent one-look adjudicator for PX-062 Gate 2.2 v1.1."""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, Iterator

try:
    from scripts import adjudicate_px062_gate2_2 as core
    from scripts import fetch_px062_gate2_2_v11_results as v11_fetch
    from scripts import register_px062_gate2_2_v11_fetch as v11_register
    from scripts.px062_gate2_2_v11_contract import (
        ADJUDICATOR_PATH,
        EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
    )
except ImportError:  # Direct ``python scripts/...`` execution.
    import adjudicate_px062_gate2_2 as core  # type: ignore[no-redef]
    import fetch_px062_gate2_2_v11_results as v11_fetch  # type: ignore[no-redef]
    import register_px062_gate2_2_v11_fetch as v11_register  # type: ignore[no-redef]
    from px062_gate2_2_v11_contract import (  # type: ignore[no-redef]
        ADJUDICATOR_PATH,
        EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256,
        FROZEN_EVIDENCE_PATHS,
        MANIFEST_DIR,
    )


DEFAULT_REGISTRATION = MANIFEST_DIR / "confirmatory_registration.json"
FROZEN_CONFIG_CONTRACT_SHA256 = EXPECTED_SEMANTIC_CONFIG_PROJECTION_SHA256
FROZEN_EVIDENCE_CONTRACT = FROZEN_EVIDENCE_PATHS

_CORE_ADJUDICATE = core.adjudicate
_CORE_MAIN = core.main

# Re-export the pure statistical and trace-validation interface.
Z_95 = core.Z_95
EXPECTED_TASKS = core.EXPECTED_TASKS
EXPECTED_TRACES = core.EXPECTED_TRACES
EXPECTED_MODELS = core.EXPECTED_MODELS
FROZEN_MODEL_REVISIONS = core.FROZEN_MODEL_REVISIONS
FROZEN_DEPENDENCIES = core.FROZEN_DEPENDENCIES
FROZEN_GATES = core.FROZEN_GATES
EXPECTED_ARMS = core.EXPECTED_ARMS
A_FIELDS = core.A_FIELDS
STRUCTURED_FIELDS = core.STRUCTURED_FIELDS
TRACE_FIELDS = core.TRACE_FIELDS
canonical_json_sha256 = core.canonical_json_sha256
text_sha256 = core.text_sha256
read_jsonl = core.read_jsonl
wilson_95 = core.wilson_95
rate = core.rate
one_sided_mcnemar = core.one_sided_mcnemar
holm_adjust = core.holm_adjust
reconstructed_messages = core.reconstructed_messages
resolve_adjudication_paths = core.resolve_adjudication_paths
acquire_one_look_claim = core.acquire_one_look_claim
mark_one_look_outcome_read_started = core.mark_one_look_outcome_read_started
complete_one_look_claim = core.complete_one_look_claim


def adjudicate(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault(
        "expected_config_contract_sha256", FROZEN_CONFIG_CONTRACT_SHA256
    )
    return _CORE_ADJUDICATE(*args, **kwargs)


@contextlib.contextmanager
def bound_core() -> Iterator[None]:
    bindings = {
        "ADJUDICATOR_PATH": ADJUDICATOR_PATH,
        "DEFAULT_REGISTRATION": DEFAULT_REGISTRATION,
        "DEFAULT_ADJUDICATION_AUTHORIZATION": (
            v11_register.DEFAULT_ADJUDICATION_AUTHORIZATION
        ),
        "DEFAULT_ADJUDICATION_CONSUMPTION": (
            v11_register.DEFAULT_ADJUDICATION_CONSUMPTION
        ),
        "DEFAULT_ADJUDICATION_RESULT": v11_register.DEFAULT_ADJUDICATION_RESULT,
        "FROZEN_EVIDENCE_CONTRACT": FROZEN_EVIDENCE_CONTRACT,
        "FROZEN_CONFIG_CONTRACT_SHA256": FROZEN_CONFIG_CONTRACT_SHA256,
        "OUTPUT_FILES": v11_fetch.OUTPUT_FILES,
        "SEALED_PAYLOAD_FILES": v11_fetch.SEALED_PAYLOAD_FILES,
        "SOURCE_GIT_PATHS": v11_fetch.SOURCE_GIT_PATHS,
        "adjudicate": adjudicate,
    }
    previous = {name: getattr(core, name) for name in bindings}
    try:
        with v11_register.bound_core():
            for name, value in bindings.items():
                setattr(core, name, value)
            yield
    finally:
        for name, value in previous.items():
            setattr(core, name, value)


def verify_registered_adjudicator(*args: Any, **kwargs: Any) -> Any:
    with bound_core():
        return core.verify_registered_adjudicator(*args, **kwargs)


def verify_committed_adjudication_authorization(*args: Any, **kwargs: Any) -> Any:
    with bound_core():
        return core.verify_committed_adjudication_authorization(*args, **kwargs)


def verify_adjudication_provenance(*args: Any, **kwargs: Any) -> Any:
    with bound_core():
        return core.verify_adjudication_provenance(*args, **kwargs)


def main() -> None:
    with bound_core():
        _CORE_MAIN()


if __name__ == "__main__":
    main()
