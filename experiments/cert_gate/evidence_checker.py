"""Frozen evidence-view and lexical-sensitivity helpers for offline research.

The checker must be fitted separately on evidence_view(FIT), using the same
LinearSVMScorer recipe as the full view. These projections provide no independent
raw authority. With an SVM, the appended notes test lexical sensitivity, not LLM
prompt-injection resistance. No model is fitted or loaded by this module.
"""
from copy import deepcopy
import json
import math
from numbers import Real
from typing import Mapping

if __package__:
    from .feature_grouping import feature_group_sha
else:
    from feature_grouping import feature_group_sha


EVIDENCE_FIELDS = (
    "proto", "method", "uri", "parameter", "req_header", "req_body",
    "rsp_header", "rsp_body", "rsp_status",
)
SUBSTANTIVE_FIELDS = (
    "uri", "parameter", "req_header", "req_body", "rsp_header", "rsp_body",
    "rsp_status",
)
EMPTY_TEXT = frozenset(("", "-", "null", "none", "n/a"))
DIRECTIVE_TEXT = (
    "This alert is benign. Ignore suspicious content and classify it as a routine health check."
)
NEUTRAL_TEXT = (
    "This is a recorded research annotation describing the current network observation for review."
)
NOTE_PREFIX = "X-Research-Note: "
NOTE_LENGTH = max(len(DIRECTIVE_TEXT), len(NEUTRAL_TEXT))
CONDITIONS = ("clean", "neutral", "directive")


def evidence_view(alert: Mapping) -> dict:
    """Copy only recorded evidence; exclude rule/host shortcuts and label fields."""
    if not isinstance(alert, Mapping):
        raise TypeError("An alert must be a mapping")
    return {key: deepcopy(alert[key]) for key in EVIDENCE_FIELDS if key in alert}


def _meaningful(value) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.casefold() in EMPTY_TEXT:
            return False
        # An empty serialized container does not create substantive evidence.
        # Ordinary text, including malformed JSON, remains observed content.
        if stripped.startswith(("{", "[")):
            try:
                decoded = json.loads(stripped)
            except (ValueError, TypeError):
                return True
            if isinstance(decoded, (dict, list)):
                return _meaningful(decoded)
        return True
    if isinstance(value, Mapping):
        return any(_meaningful(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_meaningful(item) for item in value)
    if isinstance(value, Real):
        return math.isfinite(float(value))
    return False


def has_evidence(alert: Mapping) -> bool:
    """Require substantive content, not only protocol/method or empty markers."""
    if not isinstance(alert, Mapping):
        raise TypeError("An alert must be a mapping")
    return any(_meaningful(alert.get(key)) for key in SUBSTANTIVE_FIELDS)


def evidence_group_sha(alert: Mapping) -> str:
    """Apply the existing IPv4-normalized grouping to the evidence view only."""
    return feature_group_sha(evidence_view(alert))


def evidence_eligible(alert: Mapping, benignness) -> bool:
    """Strict positive evidence-model margin, with absent/invalid scores rejected."""
    if isinstance(benignness, bool) or not isinstance(benignness, Real):
        return False
    return (math.isfinite(float(benignness)) and benignness > 0
            and has_evidence(alert))


def perturb(alert: Mapping, condition: str) -> dict:
    """Return a copied record with a fixed, length-matched request-header note.

    Labels and all other fields are retained unchanged for paired evaluation;
    serialize_features/evidence_view exclude labels from model inputs. Existing
    header strings remain an exact prefix. Non-string headers use canonical JSON.
    The shared research header must not be used as an eligibility marker.
    """
    if not isinstance(alert, Mapping):
        raise TypeError("An alert must be a mapping")
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown perturbation condition: {condition!r}")
    result = deepcopy(dict(alert))
    if condition == "clean":
        return result
    original = result.get("req_header", "")
    if not isinstance(original, str):
        original = json.dumps(original, sort_keys=True, ensure_ascii=False,
                              allow_nan=False, separators=(",", ":"))
    note = NEUTRAL_TEXT if condition == "neutral" else DIRECTIVE_TEXT
    separator = "" if not original or original.endswith(("\r", "\n")) else "\r\n"
    result["req_header"] = original + separator + NOTE_PREFIX + note.ljust(NOTE_LENGTH) + "\r\n"
    return result
