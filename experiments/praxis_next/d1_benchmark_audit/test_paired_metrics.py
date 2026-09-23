"""Independent examples for warning preservation, pairing and group inference."""
from dataclasses import replace
import json

import numpy as np
import pytest
from sklearn.metrics import f1_score

from .paired_metrics import (
    GroupBootstrapPlan, LabelSchema, PredictionBatch, make_group_bootstrap_plan,
    paired_comparison, resample_group_indices, stage_metrics,
)


SCHEMA = LabelSchema({3: "Benign", 7: "Movement", 9: "Export"}, benign_label=3)


def batches():
    truth = (3, 3, 7, 7, 9, 9, 9, 9)
    old = (3, 3, 7, 7, 7, 7, 7, 7)
    new = (3, 3, 7, 7, 3, 9, 9, 9)
    rows = tuple(f"row-{i}" for i in range(len(truth)))
    groups = ("a", "b", "a", "b", "a", "b", "c", "c")
    return (PredictionBatch(rows, truth, old, SCHEMA, groups),
            PredictionBatch(rows, truth, new, SCHEMA, groups))


def test_native_benign_is_explicit_and_wrong_stage_still_warns():
    before, after = batches()
    a = stage_metrics(before.y_true, before.y_pred, schema=SCHEMA)
    b = stage_metrics(after.y_true, after.y_pred, schema=SCHEMA)
    assert a["stages"]["Export"]["exact_stage_recall"] == 0
    assert a["stages"]["Export"]["warning_recall"] == 1
    assert a["wrong_attack_stage_count"] == 4
    assert a["attack_to_benign_count"] == 0
    assert b["stages"]["Export"]["warning_recall"] == .75
    assert b["attack_to_benign_count"] == 1
    assert b["wrong_attack_stage_count"] == 0
    assert b["benign_false_alert_rate"] == 0
    assert b["macro_f1"] == pytest.approx(f1_score(after.y_true, after.y_pred, labels=[3, 7, 9], average="macro"))


def test_sign_reversal_is_detected_without_calling_wrong_stage_benign():
    a, b = batches()
    result = paired_comparison(a, b)["paired_deltas"]
    assert result["delta_macro_f1"] > 0
    assert result["stages"]["Export"]["delta_warning_recall"] == -.25
    assert result["stages"]["Export"]["macro_f1_up_warning_down"] is True
    assert result["stages"]["Export"]["macro_f1_warning_sign_reversal"] is True
    assert result["stages"]["Movement"]["macro_f1_warning_sign_reversal"] is False


def test_unsupported_stage_and_absent_benign_rates_are_null():
    result = stage_metrics([3, 7], [9, 3], schema=SCHEMA)
    missing = result["stages"]["Export"]
    assert missing["support"] == 0 and missing["predicted_count"] == 1
    assert missing["exact_stage_recall"] is None
    assert missing["warning_recall"] is None
    assert missing["f1"] is None
    assert result["macro_f1"] is None
    assert result["macro_f1_unsupported_classes"] == ["Export"]
    no_benign = stage_metrics([7, 9], [3, 9], schema=SCHEMA)
    assert no_benign["benign_false_alert_rate"] is None
    assert no_benign["benign_false_alert_count"] == 0


def test_numpy_native_ids_and_undefined_values_are_json_safe():
    schema = LabelSchema({np.int64(3): "Benign", np.int64(7): "Movement"}, np.int64(3))
    result = stage_metrics(np.array([3, 3]), np.array([3, 7]), schema=schema)
    serialized = json.loads(json.dumps(result, allow_nan=False))
    assert serialized["benign_label"] == 3
    assert serialized["stages"]["Movement"]["warning_recall"] is None
    assert serialized["macro_f1"] is None


@pytest.mark.parametrize("schema", [
    LabelSchema({7: "Movement", 9: "Export"}, benign_label=3),
    LabelSchema({3: "Benign", 7: "Movement"}, benign_label=None),
    LabelSchema({3: "Same", 7: "Same"}, benign_label=3),
])
def test_absent_or_ambiguous_benign_mapping_is_rejected(schema):
    with pytest.raises(ValueError):
        stage_metrics([3, 7], [3, 7], schema=schema)


def test_invalid_labels_lengths_and_duplicate_row_ids_are_rejected():
    with pytest.raises(ValueError, match="outside"):
        stage_metrics([3, 7], [3, 99], schema=SCHEMA)
    with pytest.raises(ValueError):
        stage_metrics([3, 7], [3], schema=SCHEMA)
    with pytest.raises(ValueError):
        stage_metrics([3, float("nan")], [3, 7], schema=SCHEMA)
    a, b = batches()
    with pytest.raises(ValueError, match="unique"):
        paired_comparison(replace(a, row_ids=("same",) * 8), b)


def test_incompatible_meanings_truth_ids_and_groups_cannot_be_paired():
    a, b = batches()
    changed_schema = LabelSchema({3: "Benign", 7: "A different technique", 9: "Export"}, 3)
    with pytest.raises(ValueError, match="incompatible"):
        paired_comparison(a, replace(b, schema=changed_schema))
    with pytest.raises(ValueError, match="incompatible"):
        paired_comparison(a, replace(b, schema=LabelSchema(SCHEMA.label_names, 7)))
    with pytest.raises(ValueError, match="ordered row IDs"):
        paired_comparison(a, replace(b, row_ids=tuple(reversed(b.row_ids))))
    with pytest.raises(ValueError, match="Ground truth"):
        paired_comparison(a, replace(b, y_true=(3,) * 8))
    with pytest.raises(ValueError, match="source groups"):
        paired_comparison(a, replace(b, group_ids=("different",) * 8))


