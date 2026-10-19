import numpy as np
import pandas as pd
import pytest
from experiment import FEATURES, fixture, validate, tune, group_interval, models, parameter_record


@pytest.fixture
def data(tmp_path):
    return fixture(tmp_path / "fixture.csv")


def test_fixture_is_reproducible_and_grouped(tmp_path):
    a = fixture(tmp_path / "a.csv")
    b = fixture(tmp_path / "b.csv")
    pd.testing.assert_frame_equal(a, b)
    assert validate(a)["control"] == 48
    assert len(a) == 440


def test_duplicate_trial_rejected(data):
    bad = pd.concat([data, data.iloc[[0]]])
    with pytest.raises(ValueError, match="Duplicate trial"):
        validate(bad)


def test_unseen_group_leakage_rejected(data):
    data.loc[data.partition == "test_unseen", "group_id"] = data.loc[data.partition == "train", "group_id"].iloc[0]
    with pytest.raises(ValueError):
        validate(data)


def test_cross_source_class_shortcut_rejected(data):
    data.loc[data.arm == "human", "source_id"] = "human_only_archive"
    with pytest.raises(ValueError, match="confounding"):
        validate(data)


def test_control_not_relabelled_primary(data):
    data.loc[data.arm == "benign", "partition"] = "test_unseen"
    with pytest.raises(ValueError, match="Controls"):
        validate(data)


def test_unexpected_feature_metadata_rejected(data):
    data["model_name_as_feature"] = 1
    with pytest.raises(ValueError, match="Unexpected"):
        validate(data)


def test_imputer_uses_training_only(data):
    train = data[data.partition == "train"]
    val = data[data.partition == "validation"].copy()
    val.loc[:, FEATURES] = 1e6
    fitted, _ = tune(train, val, FEATURES, "logistic", 19)
    np.testing.assert_allclose(fitted[0].statistics_, np.nanmedian(train[FEATURES], axis=0))


def test_paired_identical_predictions_have_zero_difference(data):
    sub = data[data.partition == "test_unseen"]
    pred = (sub.arm == "autonomous_ai").astype(int).to_numpy()
    assert group_interval(sub, pred, pred, repeats=20) == [0., 0.]


def test_all_candidate_parameters_are_strict_json():
    import json
    for candidates in models(19).values():
        for model in candidates:
            json.dumps(parameter_record(model.get_params()), allow_nan=False)
