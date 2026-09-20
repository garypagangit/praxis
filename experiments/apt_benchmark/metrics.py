"""Evaluation helpers; no fitting, split selection or ground-truth inference.

Scores increase with maliciousness; binary alarms use strict score > threshold.
None denotes an undefined metric, always accompanied by an explanation. These
helpers describe the supplied, already-qualified labels; they do not certify
independent episodes, correct stage annotations or continuous host exposure.
"""
from __future__ import annotations

from datetime import datetime
import math
from numbers import Real

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


_METRICS = ('precision', 'recall', 'f1', 'balanced_accuracy', 'mcc',
            'roc_auc', 'average_precision')


def _finite_number(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    return float(value)


def _binary_arrays(y_true, scores, sample_weight):
    labels = np.asarray(y_true)
    values = np.asarray(scores, dtype=float)
    if labels.ndim != 1 or values.ndim != 1 or len(labels) != len(values) or not len(labels):
        raise ValueError('Nonempty equal-length one-dimensional labels and scores required')
    if not np.isin(labels, [0, 1]).all() or not np.isfinite(values).all():
        raise ValueError('Labels must be known binary 0/1; scores must be finite')
    weights = np.ones(len(labels)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
    if (weights.shape != labels.shape or not np.isfinite(weights).all()
            or (weights < 0).any() or weights.sum() <= 0):
        raise ValueError('Weights must be finite, nonnegative and have positive total')
    return labels.astype(bool), values, weights


def binary_metrics(y_true, scores, threshold=0.5, *, groups=None, sample_weight=None):
    """Pooled metrics, plus optional equal-group macro metrics (not pooled F1).

    Weights affect all metrics, including ranking. Unweighted row counts remain
    separate. A single effective class makes ROC-AUC/AP/balanced accuracy
    undefined here, including the otherwise conventionally trivial all-positive
    AP=1. MCC is undefined when its denominator is zero. No probabilities are
    inferred from arbitrary decision scores.
    """
    y, score, weight = _binary_arrays(y_true, scores, sample_weight)
    if isinstance(threshold, (bool, np.bool_)) or not isinstance(threshold, Real) or math.isnan(threshold):
        raise ValueError('Threshold must be a number or explicit +/- infinity')
    pred = score > threshold
    masks = {'tp': y & pred, 'fp': ~y & pred, 'tn': ~y & ~pred, 'fn': y & ~pred}
    counts = {key: int(mask.sum()) for key, mask in masks.items()}
    weighted = {key: float(weight[mask].sum()) for key, mask in masks.items()}
    tp, fp, tn, fn = (weighted[key] for key in ('tp', 'fp', 'tn', 'fn'))
    undefined = {}

    def ratio(name, numerator, denominator, reason):
        if denominator <= 0:
            undefined[name] = reason
            return None
        return float(numerator / denominator)

    result = {
        'n_rows': len(y), 'n_attack': int(y.sum()), 'n_benign': int((~y).sum()),
        'weighted_support': {'attack': tp + fn, 'benign': tn + fp, 'total': float(weight.sum())},
        'confusion': counts, 'weighted_confusion': weighted,
        'precision': ratio('precision', tp, tp + fp, 'No positive predictions with positive weight'),
        'recall': ratio('recall', tp, tp + fn, 'No positive labels with positive weight'),
        'f1': ratio('f1', 2 * tp, 2 * tp + fp + fn, 'No positive labels or predictions with positive weight'),
        'false_positive_rate': ratio('false_positive_rate', fp, fp + tn, 'No negative labels with positive weight'),
        'decision_rule': 'score > threshold; larger scores mean malicious',
    }
    both = tp + fn > 0 and tn + fp > 0
    result['balanced_accuracy'] = ((tp / (tp + fn) + tn / (tn + fp)) / 2) if both else None
    denominator = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    result['mcc'] = float((tp * tn - fp * fn) / math.sqrt(denominator)) if denominator > 0 else None
    if not both:
        for name in ('balanced_accuracy', 'roc_auc', 'average_precision'):
            undefined[name] = 'Both label classes with positive weight are required'
        result.update(roc_auc=None, average_precision=None)
    else:
        positive_weight = weight > 0
        result['roc_auc'] = float(roc_auc_score(y[positive_weight], score[positive_weight], sample_weight=weight[positive_weight]))
        result['average_precision'] = float(average_precision_score(y[positive_weight], score[positive_weight], sample_weight=weight[positive_weight]))
    if denominator <= 0:
        undefined['mcc'] = 'MCC denominator is zero (constant labels or predictions)'
    result['undefined'] = undefined
    if groups is not None:
        group_list = list(groups)
        if len(group_list) != len(y) or any(not isinstance(g, str) or not g for g in group_list):
            raise ValueError('Groups must be nonempty strings, one per row')
        group_array = np.asarray(group_list)
        per_group, excluded = {}, []
        for group in sorted(set(group_list)):
            idx = group_array == group
            if weight[idx].sum() == 0:
                excluded.append(group)
                continue
            per_group[group] = binary_metrics(y[idx], score[idx], threshold, sample_weight=weight[idx])
        macro = {}
        for name in _METRICS:
            values = [row[name] for row in per_group.values() if row[name] is not None]
            macro[name] = {'value': float(np.mean(values)) if values else None,
                           'defined_groups': len(values), 'total_groups': len(per_group)}
        result['group_summary'] = {
            'aggregation': 'Equal-group macro over defined metrics; top-level metrics pool all weighted rows',
            'macro': macro, 'per_group': per_group, 'zero_weight_groups_excluded': excluded,
        }
    return result


def stage_metrics(y_true, scores, *, stage_names, stage_source, mode='multilabel', threshold=0.5,
                  chronology_claim=False):
    """Source-annotated stage metrics; no label-name-to-stage conversion.

    Multilabel inputs are N x K 0/1 labels and scores, with strict thresholds.
    Categorical labels are stage-name strings, scores are N x K, and argmax
    (first supplied class on ties) determines the category. Include an explicit
    benign/unknown category when the source supports it; unknown ground truth
    must not be silently passed as an all-zero known-label row.
    """
    names = list(stage_names)
    if (not names or len(set(names)) != len(names)
            or any(not isinstance(name, str) or not name for name in names)):
        raise ValueError('Unique nonempty stage names required')
    if not isinstance(stage_source, str) or not stage_source.strip():
        raise ValueError('Versioned stage-label source provenance is required')
    if chronology_claim:
        raise ValueError('Stage names alone do not establish chronology; evaluate documented episode times separately')
    score = np.asarray(scores, dtype=float)
    if score.ndim != 2 or score.shape[1] != len(names) or not len(score) or not np.isfinite(score).all():
        raise ValueError('Finite nonempty N x K stage scores required')
    if mode == 'categorical':
        raw_labels = list(y_true)
        if len(raw_labels) != len(score) or any(label not in names for label in raw_labels):
            raise ValueError('Every categorical label must be an explicit source-supported category')
        y = np.asarray([[label == name for name in names] for label in raw_labels])
        decisions = np.eye(len(names), dtype=bool)[np.argmax(score, axis=1)]
    elif mode == 'multilabel':
        y = np.asarray(y_true)
        if y.shape != score.shape or not np.isin(y, [0, 1]).all():
            raise ValueError('Multilabel ground truth must be known 0/1 with shape N x K')
        decisions = None
    else:
        raise ValueError('Mode must be multilabel or categorical')
    per_stage = {}
    for column, name in enumerate(names):
        row = binary_metrics(y[:, column], score[:, column], threshold)
        if decisions is not None:
            # Classification uses argmax, ranking still uses continuous class scores.
            classified = binary_metrics(y[:, column], decisions[:, column].astype(float), 0.5)
            for key in ('confusion', 'weighted_confusion', 'precision', 'recall', 'f1',
                        'false_positive_rate', 'balanced_accuracy', 'mcc'):
                row[key] = classified[key]
            row['undefined'] = {**{k: v for k, v in row['undefined'].items() if k in ('roc_auc', 'average_precision')},
                                **{k: v for k, v in classified['undefined'].items() if k not in ('roc_auc', 'average_precision')}}
            row['decision_rule'] = 'argmax across categorical scores; first supplied class on ties'
        per_stage[name] = row
    macro = {}
    for metric in _METRICS:
        values = [row[metric] for row in per_stage.values() if row[metric] is not None]
        macro[metric] = {'value': float(np.mean(values)) if values else None,
                         'defined_stages': len(values), 'total_stages': len(names)}
    return {'mode': mode, 'stage_source': stage_source, 'chronology_inferred': False,
            'n_rows': len(score), 'per_stage': per_stage, 'macro': macro}


def absolute_gain_feasibility(baseline, minimum_gain, *, higher_is_better=True,
                              lower_bound=0.0, upper_bound=1.0):
    """Check a proposed absolute improvement against metric bounds, not scores.

    This flags an unattainable criterion; it must not choose a replacement gate
    after test results or reinterpret a no-op candidate as an improvement.
    """
    baseline, gain, low, high = [_finite_number(value, name) for value, name in
                               ((baseline, 'baseline'), (minimum_gain, 'minimum_gain'),
                                (lower_bound, 'lower_bound'), (upper_bound, 'upper_bound'))]
    if type(higher_is_better) is not bool or gain < 0 or low > high or not low <= baseline <= high:
        raise ValueError('Invalid direction, bounds, baseline or negative improvement')
    available = high - baseline if higher_is_better else baseline - low
    attainable = gain <= available + 1e-12
    return {'attainable': attainable, 'maximum_possible_gain': available,
            'minimum_gain': gain, 'required_value': baseline + gain if higher_is_better else baseline - gain,
            'status': 'ATTAINABLE' if attainable else 'UNATTAINABLE_CRITERION_NOT_SCIENTIFIC_FAILURE'}


def _time(value, name):
    if isinstance(value, Real) and not isinstance(value, (bool, np.bool_)):
        return _finite_number(value, name)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError(f'{name} must be finite seconds or a timezone-aware ISO timestamp') from exc
        if parsed.tzinfo is not None and parsed.utcoffset() is not None:
            return parsed.timestamp()
    raise ValueError(f'{name} must be finite seconds or a timezone-aware ISO timestamp')


def early_detection_metrics(episodes, alarms, *, benign_host_hours=None, false_alert_count=None,
                            horizon_seconds=None):
    """Describe correctly attributed detections using actual alarm availability.

    Episodes: episode_id, onset_at, observation_end_at, optional impact_at.
    Alarms: episode_id (or None), decision_at, feature_available_at,
    score_available_at, optional feature_event_cutoff_at. Attribution is supplied
    by an independent source-ground-truth join, not inferred by this function.
    Feature availability <= score availability <= operator decision is mandatory.
    Undetected episodes remain right-censored. False alerts/exposure must be
    supplied after the frozen alarm grouping/cooldown policy; they are not
    inferred from score rows or gaps between event timestamps.
    """
    episode_rows = list(episodes)
    if not episode_rows:
        raise ValueError('At least one qualified episode is required')
    indexed = {}
    for row in episode_rows:
        identity = row.get('episode_id')
        if not isinstance(identity, str) or not identity or identity in indexed:
            raise ValueError('Unique nonempty episode IDs required')
        start = _time(row['onset_at'], 'onset_at')
        end = _time(row['observation_end_at'], 'observation_end_at')
        impact = None if row.get('impact_at') is None else _time(row['impact_at'], 'impact_at')
        if end < start or (impact is not None and impact < start):
            raise ValueError('Episode end/impact cannot precede onset')
        indexed[identity] = {'start': start, 'end': end, 'impact': impact, 'alarms': []}
    ignored = {'unattributed': 0, 'before_onset': 0, 'after_observation_end': 0}
    for alarm in alarms:
        feature = _time(alarm['feature_available_at'], 'feature_available_at')
        score = _time(alarm['score_available_at'], 'score_available_at')
        decision = _time(alarm['decision_at'], 'decision_at')
        if feature > score or score > decision:
            raise ValueError('Alarm uses a feature or score unavailable at its claimed decision time')
        if alarm.get('feature_event_cutoff_at') is not None and _time(alarm['feature_event_cutoff_at'], 'feature_event_cutoff_at') > feature:
            raise ValueError('Feature includes events after its claimed availability')
        identity = alarm.get('episode_id')
        if identity is None:
            ignored['unattributed'] += 1
            continue
        if identity not in indexed:
            raise ValueError('Attributed alarm names an unknown episode')
        target = indexed[identity]
        if decision < target['start']:
            ignored['before_onset'] += 1
        elif decision > target['end']:
            ignored['after_observation_end'] += 1
        else:
            target['alarms'].append(decision)
    output, impact_known, impact_unknown, impact_unresolved = [], [], 0, 0
    for identity, item in indexed.items():
        first = min(item['alarms']) if item['alarms'] else None
        followup = item['end'] - item['start']
        delay = None if first is None else first - item['start']
        before_impact = None
        if item['impact'] is None:
            impact_unknown += 1
        elif first is not None and first < item['impact']:
            before_impact = True
        elif item['end'] >= item['impact']:
            before_impact = False
        else:
            impact_unresolved += 1
        if before_impact is not None:
            impact_known.append(before_impact)
        output.append({'episode_id': identity, 'detected': first is not None,
                       'first_detection_at_seconds': first, 'delay_seconds': delay,
                       'followup_seconds': followup, 'right_censored': first is None,
                       'observed_time_seconds': delay if first is not None else followup,
                       'detected_before_impact': before_impact})
    minimum_followup = min(row['followup_seconds'] for row in output)
    horizon = minimum_followup if horizon_seconds is None else _finite_number(horizon_seconds, 'horizon_seconds')
    if horizon < 0:
        raise ValueError('Horizon must be nonnegative')
    fully_observed = all(row['followup_seconds'] >= horizon for row in output)
    restricted = (float(np.mean([min(row['delay_seconds'], horizon) if row['detected'] else horizon
                                  for row in output])) if fully_observed else None)
    checkpoints = sorted({0.0, horizon, *[min(row['delay_seconds'], horizon) for row in output if row['detected']]})
    curve = []
    for checkpoint in checkpoints:
        detected = sum(row['detected'] and row['delay_seconds'] <= checkpoint for row in output)
        censored = sum(not row['detected'] and row['followup_seconds'] < checkpoint for row in output)
        curve.append({'delay_seconds': checkpoint, 'detected_episodes': detected,
                      'total_episodes': len(output), 'fraction_all_episodes_lower_bound': detected / len(output),
                      'right_censored_before_checkpoint': censored,
                      'fully_observed_fraction': detected / len(output) if censored == 0 else None})
    if false_alert_count is not None and (type(false_alert_count) is not int or false_alert_count < 0):
        raise ValueError('False alert count must be a nonnegative integer or None')
    exposure = None if benign_host_hours is None else _finite_number(benign_host_hours, 'benign_host_hours')
    if exposure is not None and exposure < 0:
        raise ValueError('Benign exposure cannot be negative')
    false_rate = false_alert_count / exposure if exposure is not None and exposure > 0 and false_alert_count is not None else None
    all_impact_complete = len(impact_known) == len(output)
    return {
        'n_episodes': len(output), 'detected_episodes': sum(row['detected'] for row in output),
        'right_censored_episodes': sum(row['right_censored'] for row in output),
        'episodes': output, 'ignored_alarms': ignored, 'detection_curve': curve,
        'restricted_mean_delay_seconds': restricted, 'horizon_seconds': horizon,
        'horizon_status': 'FULL_COMMON_FOLLOWUP' if fully_observed else 'UNDEFINED_INSUFFICIENT_FOLLOWUP',
        'detected_before_impact_fraction_all_episodes': float(np.mean(impact_known)) if all_impact_complete else None,
        'detected_before_impact_fraction_evaluable': float(np.mean(impact_known)) if impact_known else None,
        'impact_evaluable_episodes': len(impact_known), 'impact_missing_episodes': impact_unknown,
        'impact_unresolved_followup_episodes': impact_unresolved,
        'zero_preimpact_opportunity_episodes': sum(item['impact'] == item['start'] for item in indexed.values()),
        'false_alert_count': false_alert_count, 'benign_host_hours': exposure,
        'false_alerts_per_benign_host_hour': false_rate,
        'false_alert_rate_status': 'DEFINED_FROM_SUPPLIED_EXPOSURE' if false_rate is not None else 'UNDEFINED_MISSING_COUNT_OR_POSITIVE_EXPOSURE',
        'limitations': ['Attribution and stage truth require independent source qualification',
                        'Observation intervals and alarm cooldown are supplied, not inferred',
                        'No independent-campaign or population confidence claim is made'],
    }
