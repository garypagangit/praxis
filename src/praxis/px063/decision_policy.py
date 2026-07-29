"""PX-063 block/review/allow policy with explicit abstention semantics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .deterministic_checks import (
    block_evidence,
    semantic_review_check_ids,
    target_review_check_ids,
    valid_evidence_anchor,
)
from .evidence_extractor import (
    assistant_response_text,
    candidate_ambiguity_turns,
    extract_observable_events,
    partition_contextual_events,
)
from .trace_adapter import (
    BlindedTraceRow,
    TraceDataError,
    blind_trace_row,
    blinded_messages,
)


@dataclass(frozen=True)
class VerificationDecision:
    decision: str
    score: float
    check_ids: list[str]
    evidence: list[dict[str, Any]]
    abstained: bool
    d_checkable: bool = True
    eligibility_reason: str = "complete_normalized_transcript"
    parse_failure: bool = False
    evidence_scope: str = "normalized_transcript_only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_blinded_row(row: BlindedTraceRow | Mapping[str, Any]) -> VerificationDecision:
    """Apply the policy using only a label-free prompt/trajectory pair."""

    try:
        messages = blinded_messages(row)
    except TraceDataError:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=["TRANSCRIPT_PARSE_FAILURE"],
            evidence=[],
            abstained=True,
            d_checkable=False,
            eligibility_reason="transcript_parse_failure",
            parse_failure=True,
        )
    if any(message.has_structured_payload for message in messages):
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=["STRUCTURED_PAYLOAD_UNSUPPORTED"],
            evidence=[],
            abstained=True,
            d_checkable=False,
            eligibility_reason="structured_payload_outside_normalized_contract",
        )
    events = extract_observable_events(messages)
    ambiguous_turns = candidate_ambiguity_turns(messages, events)
    if ambiguous_turns:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=["AMBIGUOUS_CANDIDATE_SYNTAX"],
            evidence=[],
            abstained=True,
            d_checkable=False,
            eligibility_reason="candidate_syntax_not_fully_parsed",
        )
    active_events, contextual_events = partition_contextual_events(messages, events)
    decisive = block_evidence(active_events)
    if decisive:
        evidence = [asdict(item) for item in decisive]
        if not all(valid_evidence_anchor(item) for item in evidence):
            return VerificationDecision(
                decision="review",
                score=0.5,
                check_ids=["EVIDENCE_SCHEMA_FAILURE"],
                evidence=[],
                abstained=True,
                d_checkable=False,
                eligibility_reason="internal_evidence_schema_failure",
            )
        return VerificationDecision(
            decision="block",
            score=1.0,
            check_ids=sorted({item.check_id for item in decisive}),
            evidence=evidence,
            abstained=False,
        )

    if contextual_events:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=["HYPOTHETICAL_OR_NEGATED_MUTATION"],
            evidence=[],
            abstained=True,
            eligibility_reason="complete_but_semantically_nondecisive_transcript",
        )

    target_review_ids = target_review_check_ids(active_events)
    if target_review_ids:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=target_review_ids,
            evidence=[],
            abstained=True,
            eligibility_reason="complete_but_target_context_ambiguous",
        )

    review_ids = semantic_review_check_ids(assistant_response_text(messages))
    if review_ids:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=review_ids,
            evidence=[],
            abstained=True,
        )

    return VerificationDecision(
        decision="allow",
        score=0.0,
        check_ids=[],
        evidence=[],
        abstained=False,
    )


def verify_trace_row(row: Mapping[str, Any]) -> VerificationDecision:
    """Compatibility entry point that blinds gold metadata before inference."""

    try:
        blinded = blind_trace_row(row)
    except TraceDataError:
        return VerificationDecision(
            decision="review",
            score=0.5,
            check_ids=["TRANSCRIPT_PARSE_FAILURE"],
            evidence=[],
            abstained=True,
            d_checkable=False,
            eligibility_reason="transcript_parse_failure",
            parse_failure=True,
        )
    return verify_blinded_row(blinded)
