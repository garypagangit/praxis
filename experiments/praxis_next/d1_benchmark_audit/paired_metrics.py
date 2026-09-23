"""Native-label stage metrics and paired, source-group bootstrap comparisons.

No model fitting, stage remapping, threshold choice or data acquisition occurs
here. Undefined rates are None. See METRIC_SPEC.md for the fixed-label macro-F1
and support-conditional bootstrap definitions.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping, Sequence

import numpy as np

Label = str | int


def _scalar(value, field: str) -> Label:
    if isinstance(value, np.integer) and not isinstance(value, np.bool_):
        value = int(value)
    if isinstance(value, np.str_):
        value = str(value)
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError(f"{field} must contain non-null string or integer identifiers")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{field} contains an empty identifier")
    return value


def _values(values, field: str) -> tuple[Label, ...]:
    if values is None or isinstance(values, (str, bytes)):
        raise ValueError(f"{field} must be an explicit sequence")
    try:
        return tuple(_scalar(v, field) for v in values)
    except TypeError as exc:
        raise ValueError(f"{field} must be a one-dimensional sequence") from exc


@dataclass(frozen=True)
class LabelSchema:
    """Explicit native-ID meanings; benign_label has no inferred default."""

    label_names: Mapping[Label, str]
    benign_label: Label

    def validated(self) -> dict[Label, str]:
        if not isinstance(self.label_names, Mapping) or len(self.label_names) < 2:
            raise ValueError("Declare benign and at least one attack-stage label")
        names = {_scalar(k, "native labels"): v for k, v in self.label_names.items()}
        if any(not isinstance(v, str) or not v.strip() for v in names.values()):
            raise ValueError("Each native label needs a nonempty meaning")
        if len(set(names.values())) != len(names):
            raise ValueError("Native label meanings must be unique")
        benign = _scalar(self.benign_label, "benign_label")
        if benign not in names:
            raise ValueError("Explicit benign_label is absent from the native schema")
        return names


@dataclass(frozen=True)
class PredictionBatch:
    row_ids: Sequence[Label]
    y_true: Sequence[Label]
    y_pred: Sequence[Label]
    schema: LabelSchema
    group_ids: Sequence[Label] | None = None


@dataclass(frozen=True)
class GroupBootstrapPlan:
    """Reusable paired draws, bound to ordered row IDs and real source groups."""

    row_ids: tuple[Label, ...]
    group_ids: tuple[Label, ...]
    group_unit: str
    draws: tuple[tuple[Label, ...], ...]
    seed: int


def _validate_batch(batch: PredictionBatch):
    names = batch.schema.validated()
    rows = _values(batch.row_ids, "row_ids")
    truth = _values(batch.y_true, "y_true")
    pred = _values(batch.y_pred, "y_pred")
    if not rows or len(rows) != len(truth) or len(rows) != len(pred):
        raise ValueError("Nonempty row_ids, y_true and y_pred must have equal lengths")
    if len(set(rows)) != len(rows):
        raise ValueError("row_ids must be unique before resampling")
    if set(truth) - names.keys() or set(pred) - names.keys():
        raise ValueError("Truth/prediction labels are outside the declared native schema")
    groups = None if batch.group_ids is None else _values(batch.group_ids, "group_ids")
    if groups is not None and len(groups) != len(rows):
        raise ValueError("Every row must have exactly one declared group")
    return rows, truth, pred, names, groups


def stage_metrics(y_true, y_pred, *, schema: LabelSchema) -> dict:
    """Metrics on native multiclass decisions; no silent label conversions."""
    names = schema.validated()
    truth = _values(y_true, "y_true")
    pred = _values(y_pred, "y_pred")
    if not truth or len(truth) != len(pred):
        raise ValueError("Nonempty truth and prediction arrays must have equal lengths")
    if set(truth) - names.keys() or set(pred) - names.keys():
        raise ValueError("Truth/prediction labels are outside the declared native schema")
    order = list(names)
    index = {label: i for i, label in enumerate(order)}
    yt = np.asarray([index[x] for x in truth], dtype=np.int64)
    yp = np.asarray([index[x] for x in pred], dtype=np.int64)
    cm = np.zeros((len(order), len(order)), dtype=np.int64)
    np.add.at(cm, (yt, yp), 1)
    return _metrics_from_confusion(cm, names, schema.benign_label)


def _metrics_from_confusion(cm, names, benign_label):
    """Count sufficient statistics also support exact weighted group repeats."""
    benign_label = _scalar(benign_label, "benign_label")
    order = list(names)
    support, predicted = cm.sum(axis=1), cm.sum(axis=0)
    benign = order.index(benign_label)
    classes, stages = {}, {}
    for i, native_label in enumerate(order):
        n, called, tp = int(support[i]), int(predicted[i]), int(cm[i, i])
        item = {
            "native_label": native_label,
            "support": n,
            "predicted_count": called,
            "correct_count": tp,
            "exact_stage_recall": tp / n if n else None,
            "precision": tp / called if called else None,
            # Unsupported true stages remain undefined, even if predicted.
            "f1": 2 * tp / (n + called) if n else None,
        }
        classes[names[native_label]] = item
        if i != benign:
            missed = int(cm[i, benign])
            wrong_stage = n - missed - tp
            stages[names[native_label]] = {
                **item,
                "warning_count": n - missed,
                "warning_recall": (n - missed) / n if n else None,
                "attack_to_benign_count": missed,
                "wrong_attack_stage_count": wrong_stage,
            }
    benign_n = int(support[benign])
    false_alerts = benign_n - int(cm[benign, benign])
    unsupported = [name for name, value in classes.items() if value["support"] == 0]
    # Fixed-schema macro-F1 is undefined if a declared class is unsupported.
    macro = None if unsupported else float(np.mean([v["f1"] for v in classes.values()]))
    return {
        "rows": int(cm.sum()),
        "label_order": order,
        "label_mapping": [{"native_label": label, "name": name} for label, name in names.items()],
        "benign_label": benign_label,
        "confusion": cm.tolist(),
        "macro_f1": macro,
        "macro_f1_unsupported_classes": unsupported,
        "classes": classes,
        "stages": stages,
        "attack_to_benign_count": sum(v["attack_to_benign_count"] for v in stages.values()),
        "wrong_attack_stage_count": sum(v["wrong_attack_stage_count"] for v in stages.values()),
        "benign_support": benign_n,
        "benign_false_alert_count": false_alerts,
        "benign_false_alert_rate": false_alerts / benign_n if benign_n else None,
    }


def resample_group_indices(group_ids, sampled_groups) -> np.ndarray:
    """Concatenate whole source groups; repeated draws repeat their rows."""
    groups = _values(group_ids, "group_ids")
    draws = _values(sampled_groups, "sampled_groups")
    if not groups or not draws:
        raise ValueError("Groups and draws must be nonempty")
    positions: dict[Label, list[int]] = {}
    for i, group in enumerate(groups):
        positions.setdefault(group, []).append(i)
    if set(draws) - positions.keys():
        raise ValueError("Bootstrap draw contains an undeclared source group")
    return np.asarray([i for group in draws for i in positions[group]], dtype=np.int64)


def make_group_bootstrap_plan(row_ids, group_ids, *, group_unit: str,
                              n_resamples: int = 1000, seed: int = 0) -> GroupBootstrapPlan:
    """Draw G declared source groups with replacement in each replicate."""
    rows, groups = _values(row_ids, "row_ids"), _values(group_ids, "group_ids")
    if not rows or len(rows) != len(groups) or len(set(rows)) != len(rows):
        raise ValueError("Unique row IDs and group IDs must align")
    if not isinstance(group_unit, str) or not group_unit.strip():
        raise ValueError("Declare the source's actual grouping unit")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int) or n_resamples < 2:
        raise ValueError("n_resamples must be an integer of at least two")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    unique = list(dict.fromkeys(groups))
    if len(unique) < 2:
        raise ValueError("At least two declared source groups are required for a group interval")
    choices = np.random.default_rng(seed).integers(len(unique), size=(n_resamples, len(unique)))
    draws = tuple(tuple(unique[i] for i in replicate) for replicate in choices)
    return GroupBootstrapPlan(rows, groups, group_unit, draws, seed)


def _subtract(a, b):
    return None if a is None or b is None else float(a - b)


def _deltas(baseline: dict, candidate: dict) -> dict:
    macro = _subtract(candidate["macro_f1"], baseline["macro_f1"])
    per_stage = {}
    for name, before in baseline["stages"].items():
        after = candidate["stages"][name]
        warning = _subtract(after["warning_recall"], before["warning_recall"])
        defined = macro is not None and warning is not None
        up_down = None if not defined else bool(macro > 1e-12 and warning < -1e-12)
        down_up = None if not defined else bool(macro < -1e-12 and warning > 1e-12)
        per_stage[name] = {
            "delta_exact_stage_recall": _subtract(after["exact_stage_recall"], before["exact_stage_recall"]),
            "delta_warning_recall": warning,
            "delta_stage_f1": _subtract(after["f1"], before["f1"]),
            "delta_attack_to_benign_count": after["attack_to_benign_count"] - before["attack_to_benign_count"],
            "delta_wrong_attack_stage_count": after["wrong_attack_stage_count"] - before["wrong_attack_stage_count"],
            "macro_f1_up_warning_down": up_down,
            "macro_f1_down_warning_up": down_up,
            "macro_f1_warning_sign_reversal": None if not defined else up_down or down_up,
        }
    return {
        "delta_macro_f1": macro,
        "delta_benign_false_alert_rate": _subtract(candidate["benign_false_alert_rate"], baseline["benign_false_alert_rate"]),
        "delta_attack_to_benign_count": candidate["attack_to_benign_count"] - baseline["attack_to_benign_count"],
        "delta_wrong_attack_stage_count": candidate["wrong_attack_stage_count"] - baseline["wrong_attack_stage_count"],
        "stages": per_stage,
    }


def _interval(values, confidence):
    valid = [v for v in values if v is not None]
    enough = len(valid) >= 2
    bounds = np.quantile(valid, [(1 - confidence) / 2, (1 + confidence) / 2], method="linear") if enough else [None, None]
    return {
        "lower": float(bounds[0]) if enough else None,
        "upper": float(bounds[1]) if enough else None,
        "confidence": confidence,
        "valid_replicates": len(valid),
        "undefined_replicates": len(values) - len(valid),
        "conditional_on_required_label_support": len(valid) < len(values),
        "status": "SUPPORT_CONDITIONAL" if enough and len(valid) < len(values) else "COMPLETE" if enough else "INSUFFICIENT_DEFINED_REPLICATES",
    }


def paired_comparison(baseline: PredictionBatch, candidate: PredictionBatch, *,
                      bootstrap: GroupBootstrapPlan | None = None,
                      confidence: float = .95, include_replicates: bool = False) -> dict:
    """Candidate-minus-baseline metrics; both methods use identical group draws."""
    a, b = _validate_batch(baseline), _validate_batch(candidate)
    rows, truth, pred_a, names, groups = a
    if names != b[3] or baseline.schema.benign_label != candidate.schema.benign_label:
        raise ValueError("Methods have incompatible native label meanings or benign mappings")
    if rows != b[0]:
        raise ValueError("Methods must have identical ordered row IDs; align explicitly upstream")
    if truth != b[1]:
        raise ValueError("Ground truth differs on paired row IDs")
    if groups != b[4]:
        raise ValueError("Methods disagree on source groups for paired rows")
    if isinstance(confidence, bool) or not isinstance(confidence, (float, int)) or not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    before = stage_metrics(truth, pred_a, schema=baseline.schema)
    after = stage_metrics(truth, b[2], schema=baseline.schema)
    result = {"baseline": before, "candidate": after, "paired_deltas": _deltas(before, after), "bootstrap": None}
    if bootstrap is None:
        return result
    if groups is None:
        raise ValueError("Group intervals require declared source groups on both methods")
    plan_rows = _values(bootstrap.row_ids, "bootstrap row_ids")
    plan_groups = _values(bootstrap.group_ids, "bootstrap group_ids")
    if plan_rows != rows or plan_groups != groups:
        raise ValueError("Bootstrap plan is bound to different ordered rows or source groups")
    unique = tuple(dict.fromkeys(groups))
    if not isinstance(bootstrap.group_unit, str) or not bootstrap.group_unit.strip() or len(unique) < 2 or len(bootstrap.draws) < 2:
        raise ValueError("Bootstrap plan lacks enough declared source groups or draws")
    # All requested metrics depend only on confusion counts. Repeating whole
    # group matrices is exactly equivalent to repeating paired source rows,
    # without allocating a full data copy for every bootstrap replicate.
    label_index = {native: i for i, native in enumerate(names)}
    group_index = {group: i for i, group in enumerate(unique)}
    yt = np.asarray([label_index[v] for v in truth], dtype=np.int64)
    ya = np.asarray([label_index[v] for v in pred_a], dtype=np.int64)
    yb = np.asarray([label_index[v] for v in b[2]], dtype=np.int64)
    gi = np.asarray([group_index[v] for v in groups], dtype=np.int64)
    group_a = np.zeros((len(unique), len(names), len(names)), dtype=np.int64)
    group_b = np.zeros_like(group_a)
    np.add.at(group_a, (gi, yt, ya), 1)
    np.add.at(group_b, (gi, yt, yb), 1)
    replicates = []
    checked_draws = []
    for raw_draw in bootstrap.draws:
        draw = _values(raw_draw, "bootstrap group draw")
        if len(draw) != len(unique):
            raise ValueError("Each replicate must sample exactly G groups with replacement")
        if set(draw) - group_index.keys():
            raise ValueError("Bootstrap draw contains an undeclared source group")
        checked_draws.append(draw)
        weights = np.bincount([group_index[g] for g in draw], minlength=len(unique))
        left = _metrics_from_confusion(np.tensordot(weights, group_a, axes=1), names, baseline.schema.benign_label)
        right = _metrics_from_confusion(np.tensordot(weights, group_b, axes=1), names, baseline.schema.benign_label)
        replicates.append(_deltas(left, right))
    intervals = {key: _interval([r[key] for r in replicates], float(confidence))
                 for key in ["delta_macro_f1", "delta_benign_false_alert_rate"]}
    intervals["stages"] = {
        name: {key: _interval([r["stages"][name][key] for r in replicates], float(confidence))
               for key in ["delta_warning_recall", "delta_exact_stage_recall", "delta_stage_f1"]}
        for name in before["stages"]
    }
    encoded = json.dumps({"rows": rows, "groups": groups, "draws": checked_draws}, separators=(",", ":")).encode()
    result["bootstrap"] = {
        "method": "paired source-group percentile bootstrap",
        "group_unit": bootstrap.group_unit,
        "group_count": len(unique),
        "replicates": len(replicates),
        "seed": bootstrap.seed,
        "paired_draws_sha256": hashlib.sha256(encoded).hexdigest(),
        "intervals": intervals,
        "independence_note": "The caller must justify real source-group independence; resampling cannot establish it.",
    }
    if include_replicates:
        result["bootstrap"]["group_draws"] = [list(draw) for draw in checked_draws]
        result["bootstrap"]["paired_replicates"] = replicates
    return result
