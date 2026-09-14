from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import FeatureUnion, Pipeline


LETTERS_FOUR = ("A", "B", "C", "D")
LETTERS_FIVE = ("A", "B", "C", "D", "E")
ROUTER_THRESHOLD = 0.90
RANDOM_STATE = 68031
EXPECTED_QUERY_KEYS = {"id", "question", "options"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n")


def query_text(question: str, options: dict[str, str], letters: tuple[str, ...]) -> str:
    return " [OPT] ".join([question, *[options[letter] for letter in letters]])


def training_data(path: Path) -> tuple[list[str], np.ndarray, list[str]]:
    columns = [
        "URL",
        "Question",
        "Option A",
        "Option B",
        "Option C",
        "Option D",
    ]
    frame = pd.read_parquet(path, columns=columns)
    if len(frame) != 2_500:
        raise ValueError(f"Expected 2,500 CTIBench rows, found {len(frame)}")
    texts: list[str] = []
    labels: list[int] = []
    ids: list[str] = []
    for index, row in frame.iterrows():
        options = {letter: str(row[f"Option {letter}"]) for letter in LETTERS_FOUR}
        texts.append(query_text(str(row["Question"]), options, LETTERS_FOUR))
        labels.append(
            int(
                bool(
                    re.match(
                        r"^https?://attack\.mitre\.org/techniques/",
                        str(row["URL"]),
                        flags=re.I,
                    )
                )
            )
        )
        ids.append(f"ctibench_{index}")
    label_array = np.asarray(labels, dtype=np.int8)
    if int(label_array.sum()) != 1_578:
        raise ValueError(f"Expected 1,578 positive training rows, found {label_array.sum()}")
    return texts, label_array, ids


def target_data(path: Path) -> tuple[list[str], list[str]]:
    rows = read_jsonl(path)
    texts: list[str] = []
    ids: list[str] = []
    for row in rows:
        if set(row) != EXPECTED_QUERY_KEYS:
            raise ValueError(
                f"Target query {row.get('id')} violates exact query allowlist: {sorted(row)}"
            )
        options = row.get("options")
        if not isinstance(options, dict) or tuple(options) != LETTERS_FIVE:
            raise ValueError(f"Target query {row.get('id')} must contain ordered A-E options")
        texts.append(query_text(str(row["question"]), options, LETTERS_FIVE))
        ids.append(str(row["id"]))
    if len(ids) != len(set(ids)):
        raise ValueError("Target query IDs are not unique")
    return texts, ids


def build_router() -> CalibratedClassifierCV:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=2,
                    max_features=40_000,
                    sublinear_tf=True,
                    lowercase=True,
                    norm="l2",
                ),
            ),
            (
                "char_wb",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=2,
                    max_features=60_000,
                    sublinear_tf=True,
                    lowercase=True,
                    norm="l2",
                ),
            ),
        ]
    )
    base_pipeline = Pipeline(
        [
            ("features", features),
            (
                "classifier",
                LogisticRegression(
                    penalty="l2",
                    C=1.0,
                    solver="liblinear",
                    class_weight="balanced",
                    max_iter=2_000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]
    )
    # The complete vectorizer+classifier pipeline is the calibrated estimator.
    # CalibratedClassifierCV therefore refits both vectorizers and the logistic
    # classifier independently inside every calibration fold.
    return CalibratedClassifierCV(
        estimator=base_pipeline,
        method="sigmoid",
        cv=StratifiedKFold(
            n_splits=5,
            shuffle=True,
            random_state=RANDOM_STATE,
        ),
        ensemble=True,
    )


def fitted_pipeline(calibrated: Any) -> Pipeline:
    estimator = getattr(calibrated, "estimator", None)
    if not isinstance(estimator, Pipeline):
        raise TypeError("Calibration fold does not contain a fitted Pipeline")
    return estimator


def fold_vocabulary_hashes(router: CalibratedClassifierCV) -> list[dict[str, Any]]:
    hashes: list[dict[str, Any]] = []
    for index, calibrated in enumerate(router.calibrated_classifiers_):
        pipeline = fitted_pipeline(calibrated)
        feature_union = pipeline.named_steps["features"]
        by_name = dict(feature_union.transformer_list)
        hashes.append(
            {
                "fold": index,
                "word_vocabulary_sha256": sha256_json(
                    {
                        str(token): int(index)
                        for token, index in by_name["word"].vocabulary_.items()
                    }
                ),
                "char_wb_vocabulary_sha256": sha256_json(
                    {
                        str(token): int(index)
                        for token, index in by_name["char_wb"].vocabulary_.items()
                    }
                ),
                "classifier_coef_sha256": hashlib.sha256(
                    pipeline.named_steps["classifier"].coef_.tobytes()
                ).hexdigest(),
            }
        )
    if len(hashes) != 5:
        raise ValueError(f"Expected five fitted calibration pipelines, found {len(hashes)}")
    return hashes


def assignments(
    router: CalibratedClassifierCV,
    texts: list[str],
    ids: list[str],
) -> list[dict[str, Any]]:
    positive_index = list(router.classes_).index(1)
    probabilities = router.predict_proba(texts)[:, positive_index]
    return [
        {
            "id": row_id,
            "p_eligible": float(probability),
            "route_relationship_evidence": bool(probability >= ROUTER_THRESHOLD),
        }
        for row_id, probability in zip(ids, probabilities, strict=True)
    ]


def fit_and_assign(
    ctibench_parquet: Path,
    target_queries: Path,
    sensitivity_queries: Path | None,
    model_output: Path,
    assignments_output: Path,
    sensitivity_assignments_output: Path | None,
    audit_output: Path,
) -> dict[str, Any]:
    train_texts, train_labels, train_ids = training_data(ctibench_parquet)
    target_texts, target_ids = target_data(target_queries)
    router = build_router()
    router.fit(train_texts, train_labels)
    target_assignments = assignments(router, target_texts, target_ids)

    model_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(router, model_output, compress=3)
    write_jsonl(assignments_output, target_assignments)
    sensitivity_record: dict[str, Any] | None = None
    if sensitivity_queries is not None:
        if sensitivity_assignments_output is None:
            raise ValueError("Sensitivity output is required with sensitivity queries")
        sensitivity_texts, sensitivity_ids = target_data(sensitivity_queries)
        sensitivity_rows = assignments(router, sensitivity_texts, sensitivity_ids)
        write_jsonl(sensitivity_assignments_output, sensitivity_rows)
        sensitivity_record = {
            "queries_path": str(sensitivity_queries),
            "queries_sha256": sha256_file(sensitivity_queries),
            "rows": len(sensitivity_ids),
            "assignments_path": str(sensitivity_assignments_output),
            "assignments_sha256": sha256_file(sensitivity_assignments_output),
        }

    audit: dict[str, Any] = {
        "status": "assignments_frozen_without_target_truth_or_router_label_metrics",
        "target_truth_read": False,
        "target_router_label_metrics_computed": False,
        "threshold_sweep_performed": False,
        "router_threshold": ROUTER_THRESHOLD,
        "random_state": RANDOM_STATE,
        "calibration": {
            "wrapper": "CalibratedClassifierCV",
            "wrapped_estimator": "Pipeline(FeatureUnion(word,char_wb),LogisticRegression)",
            "method": "sigmoid",
            "ensemble": True,
            "cv": "StratifiedKFold(n_splits=5,shuffle=True,random_state=68031)",
            "fold_refits_complete_pipeline": True,
        },
        "training": {
            "rows": len(train_texts),
            "positive": int(train_labels.sum()),
            "negative": int(len(train_labels) - train_labels.sum()),
            "training_id_sha256": sha256_json(train_ids),
            "ctibench_parquet": str(ctibench_parquet),
            "ctibench_parquet_sha256": sha256_file(ctibench_parquet),
        },
        "target": {
            "queries_path": str(target_queries),
            "queries_sha256": sha256_file(target_queries),
            "rows": len(target_ids),
            "target_id_sha256": sha256_json(target_ids),
            "assignments_path": str(assignments_output),
            "assignments_sha256": sha256_file(assignments_output),
            "accept_count_withheld_until_registered_analysis": True,
        },
        "sensitivity": sensitivity_record,
        "model": {
            "path": str(model_output),
            "sha256": sha256_file(model_output),
            "fold_vocabulary_hashes": fold_vocabulary_hashes(router),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    audit_output.parent.mkdir(parents=True, exist_ok=True)
    audit_output.write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ctibench-parquet", type=Path, required=True)
    parser.add_argument("--target-queries", type=Path, required=True)
    parser.add_argument("--sensitivity-queries", type=Path)
    parser.add_argument("--model-output", type=Path, required=True)
    parser.add_argument("--assignments-output", type=Path, required=True)
    parser.add_argument("--sensitivity-assignments-output", type=Path)
    parser.add_argument("--audit-output", type=Path, required=True)
    args = parser.parse_args()
    audit = fit_and_assign(
        ctibench_parquet=args.ctibench_parquet,
        target_queries=args.target_queries,
        sensitivity_queries=args.sensitivity_queries,
        model_output=args.model_output,
        assignments_output=args.assignments_output,
        sensitivity_assignments_output=args.sensitivity_assignments_output,
        audit_output=args.audit_output,
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "target_rows": audit["target"]["rows"],
                "assignments_sha256": audit["target"]["assignments_sha256"],
                "model_sha256": audit["model"]["sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
