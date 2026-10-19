"""Check saved artifacts and independently recalculate reported classification metrics."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from experiment import HERE, sha, scores, validate


def verify(input_path, directory):
    directory = Path(directory)
    df = pd.read_csv(input_path)
    validate(df)
    manifest = json.loads((directory / "artifact_manifest.json").read_text())
    for name, expected in manifest.items():
        assert sha(directory / name) == expected, f"Artifact changed: {name}"
    freeze = json.loads((directory / "selection_freeze.json").read_text())
    assert sha(input_path) == freeze["input_sha256"]
    assert sha(HERE / "experiment.py") == freeze["code_sha256"]
    assert sha(HERE / "feature_spec.json") == freeze["feature_spec_sha256"]
    predictions = pd.read_csv(directory / "predictions.csv")
    assert not predictions.duplicated(["model", "trial_id"]).any()
    assert predictions[predictions.partition == "control"].y_true.isna().all()
    assert set(predictions.dataset_kind) == set(df.dataset_kind)
    expected_trials = set(df[df.partition != "train"].trial_id)
    for model, sub in predictions.groupby("model"):
        assert set(sub.trial_id) == expected_trials, model
    joined = predictions.merge(df[["trial_id", "group_id", "arm", "partition"]],
                               on="trial_id", suffixes=("", "_source"), validate="many_to_one")
    for col in ["group_id", "arm", "partition"]:
        assert (joined[col] == joined[col + "_source"]).all()
    primary = predictions[predictions.partition != "control"]
    assert (primary.y_true == (primary.arm == "autonomous_ai").astype(int)).all()
    metrics = json.loads((directory / "metrics.json").read_text())
    for row in metrics:
        sub = predictions[(predictions.model == row["model"]) & (predictions.partition == row["partition"])]
        actual = scores(sub.y_true.to_numpy(int), sub.predicted_ai.to_numpy(int))
        assert len(sub) == row["trials"]
        for key, value in actual.items():
            np.testing.assert_allclose(value, row[key])
    expected_models = set(freeze["search"])
    assert set(predictions.model) == expected_models
    assert len(metrics) == len(expected_models) * 3
    for name in ["rq1_features.json", "rq2_transfer.json", "rq3_comparison.json"]:
        assert json.loads((directory / name).read_text())
    print(f"PASS: {len(expected_models)} model/feature combinations, {len(predictions)} predictions, "
          f"{len(metrics)} metric records; labels, partitions, hashes and recomputed metrics agree.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    verify(args.input, args.run)
