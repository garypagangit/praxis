"""Class-conditional Neyman-Pearson tolerance calibration for a frozen gate.

Larger finite scores mean more benign. Only eligible alerts with score strictly
above the threshold are suppressed. Statistical validity requires independent,
identically distributed attack calibration units, correct labels, and a scorer
and eligibility predicate fixed independently of those units. This module cannot
verify those scientific assumptions or confer an adversarial/drift guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from numbers import Integral, Real
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import binom


SCHEMA = "cert-gate-order-statistic-v1"
CALIBRATED = "CALIBRATED"
KEEP_ALL = "KEEP_ALL_INSUFFICIENT_ATTACKS"


def _probability(value: Any, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite number strictly between 0 and 1")
    value = float(value)
    if not np.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError(f"{name} must be a finite number strictly between 0 and 1")
    return value


def _count(value: Any, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return int(value)


def _inputs(scores: Sequence[float], eligible: Sequence[bool] | None) -> tuple[np.ndarray, np.ndarray]:
    raw = np.asarray(scores)
    if raw.ndim != 1 or raw.dtype.kind not in "fiu":
        raise ValueError("scores must be a one-dimensional array of finite real numbers")
    values = raw.astype(np.float64, copy=True)
    if not np.all(np.isfinite(values)):
        raise ValueError("nonfinite scores are invalid, including on ineligible examples")
    if eligible is None:
        mask = np.ones(len(values), dtype=bool)
    else:
        mask = np.asarray(eligible)
        if mask.ndim != 1 or len(mask) != len(values) or (mask.size and mask.dtype.kind != "b"):
            raise ValueError("eligible must be a boolean array with the same length as scores")
        mask = mask.astype(bool, copy=True)
    return values, mask


def tolerance_rank(n: int, alpha: float = 0.01, delta: float = 0.05) -> int | None:
    """Smallest valid one-based ascending rank; None means deterministic keep-all.

    For rank k, P(R > alpha) <= BinomCDF(n-k; n, alpha). The rank depends
    only on n/alpha/delta, so there is no search over observed score values.
    """
    n = _count(n, "n")
    alpha, delta = _probability(alpha, "alpha"), _probability(delta, "delta")
    if n == 0 or float(binom.cdf(0, n, alpha)) > delta:
        return None
    # Find the largest permitted number of calibration exceedances. The CDF
    # is monotone, and comparisons deliberately have no permissive epsilon.
    low, high = 0, n - 1
    while low < high:
        mid = (low + high + 1) // 2
        if float(binom.cdf(mid, n, alpha)) <= delta:
            low = mid
        else:
            high = mid - 1
    return n - low


def _metadata_json(metadata: Mapping[str, Any] | None) -> str:
    if metadata is None:
        return "{}"
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be a JSON object")
    try:
        return json.dumps(dict(metadata), sort_keys=True, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise ValueError("metadata must contain only JSON-safe values") from exc


@dataclass(frozen=True)
class Certificate:
    alpha: float
    delta: float
    n_attack: int
    n_eligible_attack: int
    allowed_exceedances: int | None
    order_rank: int | None
    observed_exceedances: int
    violation_bound: float
    mode: str
    threshold_kind: str
    threshold_value: float | None
    metadata_json: str = "{}"

    def __post_init__(self) -> None:
        alpha, delta = _probability(self.alpha, "alpha"), _probability(self.delta, "delta")
        n = _count(self.n_attack, "n_attack")
        n_eligible = _count(self.n_eligible_attack, "n_eligible_attack")
        observed = _count(self.observed_exceedances, "observed_exceedances")
        if n_eligible > n or observed > n_eligible:
            raise ValueError("inconsistent calibration counts")
        try:
            decoded_metadata = json.loads(self.metadata_json)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid metadata_json") from exc
        if not isinstance(decoded_metadata, dict):
            raise ValueError("metadata_json must encode an object")
        _metadata_json(decoded_metadata)
        rank = tolerance_rank(n, alpha, delta)
        if self.mode == KEEP_ALL:
            if rank is not None or self.allowed_exceedances is not None or self.order_rank is not None:
                raise ValueError("keep-all insufficient-data certificate has inconsistent rank")
            if observed != 0 or self.violation_bound != 0.0 or self.threshold_kind != "positive_infinity" or self.threshold_value is not None:
                raise ValueError("invalid keep-all threshold or counts")
        elif self.mode == CALIBRATED:
            if rank is None or _count(self.order_rank, "order_rank") != rank:
                raise ValueError("invalid calibrated order rank")
            if _count(self.allowed_exceedances, "allowed_exceedances") != n - rank or observed > n - rank:
                raise ValueError("invalid permitted or observed exceedances")
            bound = float(binom.cdf(n - rank, n, alpha))
            if self.violation_bound != bound or not 0 <= self.violation_bound <= delta:
                raise ValueError("invalid binomial violation bound")
            if self.threshold_kind == "negative_infinity":
                if self.threshold_value is not None or observed != n_eligible:
                    raise ValueError("invalid ineligible-score threshold")
            elif self.threshold_kind == "finite":
                # There are n-n_eligible initial -inf values in the ordering.
                # The selected rank can be finite only if it lies after them.
                if isinstance(self.threshold_value, (bool, np.bool_)) or not isinstance(self.threshold_value, Real) or not np.isfinite(self.threshold_value) or n_eligible <= n - rank:
                    raise ValueError("invalid finite threshold")
            else:
                raise ValueError("invalid calibrated threshold kind")
        else:
            raise ValueError("unknown certificate mode")

    @property
    def metadata(self) -> dict[str, Any]:
        """A detached copy; caller mutation cannot change this certificate."""
        return json.loads(self.metadata_json)

    @property
    def threshold(self) -> float:
        if self.threshold_kind == "positive_infinity":
            return float("inf")
        if self.threshold_kind == "negative_infinity":
            return float("-inf")
        return float(self.threshold_value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SCHEMA,
            "scope": "PER_FIXED_SCORER_AND_ELIGIBILITY",
            "comparison": "strict_greater_than",
            "alpha": self.alpha, "delta": self.delta,
            "n_attack": self.n_attack, "n_eligible_attack": self.n_eligible_attack,
            "allowed_exceedances": self.allowed_exceedances,
            "order_rank": self.order_rank,
            "observed_exceedances": self.observed_exceedances,
            "violation_bound": self.violation_bound, "mode": self.mode,
            "threshold": {"kind": self.threshold_kind, "value": self.threshold_value},
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "Certificate":
        expected = {"schema", "scope", "comparison", "alpha", "delta", "n_attack", "n_eligible_attack", "allowed_exceedances", "order_rank", "observed_exceedances", "violation_bound", "mode", "threshold", "metadata"}
        if not isinstance(document, Mapping) or set(document) != expected:
            raise ValueError("certificate fields do not match the schema")
        if document["schema"] != SCHEMA or document["scope"] != "PER_FIXED_SCORER_AND_ELIGIBILITY" or document["comparison"] != "strict_greater_than":
            raise ValueError("unsupported certificate contract")
        threshold = document["threshold"]
        if not isinstance(threshold, Mapping) or set(threshold) != {"kind", "value"}:
            raise ValueError("invalid threshold encoding")
        return cls(
            alpha=document["alpha"], delta=document["delta"],
            n_attack=document["n_attack"], n_eligible_attack=document["n_eligible_attack"],
            allowed_exceedances=document["allowed_exceedances"], order_rank=document["order_rank"],
            observed_exceedances=document["observed_exceedances"], violation_bound=document["violation_bound"],
            mode=document["mode"], threshold_kind=threshold["kind"], threshold_value=threshold["value"],
            metadata_json=_metadata_json(document["metadata"]),
        )


def calibrate(
    attack_scores: Sequence[float], eligible: Sequence[bool] | None = None,
    alpha: float = 0.01, delta: float = 0.05,
    metadata: Mapping[str, Any] | None = None,
) -> Certificate:
    """Calibrate on ALL attack units, including ineligible ones; no model fitting.

    Input scores must be finite even where eligible=False. There is deliberately
    no scorer-selection interface and no automatic guarantee across certificates.
    """
    scores, mask = _inputs(attack_scores, eligible)
    alpha, delta = _probability(alpha, "alpha"), _probability(delta, "delta")
    n, n_eligible = len(scores), int(mask.sum())
    rank = tolerance_rank(n, alpha, delta)
    metadata_text = _metadata_json(metadata)
    if rank is None:
        return Certificate(alpha, delta, n, n_eligible, None, None, 0, 0.0, KEEP_ALL, "positive_infinity", None, metadata_text)
    effective = np.where(mask, scores, -np.inf)
    threshold = float(np.partition(effective, rank - 1)[rank - 1])
    negative_infinity = bool(np.isneginf(threshold))
    return Certificate(
        alpha, delta, n, n_eligible, n - rank, rank,
        int(np.count_nonzero(mask & (scores > threshold))),
        float(binom.cdf(n - rank, n, alpha)), CALIBRATED,
        "negative_infinity" if negative_infinity else "finite",
        None if negative_infinity else threshold, metadata_text,
    )


def apply_certificate(
    certificate: Certificate | Mapping[str, Any], scores: Sequence[float],
    eligible: Sequence[bool] | None = None,
) -> np.ndarray:
    """Return True only for suppression; reject invalid inputs before deciding.

    A caller handling a validation exception must retain the affected alerts.
    Apply the same frozen scorer and eligibility definition used for calibration.
    """
    if not isinstance(certificate, Certificate):
        certificate = Certificate.from_dict(certificate)
    values, mask = _inputs(scores, eligible)
    if certificate.mode == KEEP_ALL:
        return np.zeros(len(values), dtype=bool)
    return mask & (values > certificate.threshold)


def gate_decision(certificate: Certificate | Mapping[str, Any], score: float, eligible: bool = True) -> bool:
    """Scalar version of apply_certificate; True means suppress this alert."""
    return bool(apply_certificate(certificate, [score], [eligible])[0])
