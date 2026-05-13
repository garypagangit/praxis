from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_sequence(rows: list[dict[str, Any]], top_k: int) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["_timestamp"] = pd.to_numeric(frame["timestamp_nanos"], errors="coerce")
    frame = frame.sort_values(["_timestamp", "sequence", "record_index"]).reset_index(
        drop=True
    )
    top_events = {
        name for name, _ in Counter(frame["datum_type"].astype(str)).most_common(top_k)
    }
    frame["event_label"] = (
        frame["datum_type"]
        .astype(str)
        .map(lambda value: value if value in top_events else "OTHER")
    )
    frame["prev_event"] = frame["event_label"].shift(1).fillna("START")
    frame["prev2_event"] = frame["event_label"].shift(2).fillna("START")
    frame["delta_ns"] = frame["_timestamp"].diff().fillna(0).clip(lower=0)
    return frame.iloc[2:].reset_index(drop=True)


def featurize(frame: pd.DataFrame) -> list[dict[str, Any]]:
    features = []
    for row in frame.to_dict("records"):
        subject = str(row.get("subject_uuid") or "missing")
        obj = str(row.get("object_uuid") or "missing")
        features.append(
            {
                "prev_event": row["prev_event"],
                "prev2_event": row["prev2_event"],
                "subject_bucket": hash(subject) % 256,
                "object_bucket": hash(obj) % 512,
                "source_file": row.get("source_file", "unknown"),
                "delta_bucket": int(np.log1p(float(row["delta_ns"])) // 2),
            }
        )
    return features


def transition_predict(train_labels: pd.Series, test_prev: pd.Series) -> list[str]:
    transitions: dict[str, Counter[str]] = defaultdict(Counter)
    prev = train_labels.shift(1).fillna("START")
    for prev_event, event in zip(prev, train_labels):
        transitions[str(prev_event)][str(event)] += 1
    majority = train_labels.value_counts().idxmax()
    preds = []
    for event in test_prev.astype(str):
        if transitions[event]:
            preds.append(transitions[event].most_common(1)[0][0])
        else:
            preds.append(majority)
    return preds


def metrics(
    y_true: list[str] | pd.Series, y_pred: list[str] | np.ndarray
) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
    }


def render_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Cadets TGN Next-Event Pilot",
        "",
        "Generated: 2026-05-09",
        "",
        "## Decision",
        "",
        f"Status: **{summary['decision']}**.",
        "",
        "## Chronological Results",
        "",
        "| Method | Accuracy | Macro F1 |",
        "|---|---:|---:|",
    ]
    for row in summary["results"]:
        lines.append(
            f"| `{row['method']}` | `{row['accuracy']:.4f}` | `{row['macro_f1']:.4f}` |"
        )
    lines.extend(["", "## Recommendation", "", summary["recommendation"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-dir", type=Path, default=Path("tmp") / "cadets_edge_sample"
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("runs") / "cadets-tgn-next-event-pilot-20260509",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports")
        / "continuous_time_tgn_apt_provenance"
        / "CADETS_TGN_NEXT_EVENT_PILOT_20260509.md",
    )
    parser.add_argument("--top-k-events", type=int, default=12)
    args = parser.parse_args()

    rows = read_jsonl(args.input_dir / "edges.jsonl")
    frame = build_sequence(rows, args.top_k_events)
    n = len(frame)
    train_end = int(n * 0.70)
    val_end = int(n * 0.85)
    train = frame.iloc[:train_end].reset_index(drop=True)
    test = frame.iloc[val_end:].reset_index(drop=True)

    majority = train["event_label"].value_counts().idxmax()
    majority_pred = [majority] * len(test)
    transition_pred = transition_predict(train["event_label"], test["prev_event"])

    vectorizer = DictVectorizer(sparse=True)
    x_train = vectorizer.fit_transform(featurize(train))
    x_test = vectorizer.transform(featurize(test))
    clf = LogisticRegression(max_iter=500, class_weight="balanced", n_jobs=-1)
    clf.fit(x_train, train["event_label"])
    model_pred = clf.predict(x_test)

    results = [
        {"method": "majority", **metrics(test["event_label"], majority_pred)},
        {
            "method": "previous-event transition",
            **metrics(test["event_label"], transition_pred),
        },
        {
            "method": "logistic temporal/hash features",
            **metrics(test["event_label"], model_pred),
        },
    ]
    best_baseline = max(results[0]["macro_f1"], results[1]["macro_f1"])
    gain = results[2]["macro_f1"] - best_baseline
    pass_gate = gain >= 0.03 and results[2]["macro_f1"] >= 0.20
    summary = {
        "decision": (
            "PASS - TEMPORAL PREDICTION SIGNAL"
            if pass_gate
            else "WEAK - TEMPORAL PREDICTION SIGNAL"
        ),
        "rows": int(n),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "results": results,
        "macro_f1_gain_vs_best_baseline": float(gain),
        "recommendation": (
            "Proceed to a tiny TGN/temporal-memory pilot; simple temporal/hash features already beat static baselines."
            if pass_gate
            else "Do not spend GPU on TGN yet; build richer windows or labels first."
        ),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(args.out_dir / "results.csv", index=False)
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_report(args.report, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
