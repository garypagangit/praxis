"""Exploratory, trial-level experiment harness. Synthetic scores are not evidence.

No offensive commands or external datasets are executed. Real inputs must already
be validated defender-visible aggregate features in the documented CSV contract.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE / "feature_spec.json").read_text())
FEATURES = [c for columns in SPEC.values() for c in columns]
META = ["trial_id", "group_id", "arm", "partition", "source_id", "dataset_kind"]
PARTS = {"train", "validation", "test_seen", "test_unseen", "control"}
ARMS = {"human", "autonomous_ai", "scripted_control", "benign"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def parameter_record(params):
    # XGBoost uses NaN as its missing-value sentinel. Record the sentinel as text,
    # without permitting non-finite result metrics in strict JSON artifacts.
    return {k: ("NaN" if isinstance(v, float) and np.isnan(v) else v)
            for k, v in params.items()}


def fixture(path, seed=19):
    """Deliberate signal + nuisance shift, not a simulation of real attackers."""
    rng = np.random.default_rng(seed)
    rows = []
    for label, arm in enumerate(["human", "autonomous_ai"]):
        for group in range(14):
            group_effect = rng.normal(0, .3, len(FEATURES))
            for trial in range(14):
                part = ("test_unseen" if group >= 10 else
                        "validation" if group >= 8 else
                        "test_seen" if trial >= 11 else "train")
                x = rng.normal(0, 1, len(FEATURES)) + group_effect
                x[:7] += label * np.array([.7, .6, -.4, .7, .4, .5, .3])
                # Shift an easy timing/tool cue in unseen groups.
                x[7:] += label * (1.5 if group < 10 else -.4)
                if rng.random() < .15:
                    x[rng.integers(0, len(x))] = np.nan
                rows.append(dict(zip(META + FEATURES,
                    [f"s-{label}-{group}-{trial}", f"{arm}-{group}", arm,
                     part, "synthetic_fixture", "synthetic"] + x.tolist())))
    for arm in ["scripted_control", "benign"]:
        for i in range(24):
            x = rng.normal(0, 1, len(FEATURES))
            if arm == "scripted_control":
                x[7:] += 2
            rows.append(dict(zip(META + FEATURES,
                [f"{arm}-{i}", f"{arm}-{i//6}", arm, "control",
                 "synthetic_fixture", "synthetic"] + x.tolist())))
    frame = pd.DataFrame(rows)
    validate(frame)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def validate(df):
    missing = set(META + FEATURES) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if set(df.columns) - set(META + FEATURES):
        raise ValueError("Unexpected columns: use the exact schema; metadata cannot become features")
    if df[META].isna().any().any() or (df[META].astype(str).apply(lambda c: c.str.strip()) == "").any().any():
        raise ValueError("Metadata must be nonempty")
    if df.trial_id.duplicated().any():
        raise ValueError("Duplicate trial IDs: aggregate windows to one row per trial")
    if not set(df.partition) <= PARTS or not set(df.arm) <= ARMS:
        raise ValueError("Unknown arm/partition")
    if len(set(df.dataset_kind)) != 1 or not set(df.dataset_kind) <= {"synthetic", "real"}:
        raise ValueError("One dataset_kind (synthetic or real) required")
    if not all(pd.api.types.is_numeric_dtype(df[c]) for c in FEATURES):
        raise ValueError("Features must be numeric")
    if np.isinf(df[FEATURES].to_numpy(float)).any():
        raise ValueError("Infinite features are not allowed")
    if df.groupby("group_id").arm.nunique().max() > 1:
        raise ValueError("A group ID must identify one operator/configuration arm")
    if ((df.partition == "control") != df.arm.isin(["scripted_control", "benign"])).any():
        raise ValueError("Controls must remain in the control partition")
    group_sets = {}
    for part in ["train", "validation", "test_seen", "test_unseen"]:
        sub = df[df.partition == part]
        if set(sub.arm) != {"human", "autonomous_ai"}:
            raise ValueError(f"{part} requires both primary classes")
        if sub.groupby("arm").group_id.nunique().min() < 2:
            raise ValueError(f"{part} needs at least two groups per class for this harness")
        group_sets[part] = set(sub.group_id)
    if group_sets["validation"] & (group_sets["train"] | group_sets["test_seen"] | group_sets["test_unseen"]):
        raise ValueError("Validation group leakage")
    if group_sets["test_unseen"] & (group_sets["train"] | group_sets["test_seen"]):
        raise ValueError("Unseen group leakage")
    if not group_sets["test_seen"] <= group_sets["train"]:
        raise ValueError("test_seen must contain new trials from known training groups")
    if df[df.partition == "train"][FEATURES].isna().all().any():
        raise ValueError("Training feature entirely missing")
    # Reject the obvious human-source-A / AI-source-B shortcut.
    primary = df[df.partition != "control"]
    for source, sub in primary.groupby("source_id"):
        if sub.arm.nunique() != 2:
            raise ValueError(f"Source {source!r} lacks both arms; cross-source label confounding")
    if primary.duplicated(FEATURES, keep=False).any():
        raise ValueError("Exact duplicate primary feature rows require a duplicate audit")
    return {p: int((df.partition == p).sum()) for p in sorted(PARTS)}


def xy(df, columns):
    return df[columns].to_numpy(float), (df.arm == "autonomous_ai").astype(int).to_numpy()


class NumericTransformer(ClassifierMixin, BaseEstimator):
    """Small FT-style numerical tokenizer + CLS transformer, not paper replication.

    Fixed epoch budget avoids early stopping on the external validation/test set.
    Scaling/imputation are in the enclosing training-only sklearn pipeline.
    """
    def __init__(self, width=16, epochs=25, seed=19):
        self.width, self.epochs, self.seed = width, epochs, seed

    def fit(self, X, y):
        import torch
        from torch import nn
        torch.manual_seed(self.seed)
        torch.set_num_threads(1)
        width = self.width
        class Net(nn.Module):
            def __init__(self, n):
                super().__init__()
                self.weight = nn.Parameter(torch.randn(n, width) * .05)
                self.bias = nn.Parameter(torch.randn(n, width) * .05)
                self.cls = nn.Parameter(torch.zeros(1, 1, width))
                layer = nn.TransformerEncoderLayer(width, 4, width * 2,
                    dropout=.1, batch_first=True, activation="gelu")
                self.encoder = nn.TransformerEncoder(layer, 1)
                self.head = nn.Linear(width, 2)
            def forward(self, x):
                tokens = x.unsqueeze(-1) * self.weight + self.bias
                tokens = torch.cat([self.cls.expand(len(x), -1, -1), tokens], dim=1)
                return self.head(self.encoder(tokens)[:, 0])
        self.model_ = Net(X.shape[1])
        self.classes_ = np.array([0, 1])
        X = torch.tensor(X, dtype=torch.float32)
        y = torch.tensor(y, dtype=torch.long)
        optimizer = torch.optim.AdamW(self.model_.parameters(), lr=.003, weight_decay=.01)
        for _ in range(self.epochs):
            self.model_.train()
            for idx in torch.randperm(len(y)).split(64):
                optimizer.zero_grad()
                loss = nn.functional.cross_entropy(self.model_(X[idx]), y[idx])
                loss.backward()
                optimizer.step()
        return self

    def predict_proba(self, X):
        import torch
        self.model_.eval()
        with torch.no_grad():
            return torch.softmax(self.model_(torch.tensor(X, dtype=torch.float32)), dim=1).numpy()

    def predict(self, X):
        return self.predict_proba(X).argmax(axis=1)


def models(seed):
    from xgboost import XGBClassifier
    return {
        "dummy": [DummyClassifier(strategy="prior")],
        "logistic": [LogisticRegression(C=c, max_iter=1000, random_state=seed) for c in [.1, 1]],
        "decision_tree": [DecisionTreeClassifier(max_depth=d, min_samples_leaf=4, random_state=seed) for d in [2, 4]],
        "random_forest": [RandomForestClassifier(n_estimators=80, max_depth=d, min_samples_leaf=3, random_state=seed, n_jobs=1) for d in [3, 6]],
        "xgboost": [XGBClassifier(n_estimators=60, max_depth=d, learning_rate=.08, n_jobs=1, random_state=seed, eval_metric="logloss") for d in [2, 4]],
        "svm": [SVC(C=c, kernel="rbf") for c in [.5, 2]],
        "ft_style_transformer": [NumericTransformer(width=w, seed=seed) for w in [16, 32]],
    }


def scores(y, pred):
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {"macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
            "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
            "human_false_ai_rate": float(fp / (tn + fp)),
            "ai_recall": float(tp / (tp + fn)),
            "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]}


def group_interval(df, pred, other=None, seed=19, repeats=250):
    """Class-stratified cluster bootstrap; descriptive with few groups."""
    rng = np.random.default_rng(seed)
    y = (df.arm == "autonomous_ai").astype(int).to_numpy()
    groups = df.group_id.to_numpy()
    values = []
    for _ in range(repeats):
        indices = []
        for label in [0, 1]:
            pool = np.unique(groups[y == label])
            for group in rng.choice(pool, len(pool), replace=True):
                indices.extend(np.flatnonzero(groups == group))
        idx = np.array(indices)
        value = f1_score(y[idx], pred[idx], average="macro", zero_division=0)
        if other is not None:
            value -= f1_score(y[idx], other[idx], average="macro", zero_division=0)
        values.append(value)
    return [float(x) for x in np.quantile(values, [.025, .975])]


def tune(train, val, columns, name, seed):
    X, y = xy(train, columns)
    V, vy = xy(val, columns)
    records, fitted = [], []
    for index, candidate in enumerate(models(seed)[name]):
        pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), candidate)
        start = time.perf_counter()
        pipeline.fit(X, y)
        prediction = pipeline.predict(V)
        records.append({"index": index, "parameters": parameter_record(candidate.get_params()),
                        "validation_macro_f1": scores(vy, prediction)["macro_f1"],
                        "fit_seconds": time.perf_counter() - start})
        fitted.append(pipeline)
    best = max(range(len(records)), key=lambda i: records[i]["validation_macro_f1"])
    return fitted[best], {"chosen_index": best, "search": records}


def importance(model, data, columns, seed):
    X, y = xy(data, columns)
    base = f1_score(y, model.predict(X), average="macro", zero_division=0)
    rng = np.random.default_rng(seed)
    result = {}
    for family, members in SPEC.items():
        indices = [columns.index(c) for c in members if c in columns]
        if not indices:
            continue
        drops = []
        for _ in range(8):
            permuted = X.copy()
            # Same row permutation preserves within-family correlations.
            permuted[:, indices] = X[rng.permutation(len(X))][:, indices]
            drops.append(base - f1_score(y, model.predict(permuted), average="macro", zero_division=0))
        result[family] = {"mean_drop": float(np.mean(drops)), "repeat_sd": float(np.std(drops))}
    return result


def run(input_path, output, allow_real=False, seed=19):
    df = pd.read_csv(input_path)
    counts = validate(df)
    kind = df.dataset_kind.iloc[0]
    if kind == "real" and not allow_real:
        raise ValueError("Real data requires --allow-real; harness remains exploratory")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    train = df[df.partition == "train"].copy()
    val = df[df.partition == "validation"].copy()
    sets = {"full": FEATURES, "no_timing": [c for c in FEATURES if c not in SPEC["timing"]],
            "reduced": SPEC["host"] + SPEC["network"],
            "host_only": SPEC["host"], "network_only": SPEC["network"],
            "timing_only": SPEC["timing"]}
    fitted, search = {}, {}
    # All decisions and fits precede access to locked-test features and labels.
    for feature_set in ["full", "reduced"]:
        for name in models(seed):
            key = name + ":" + feature_set
            fitted[key], search[key] = tune(train, val, sets[feature_set], name, seed)
            print("Fitted", key, flush=True)
    # RQ1 ablations use a predeclared RF reference, not the final-test winner.
    for feature_set in ["no_timing", "host_only", "network_only", "timing_only"]:
        key = "random_forest:" + feature_set
        fitted[key], search[key] = tune(train, val, sets[feature_set], "random_forest", seed)
    for family in SPEC:
        feature_set = "minus_" + family
        sets[feature_set] = [c for c in FEATURES if c not in SPEC[family]]
        key = "random_forest:" + feature_set
        fitted[key], search[key] = tune(train, val, sets[feature_set], "random_forest", seed)
    primary = max([k for k in fitted if k.endswith(":full") and not k.startswith("dummy:")],
                  key=lambda k: search[k]["search"][search[k]["chosen_index"]]["validation_macro_f1"])
    freeze = {"dataset_kind": kind, "mode": "exploratory_engineering_test", "seed": seed,
              "input_sha256": sha(input_path), "code_sha256": sha(__file__),
              "feature_spec_sha256": sha(HERE / "feature_spec.json"), "counts": counts,
              "primary_selected_on_validation": primary, "feature_sets": sets,
              "search": search, "hypotheses": "NOT TESTED CONFIRMATORILY; margins not frozen",
              "python": platform.python_version()}
    import importlib.metadata
    freeze["packages"] = {m: importlib.metadata.version(m) for m in
                          ["numpy", "pandas", "scikit-learn", "xgboost", "torch"]}
    dump(output / "selection_freeze.json", freeze)
    metrics, prediction_rows, predictions = [], [], {}
    for key, model in fitted.items():
        name, feature_set = key.split(":")
        for part in ["validation", "test_seen", "test_unseen", "control"]:
            sub = df[df.partition == part]
            if sub.empty:
                continue
            X, y = xy(sub, sets[feature_set])
            pred = model.predict(X)
            predictions[key, part] = pred
            for trial, group, arm, truth, value in zip(sub.trial_id, sub.group_id, sub.arm, y, pred):
                prediction_rows.append({"model": key, "partition": part, "trial_id": trial,
                    "group_id": group, "arm": arm, "y_true": int(truth) if part != "control" else None,
                    "predicted_ai": int(value), "dataset_kind": kind})
            if part != "control":
                row = {"model": key, "partition": part, "trials": len(sub), **scores(y, pred)}
                row["cluster_bootstrap_95_interval"] = group_interval(sub, pred, seed=seed)
                metrics.append(row)
    dump(output / "metrics.json", metrics)
    pd.DataFrame(prediction_rows).to_csv(output / "predictions.csv", index=False)
    controls = pd.DataFrame(prediction_rows)
    controls = controls[controls.partition == "control"]
    if not controls.empty:
        controls.groupby(["model", "arm"]).agg(trials=("trial_id", "count"),
            predicted_ai_rate=("predicted_ai", "mean")).reset_index().to_csv(output / "control_summary.csv", index=False)
    rq1 = {"reference": "random_forest:full", "importance_validation": importance(
        fitted["random_forest:full"], val, FEATURES, seed), "ablations": []}
    for part in ["validation", "test_unseen"]:
        sub = df[df.partition == part]
        for family in SPEC:
            key = "random_forest:minus_" + family
            pred = predictions[key, part]
            full = predictions["random_forest:full", part]
            rq1["ablations"].append({"removed": family, "partition": part,
                "full_minus_ablated_macro_f1": scores(xy(sub, FEATURES)[1], full)["macro_f1"] - scores(xy(sub, FEATURES)[1], pred)["macro_f1"],
                "paired_cluster_interval": group_interval(sub, full, pred, seed)})
    dump(output / "rq1_features.json", rq1)
    rq2 = []
    for name in models(seed):
        for feature_set in ["full", "reduced"]:
            key = name + ":" + feature_set
            seen = next(m for m in metrics if m["model"] == key and m["partition"] == "test_seen")
            unseen = next(m for m in metrics if m["model"] == key and m["partition"] == "test_unseen")
            imp_val = importance(fitted[key], val, sets[feature_set], seed)
            test = df[df.partition == "test_unseen"]
            imp_test = importance(fitted[key], test, sets[feature_set], seed)
            families = list(imp_val)
            top_val = max(families, key=lambda f: imp_val[f]["mean_drop"])
            top_test = max(families, key=lambda f: imp_test[f]["mean_drop"])
            rq2.append({"model": key, "known_group_macro_f1": seen["macro_f1"],
                "unseen_group_macro_f1": unseen["macro_f1"],
                "descriptive_transfer_gap": seen["macro_f1"] - unseen["macro_f1"],
                "importance_validation": imp_val, "importance_unseen": imp_test,
                "top_family_agrees": top_val == top_test,
                "caution": "descriptive; different populations; flat/tied importance is not reliable stability"})
    dump(output / "rq2_transfer.json", rq2)
    test = df[df.partition == "test_unseen"]
    rq3 = []
    keys = [k for k in fitted if k.endswith(":full")]
    for key in keys:
        rq3.append({"model": key, "primary": key == primary,
            "paired_difference_vs_primary_interval": group_interval(test,
                predictions[key, "test_unseen"], predictions[primary, "test_unseen"], seed)})
    dump(output / "rq3_comparison.json", rq3)
    rows = ["# Synthetic smoke-test results" if kind == "synthetic" else "# Exploratory imported-data results",
        "", "Engineering validation only. No H1/H2/H3 claim is established. Intervals are descriptive, unadjusted cluster bootstraps.",
        "", f"Input SHA-256: `{sha(input_path)}`. Seed: {seed}. Primary selected on validation: **{primary}**.",
        "", "| Candidate (full features) | Known-group F1 | Unseen-group F1 | Human false-AI rate (unseen) |",
        "| --- | --- | --- | --- |"]
    for key in keys:
        seen = next(m for m in metrics if m["model"] == key and m["partition"] == "test_seen")
        unseen = next(m for m in metrics if m["model"] == key and m["partition"] == "test_unseen")
        rows.append(f"| {key} | {seen['macro_f1']:.3f} | {unseen['macro_f1']:.3f} | {unseen['human_false_ai_rate']:.3f} |")
    rows += ["", "RQ1: see rq1_features.json for validation-family permutations and retrained ablations.",
             "RQ2: see rq2_transfer.json for full/reduced transfer and importance stability.",
             "RQ3: see rq3_comparison.json and metrics.json for paired candidate comparisons.",
             "", "Controls are separately labeled in predictions.csv; no binary correctness is assigned to them.",
             "The numerical-token transformer is an FT-style smoke-test implementation, not an exact published FT-Transformer replication.",
             "Model artifacts are not persisted in this version; reproduce from input, seed, source and package manifest."]
    (output / "REPORT.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    dump(output / "artifact_manifest.json", {p.name: sha(p) for p in output.iterdir() if p.is_file()})
    print("Completed:", output, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate")
    gen.add_argument("--output", required=True)
    gen.add_argument("--seed", type=int, default=19)
    check = sub.add_parser("validate")
    check.add_argument("--input", required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--input", required=True)
    execute.add_argument("--output", required=True)
    execute.add_argument("--seed", type=int, default=19)
    execute.add_argument("--allow-real", action="store_true")
    args = parser.parse_args()
    if args.command == "generate":
        fixture(args.output, args.seed)
    elif args.command == "validate":
        print(json.dumps(validate(pd.read_csv(args.input)), indent=2))
    else:
        run(args.input, args.output, args.allow_real, args.seed)


if __name__ == "__main__":
    main()
