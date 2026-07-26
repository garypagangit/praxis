"""PX-063 deterministic reward-hack transcript verification."""

from .decision_policy import VerificationDecision, verify_trace_row
from .trace_adapter import (
    DEFAULT_HF_REVISION,
    EXPECTED_CLEAN_ROWS,
    EXPECTED_HACKING_ROWS,
    EXPECTED_TRACE_ROWS,
    recover_trace_label,
)

__all__ = [
    "DEFAULT_HF_REVISION",
    "EXPECTED_CLEAN_ROWS",
    "EXPECTED_HACKING_ROWS",
    "EXPECTED_TRACE_ROWS",
    "VerificationDecision",
    "recover_trace_label",
    "verify_trace_row",
]
