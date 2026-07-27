#!/usr/bin/env python
"""Pure mechanics for the repaired PX-057 H5 stopping rule.

H5 separates answer validity from transport diagnostics:

* Every ``Final answer`` marker is parsed.  The answer for a generation is the
  last marker, scanning backwards, that contains a valid numeric value or an
  in-vocabulary choice label.
* Token-cap and repeated-answer flags are deterministic evidence fields.  They
  do not, by themselves, invalidate an otherwise valid answer.
* A stability window qualifies only when every answer in it is explicitly
  valid and nonempty.
* When stability never qualifies, the fixed-long decision charges the final
  round's cumulative compute.  If requested, an invalid final round may use
  the latest earlier valid answer without pretending that its earlier compute
  was the fixed-long cost.

The module deliberately has no model, dataset, gold-label, filesystem, or H4
dependencies so that the scientific rule can be tested and independently
replayed.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal, Sequence


AnswerType = Literal["numeric", "choice"]

FINAL_ANSWER_MARKER = re.compile(
    r"final\s+answer\s*(?:is|:|=)?",
    flags=re.IGNORECASE,
)
NUMERIC_CANDIDATE = re.compile(
    r"\s*([-+]?(?:\d[\d,]*\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)"
)
CHOICE_CANDIDATE = re.compile(r"\s*\(?([A-Za-z0-9]+)\)?")


@dataclass(frozen=True)
class AnswerCandidate:
    """One candidate parsed immediately after a ``Final answer`` marker."""

    marker_ordinal: int
    marker_start: int
    marker_end: int
    raw_value: str
    normalized_answer: str
    valid: bool


@dataclass(frozen=True)
class ExtractionResult:
    """Outcome-independent extraction and generation-anomaly evidence."""

    answer: str
    valid: bool
    selected_marker_ordinal: int | None
    candidates: tuple[AnswerCandidate, ...]
    token_cap_reached: bool
    repetition_detected: bool
    maximum_consecutive_valid_answer_run: int
    repetition_min_run: int

    @property
    def marker_count(self) -> int:
        return len(self.candidates)

    @property
    def used_prior_valid_marker(self) -> bool:
        """Whether a later marker was skipped because it was invalid."""

        return (
            self.selected_marker_ordinal is not None
            and self.selected_marker_ordinal != self.marker_count
        )


@dataclass(frozen=True)
class StoppingStep:
    """One round as seen by the H5 stopping rule.

    ``token_cap_reached`` and ``repetition_detected`` are retained for audit
    and subgroup reporting.  The selector intentionally does not treat either
    flag as invalidity; validity is represented only by ``answer_valid``.
    """

    round_index: int
    answer: str
    answer_valid: bool
    confidence: float
    cumulative_tokens: int
    token_cap_reached: bool = False
    repetition_detected: bool = False

    def __post_init__(self) -> None:
        if self.round_index < 1:
            raise ValueError("round_index must be >= 1")
        if self.cumulative_tokens < 0:
            raise ValueError("cumulative_tokens must be >= 0")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be finite and within [0, 1]")
        if self.answer_valid and not normalize_stability_answer(self.answer):
            raise ValueError("a valid answer must be nonempty after normalization")


@dataclass(frozen=True)
class FixedLongDecision:
    """Fixed-long answer identity separated from its full compute charge."""

    answer: str
    answer_valid: bool
    answer_round: int | None
    compute_round: int
    charged_tokens: int
    used_latest_valid_fallback: bool


@dataclass(frozen=True)
class StopDecision:
    """Result of applying the H5 stability rule to one complete trace."""

    answer: str
    answer_valid: bool
    answer_round: int | None
    compute_round: int
    charged_tokens: int
    stability_triggered: bool
    stopped_early: bool
    used_latest_valid_fallback: bool


def normalize_numeric_answer(value: str) -> str:
    """Normalize a numeric candidate using the frozen PX-057 convention."""

    value = value.replace(",", "").strip()
    try:
        number = float(value)
    except ValueError:
        return value.casefold()
    if number.is_integer():
        return str(int(number))
    return f"{number:.10g}"


def normalize_stability_answer(value: str) -> str:
    """Canonical form used only for equality inside a stability window."""

    return re.sub(r"\s+", " ", value.strip()).casefold()


def _parse_candidate(
    text: str,
    *,
    marker: re.Match[str],
    marker_ordinal: int,
    answer_type: AnswerType,
    allowed_labels: frozenset[str],
) -> AnswerCandidate:
    suffix = text[marker.end() :]
    if answer_type == "numeric":
        match = NUMERIC_CANDIDATE.match(suffix)
        raw_value = "" if match is None else match.group(1)
        normalized = "" if match is None else normalize_numeric_answer(raw_value)
        valid = bool(normalized)
    else:
        match = CHOICE_CANDIDATE.match(suffix)
        raw_value = "" if match is None else match.group(1)
        normalized = raw_value.strip().upper()
        valid = bool(normalized) and normalized in allowed_labels
        if not valid:
            normalized = ""
    return AnswerCandidate(
        marker_ordinal=marker_ordinal,
        marker_start=marker.start(),
        marker_end=marker.end(),
        raw_value=raw_value,
        normalized_answer=normalized,
        valid=valid,
    )


def _maximum_consecutive_valid_answer_run(
    candidates: Sequence[AnswerCandidate],
) -> int:
    maximum = 0
    current_answer: str | None = None
    current_run = 0
    for candidate in candidates:
        if not candidate.valid:
            current_answer = None
            current_run = 0
            continue
        answer = normalize_stability_answer(candidate.normalized_answer)
        if answer == current_answer:
            current_run += 1
        else:
            current_answer = answer
            current_run = 1
        maximum = max(maximum, current_run)
    return maximum


def extract_last_valid_answer(
    text: str,
    *,
    answer_type: AnswerType,
    allowed_labels: Sequence[str] = (),
    generated_tokens: int | None = None,
    max_new_tokens: int | None = None,
    repetition_min_run: int = 3,
) -> ExtractionResult:
    """Extract the last valid marked answer and deterministic anomaly flags.

    Repetition is defined as at least ``repetition_min_run`` consecutive valid
    ``Final answer`` candidates with the same normalized value.  An invalid
    marker breaks a run.  The token-cap flag is true when the observed number
    of generated tokens is greater than or equal to the configured cap.

    Neither flag changes ``valid``.  For example, a capped response ending in
    ``Final answer: B`` remains a valid response and may participate in a
    stability window.
    """

    if answer_type not in {"numeric", "choice"}:
        raise ValueError(f"unsupported answer_type: {answer_type}")
    if repetition_min_run < 2:
        raise ValueError("repetition_min_run must be >= 2")
    if (generated_tokens is None) != (max_new_tokens is None):
        raise ValueError(
            "generated_tokens and max_new_tokens must be supplied together"
        )
    if generated_tokens is not None and generated_tokens < 0:
        raise ValueError("generated_tokens must be >= 0")
    if max_new_tokens is not None and max_new_tokens < 1:
        raise ValueError("max_new_tokens must be >= 1")

    normalized_labels = frozenset(
        str(label).strip().upper() for label in allowed_labels if str(label).strip()
    )
    if answer_type == "choice" and not normalized_labels:
        raise ValueError("choice extraction requires nonempty allowed_labels")

    markers = tuple(FINAL_ANSWER_MARKER.finditer(text))
    candidates = tuple(
        _parse_candidate(
            text,
            marker=marker,
            marker_ordinal=index,
            answer_type=answer_type,
            allowed_labels=normalized_labels,
        )
        for index, marker in enumerate(markers, 1)
    )
    selected = next(
        (candidate for candidate in reversed(candidates) if candidate.valid),
        None,
    )
    maximum_run = _maximum_consecutive_valid_answer_run(candidates)
    token_cap_reached = (
        generated_tokens is not None
        and max_new_tokens is not None
        and generated_tokens >= max_new_tokens
    )
    return ExtractionResult(
        answer="" if selected is None else selected.normalized_answer,
        valid=selected is not None,
        selected_marker_ordinal=(
            None if selected is None else selected.marker_ordinal
        ),
        candidates=candidates,
        token_cap_reached=token_cap_reached,
        repetition_detected=maximum_run >= repetition_min_run,
        maximum_consecutive_valid_answer_run=maximum_run,
        repetition_min_run=repetition_min_run,
    )


def stopping_step_from_extraction(
    *,
    round_index: int,
    extraction: ExtractionResult,
    confidence: float,
    cumulative_tokens: int,
) -> StoppingStep:
    """Create a selector step without allowing diagnostics to alter validity."""

    return StoppingStep(
        round_index=round_index,
        answer=extraction.answer,
        answer_valid=extraction.valid,
        confidence=confidence,
        cumulative_tokens=cumulative_tokens,
        token_cap_reached=extraction.token_cap_reached,
        repetition_detected=extraction.repetition_detected,
    )


def _validate_steps(steps: Sequence[StoppingStep]) -> tuple[StoppingStep, ...]:
    frozen = tuple(steps)
    if not frozen:
        raise ValueError("at least one stopping step is required")
    rounds = [step.round_index for step in frozen]
    if any(current != previous + 1 for previous, current in zip(rounds, rounds[1:])):
        raise ValueError("round indices must be strictly consecutive")
    tokens = [step.cumulative_tokens for step in frozen]
    if any(current < previous for previous, current in zip(tokens, tokens[1:])):
        raise ValueError("cumulative_tokens must be nondecreasing")
    return frozen


def stability_window_qualifies(
    window: Sequence[StoppingStep],
    *,
    confidence_threshold: float | None,
) -> bool:
    """Return true only for a nonempty, validity-gated stable window."""

    frozen = tuple(window)
    if not frozen:
        return False
    normalized = [normalize_stability_answer(step.answer) for step in frozen]
    valid_and_nonempty = all(
        step.answer_valid and bool(answer)
        for step, answer in zip(frozen, normalized)
    )
    if not valid_and_nonempty or len(set(normalized)) != 1:
        return False
    if confidence_threshold is None:
        return True
    if not math.isfinite(
        confidence_threshold
    ) or not 0.0 <= confidence_threshold <= 1.0:
        raise ValueError("confidence_threshold must be within [0, 1] or None")
    return all(step.confidence >= confidence_threshold for step in frozen)


def fixed_long_decision(
    steps: Sequence[StoppingStep],
    *,
    fallback_to_latest_valid: bool = True,
) -> FixedLongDecision:
    """Choose the fixed-long answer while always charging final-round compute."""

    frozen = _validate_steps(steps)
    compute_step = frozen[-1]
    answer_step: StoppingStep | None
    if compute_step.answer_valid and normalize_stability_answer(compute_step.answer):
        answer_step = compute_step
    elif fallback_to_latest_valid:
        answer_step = next(
            (
                step
                for step in reversed(frozen[:-1])
                if step.answer_valid and normalize_stability_answer(step.answer)
            ),
            None,
        )
    else:
        answer_step = None
    return FixedLongDecision(
        answer="" if answer_step is None else answer_step.answer,
        answer_valid=answer_step is not None,
        answer_round=None if answer_step is None else answer_step.round_index,
        compute_round=compute_step.round_index,
        charged_tokens=compute_step.cumulative_tokens,
        used_latest_valid_fallback=(
            answer_step is not None and answer_step is not compute_step
        ),
    )


def select_stability_stop(
    steps: Sequence[StoppingStep],
    *,
    min_step: int,
    patience: int,
    confidence_threshold: float | None,
    fallback_to_latest_valid: bool = True,
) -> StopDecision:
    """Apply the validity-gated H5 stopping policy to a complete trace.

    ``confidence_threshold=None`` disables the confidence condition.  If no
    stability window qualifies, the result delegates to
    :func:`fixed_long_decision`, preserving the full final-round token charge.
    """

    frozen = _validate_steps(steps)
    if min_step < 1:
        raise ValueError("min_step must be >= 1")
    if patience < 1:
        raise ValueError("patience must be >= 1")
    if confidence_threshold is not None and (
        not math.isfinite(confidence_threshold)
        or not 0.0 <= confidence_threshold <= 1.0
    ):
        raise ValueError("confidence_threshold must be within [0, 1] or None")

    for index, current in enumerate(frozen):
        if current.round_index < min_step or index + 1 < patience:
            continue
        window = frozen[index + 1 - patience : index + 1]
        if stability_window_qualifies(
            window,
            confidence_threshold=confidence_threshold,
        ):
            return StopDecision(
                answer=current.answer,
                answer_valid=True,
                answer_round=current.round_index,
                compute_round=current.round_index,
                charged_tokens=current.cumulative_tokens,
                stability_triggered=True,
                stopped_early=index < len(frozen) - 1,
                used_latest_valid_fallback=False,
            )

    fixed_long = fixed_long_decision(
        frozen,
        fallback_to_latest_valid=fallback_to_latest_valid,
    )
    return StopDecision(
        answer=fixed_long.answer,
        answer_valid=fixed_long.answer_valid,
        answer_round=fixed_long.answer_round,
        compute_round=fixed_long.compute_round,
        charged_tokens=fixed_long.charged_tokens,
        stability_triggered=False,
        stopped_early=False,
        used_latest_valid_fallback=fixed_long.used_latest_valid_fallback,
    )
