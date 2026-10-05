"""Split-conformal abstention gate (Mondrian / class-conditional).

The classifier produces calibrated probabilities p̂(y|x).  The gate converts
them into prediction *sets* with a marginal coverage guarantee, and emits a
decision only when the set is a singleton.  Everything else abstains.

Guarantee (under exchangeability of calibration and test):
    P(y_true ∉ set(x)) ≤ α  , per class when class-conditional.

The threshold q is fixed from calibration data BEFORE any test point is seen
and is never adapted online — that fixed, pre-committed threshold is the
deterministic component the praxis argument rests on.
"""
from __future__ import annotations

import math
import numpy as np


class ConformalGate:
    def __init__(self, alpha: float = 0.05, class_conditional: bool = True):
        self.alpha = alpha
        self.class_conditional = class_conditional
        self.classes_: list = []
        self.q_: dict = {}      # class -> threshold on nonconformity
        self.q_global_: float = 1.0

    def _nonconf(self, proba, class_index):
        # nonconformity for the TRUE class = 1 - p̂(true)
        return 1.0 - proba[:, class_index]

    def calibrate(self, proba_cal: np.ndarray, y_cal, classes: list):
        self.classes_ = list(classes)
        idx = {c: i for i, c in enumerate(self.classes_)}
        y_cal = np.asarray(y_cal)
        if self.class_conditional:
            for c in self.classes_:
                mask = y_cal == c
                if mask.sum() == 0:
                    self.q_[c] = 1.0
                    continue
                scores = 1.0 - proba_cal[mask, idx[c]]
                self.q_[c] = self._quantile(scores, self.alpha)
        else:
            scores = np.array([1.0 - proba_cal[i, idx[y]] for i, y in enumerate(y_cal)])
            self.q_global_ = self._quantile(scores, self.alpha)
        return self

    @staticmethod
    def _quantile(scores: np.ndarray, alpha: float) -> float:
        n = len(scores)
        if n == 0:
            return 1.0
        # conformal quantile level with finite-sample correction
        level = min(1.0, math.ceil((n + 1) * (1 - alpha)) / n)
        return float(np.quantile(scores, level, method="higher"))

    def prediction_sets(self, proba: np.ndarray) -> list[list]:
        idx = {c: i for i, c in enumerate(self.classes_)}
        sets = []
        for row in proba:
            s = []
            for c in self.classes_:
                thr = self.q_[c] if self.class_conditional else self.q_global_
                if (1.0 - row[idx[c]]) <= thr:
                    s.append(c)
            sets.append(s)
        return sets

    def decide(self, proba: np.ndarray):
        """Return (labels, decided_mask).  Emit a label only on singletons."""
        sets = self.prediction_sets(proba)
        labels, decided = [], []
        for s in sets:
            if len(s) == 1:
                labels.append(s[0]); decided.append(True)
            else:
                labels.append(None); decided.append(False)
        return labels, np.array(decided)


def clopper_pearson_upper(k: int, n: int, conf: float = 0.95) -> float:
    """Upper bound of a binomial proportion (one-sided), for decided-error."""
    if n == 0:
        return 1.0
    if k == n:
        return 1.0
    from scipy.stats import beta
    return float(beta.ppf(conf, k + 1, n - k))


def gate_report(gate: ConformalGate, proba: np.ndarray, y_true) -> dict:
    labels, decided = gate.decide(proba)
    y_true = np.asarray(y_true)
    n = len(y_true)
    n_dec = int(decided.sum())
    coverage = n_dec / n if n else 0.0
    errs = sum(1 for i in range(n) if decided[i] and labels[i] != y_true[i])
    err_rate = errs / n_dec if n_dec else 0.0
    sets = gate.prediction_sets(proba)
    set_coverage = sum(1 for i in range(n) if y_true[i] in sets[i]) / n if n else 0.0
    return {
        "alpha": gate.alpha,
        "n": n,
        "n_decided": n_dec,
        "coverage": round(coverage, 4),
        "decided_error": round(err_rate, 4),
        "decided_error_cp_upper95": round(clopper_pearson_upper(errs, n_dec), 4),
        "set_coverage_empirical": round(set_coverage, 4),  # should be ≥ 1-alpha
        "mean_set_size": round(float(np.mean([len(s) for s in sets])), 3) if n else 0.0,
    }