def test_group_ci_requires_real_declared_groups_and_two_units():
    a, b = batches()
    with pytest.raises(ValueError, match="explicit sequence"):
        make_group_bootstrap_plan(a.row_ids, None, group_unit="execution_id")
    with pytest.raises(ValueError, match="grouping unit"):
        make_group_bootstrap_plan(a.row_ids, a.group_ids, group_unit="")
    with pytest.raises(ValueError, match="At least two"):
        make_group_bootstrap_plan(a.row_ids, ("one",) * 8, group_unit="campaign_id")
    plan = make_group_bootstrap_plan(a.row_ids, a.group_ids, group_unit="execution_id", n_resamples=10)
    with pytest.raises(ValueError, match="declared source groups"):
        paired_comparison(replace(a, group_ids=None), replace(b, group_ids=None), bootstrap=plan)
    wrong_rows = replace(plan, row_ids=tuple(reversed(plan.row_ids)))
    with pytest.raises(ValueError, match="bound to different"):
        paired_comparison(a, b, bootstrap=wrong_rows)


def test_unequal_groups_and_repeated_draws_retain_all_paired_rows():
    a, b = batches()
    groups = ("small", "large", "large", "large", "large", "large", "large", "large")
    a, b = replace(a, group_ids=groups), replace(b, group_ids=groups)
    plan = GroupBootstrapPlan(a.row_ids, groups, "actual_execution_id",
                              (("large", "large"), ("small", "large")), 11)
    result = paired_comparison(a, b, bootstrap=plan, include_replicates=True)
    ix = resample_group_indices(groups, ("large", "large"))
    np.testing.assert_array_equal(ix, list(range(1, 8)) * 2)
    # Independent sklearn F1 over the explicitly repeated rows checks that
    # whole-group weighting was not replaced by unique rows or equal groups.
    yt = np.asarray(a.y_true)[ix]
    expected = f1_score(yt, np.asarray(b.y_pred)[ix], labels=[3, 7, 9], average="macro") - f1_score(yt, np.asarray(a.y_pred)[ix], labels=[3, 7, 9], average="macro")
    assert result["bootstrap"]["paired_replicates"][0]["delta_macro_f1"] == pytest.approx(expected)


def test_rare_stage_bootstrap_reports_undefined_draws_explicitly():
    schema = LabelSchema({"B": "Benign", "M": "Movement"}, "B")
    a = PredictionBatch(("n", "m"), ("B", "M"), ("B", "B"), schema, ("normal-run", "rare-run"))
    b = replace(a, y_pred=("B", "M"))
    plan = GroupBootstrapPlan(tuple(a.row_ids), tuple(a.group_ids), "execution_id",
        (("normal-run", "normal-run"), ("normal-run", "rare-run"), ("rare-run", "rare-run")), 0)
    boot = paired_comparison(a, b, bootstrap=plan, include_replicates=True)["bootstrap"]
    warning = boot["intervals"]["stages"]["Movement"]["delta_warning_recall"]
    assert warning["valid_replicates"] == 2 and warning["undefined_replicates"] == 1
    assert warning["status"] == "SUPPORT_CONDITIONAL"
    assert warning["lower"] == warning["upper"] == 1
    macro = boot["intervals"]["delta_macro_f1"]
    assert macro["valid_replicates"] == 1 and macro["lower"] is None
    assert macro["status"] == "INSUFFICIENT_DEFINED_REPLICATES"
    assert boot["paired_replicates"][0]["stages"]["Movement"]["delta_warning_recall"] is None


def test_identical_plans_preserve_pairing_across_contrasts_and_reversal():
    a, b = batches()
    plan = make_group_bootstrap_plan(a.row_ids, a.group_ids, group_unit="execution_id", n_resamples=101, seed=43)
    forward = paired_comparison(a, b, bootstrap=plan, include_replicates=True)["bootstrap"]
    reverse = paired_comparison(b, a, bootstrap=plan, include_replicates=True)["bootstrap"]
    same = paired_comparison(a, a, bootstrap=plan, include_replicates=True)["bootstrap"]
    assert forward["paired_draws_sha256"] == reverse["paired_draws_sha256"] == same["paired_draws_sha256"]
    assert forward["group_draws"] == reverse["group_draws"]
    for f, r, z in zip(forward["paired_replicates"], reverse["paired_replicates"], same["paired_replicates"]):
        if f["delta_macro_f1"] is not None:
            assert f["delta_macro_f1"] == pytest.approx(-r["delta_macro_f1"])
            assert z["delta_macro_f1"] == 0
    fi, ri = forward["intervals"]["delta_macro_f1"], reverse["intervals"]["delta_macro_f1"]
    assert fi["lower"] == pytest.approx(-ri["upper"])
    assert fi["upper"] == pytest.approx(-ri["lower"])


def test_unknown_group_draw_rejected_and_reordered_equivalent_schema_accepted():
    a, b = batches()
    plan = GroupBootstrapPlan(a.row_ids, a.group_ids, "execution_id", (("a", "b", "missing"), ("a", "b", "c")), 0)
    with pytest.raises(ValueError, match="undeclared"):
        paired_comparison(a, b, bootstrap=plan)
    equivalent = LabelSchema({9: "Export", 3: "Benign", 7: "Movement"}, 3)
    assert paired_comparison(a, replace(b, schema=equivalent))["paired_deltas"] == paired_comparison(a, b)["paired_deltas"]
