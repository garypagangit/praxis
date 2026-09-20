"""Deterministic offline eligibility; absent evidence always retains the alert.

Context must come from an independent trusted evidence service, never from
model output or a flag embedded in attacker-controlled alert content.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

IDENTITY_FIELDS = ("host", "user", "rule_id", "timestamp")
SEVERITIES = {"informational", "low", "medium", "high", "critical"}


@dataclass(frozen=True)
class EvidenceContext:
    raw_event: Mapping | None = None
    independent_source_verified: bool = False
    raw_reference: str | None = None
    allowed_rule_ids: frozenset = field(default_factory=frozenset)
    incident_context_complete: bool = False
    cluster_member: bool | None = None


def check_eligibility(alert, context=None):
    context = context or EvidenceContext()
    if not isinstance(alert, Mapping):
        alert = {}
    nonempty = lambda x: isinstance(x, str) and bool(x.strip())
    fields_ok = all(nonempty(alert.get(k)) for k in IDENTITY_FIELDS)
    try:
        stamp = datetime.fromisoformat(str(alert.get("timestamp", "")).replace("Z", "+00:00"))
        fields_ok = fields_ok and stamp.tzinfo is not None
    except ValueError:
        fields_ok = False
    raw = context.raw_event
    p1 = (context.independent_source_verified is True and nonempty(context.raw_reference)
          and isinstance(raw, Mapping) and fields_ok
          and all(nonempty(raw.get(k)) and raw[k] == alert[k] for k in IDENTITY_FIELDS))
    severity = alert.get("severity")
    trusted_severity = raw.get("severity") if isinstance(raw, Mapping) else None
    p2 = (context.independent_source_verified is True and isinstance(severity, str)
          and severity in SEVERITIES and severity == trusted_severity and severity != "critical"
          and nonempty(alert.get("rule_id")) and alert["rule_id"] in context.allowed_rule_ids)
    p3 = context.incident_context_complete is True and context.cluster_member is False
    p4 = fields_ok and isinstance(severity, str) and severity in SEVERITIES
    predicates = {"P1_independent_raw_match": bool(p1), "P2_allowed_noncritical_rule": bool(p2),
                  "P3_complete_unclustered_context": bool(p3), "P4_valid_required_schema": bool(p4)}
    return {"eligible": all(predicates.values()), "predicates": predicates,
            "failed_predicates": [key for key, passed in predicates.items() if not passed]}
