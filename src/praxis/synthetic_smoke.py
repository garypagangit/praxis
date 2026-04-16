from __future__ import annotations

import json
import platform
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.datasets import make_classification
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


DEFAULTS = {
    "pipeline": "synthetic_smoke",
    "run_name": "synthetic-smoke",
    "output_dir": "runs",
    "notes": "Synthetic smoke test for validating a fresh Praxis environment.",
    "random_seed": 42,
    "n_samples": 2400,
    "n_features": 24,
    "n_informative": 12,
    "n_redundant": 4,
    "n_classes": 4,
    "class_weights": [0.55, 0.2, 0.15, 0.1],
    "test_size": 0.2,
    "val_size": 0.2,
    "enabled_models": ["LogisticRegression", "MLP"],
    "max_iter": 120,
    "hidden_layers": [64, 32],
}


def resolve_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(repo_root: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def detect_environment() -> dict[str, Any]:
    return {
        "cwd": str(Path.cwd()),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }


def coerce_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): coerce_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [coerce_json(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    return str(value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(coerce_json(payload), indent=2), encoding="utf-8")


def merge_settings(settings: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULTS)
    merged.update(settings)
    return merged


def build_models(settings: dict[str, Any]) -> dict[str, Pipeline]:
    max_iter = int(settings["max_iter"])
    hidden_layers = tuple(int(value) for value in settings.get("hidden_layers", [64, 32]))

    catalog: dict[str, Pipeline] = {
        "LogisticRegression": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        max_iter=max_iter,
                        random_state=int(settings["random_seed"]),
                    ),
                ),
            ]
        ),
        "MLP": Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=hidden_layers,
                        max_iter=max_iter,
                        early_stopping=False,
                        random_state=int(settings["random_seed"]),
                    ),
                ),
            ]
        ),
    }

    requested = settings.get("enabled_models", list(catalog))
    invalid = sorted(set(requested) - set(catalog))
    if invalid:
        raise ValueError(f"Unsupported synthetic smoke model(s): {', '.join(invalid)}")
    return {name: catalog[name] for name in requested}


def evaluate_model(name: str, model: Pipeline, x_train: np.ndarray, x_test: np.ndarray, y_train: np.ndarray, y_test: np.ndarray) -> dict[str, Any]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=ConvergenceWarning)
        model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    report = classification_report(y_test, predictions, output_dict=True, zero_division=0)

    return {
        "model_name": name,
        "accuracy": accuracy_score(y_test, predictions),
        "macro_f1": f1_score(y_test, predictions, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_test, predictions, average="weighted", zero_division=0),
        "macro_precision": precision_score(y_test, predictions, average="macro", zero_division=0),
        "macro_recall": recall_score(y_test, predictions, average="macro", zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "classification_report": report,
    }


def run_synthetic_smoke(settings: dict[str, Any]) -> Path:
    merged = merge_settings(settings)
    repo_root = resolve_repo_root()
    run_dir = resolve_path(repo_root, str(merged["output_dir"])) / str(merged["run_name"])
    run_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "settings": merged,
        "environment": detect_environment(),
    }
    write_json(run_dir / "metadata.json", metadata)

    x, y = make_classification(
        n_samples=int(merged["n_samples"]),
        n_features=int(merged["n_features"]),
        n_informative=int(merged["n_informative"]),
        n_redundant=int(merged["n_redundant"]),
        n_classes=int(merged["n_classes"]),
        weights=list(merged["class_weights"]),
        class_sep=1.4,
        random_state=int(merged["random_seed"]),
    )

    x_train_val, x_test, y_train_val, y_test = train_test_split(
        x,
        y,
        test_size=float(merged["test_size"]),
        stratify=y,
        random_state=int(merged["random_seed"]),
    )
    relative_val_size = float(merged["val_size"]) / (1.0 - float(merged["test_size"]))
    x_train, x_val, y_train, y_val = train_test_split(
        x_train_val,
        y_train_val,
        test_size=relative_val_size,
        stratify=y_train_val,
        random_state=int(merged["random_seed"]),
    )

    results: dict[str, Any] = {}
    for model_name, model in build_models(merged).items():
        print(f"Training synthetic smoke model: {model_name}")
        val_metrics = evaluate_model(model_name, model, x_train, x_val, y_train, y_val)
        test_metrics = evaluate_model(model_name, model, x_train_val, x_test, y_train_val, y_test)
        results[model_name] = {
            "validation": val_metrics,
            "test": test_metrics,
        }

    summary = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": merged["pipeline"],
        "dataset": {
            "n_samples": int(merged["n_samples"]),
            "n_features": int(merged["n_features"]),
            "n_classes": int(merged["n_classes"]),
            "train_size": int(len(x_train)),
            "val_size": int(len(x_val)),
            "test_size": int(len(x_test)),
        },
        "results": results,
    }
    write_json(run_dir / "results-summary.json", summary)
    (run_dir / "README.txt").write_text(
        "This folder contains results for the synthetic Praxis smoke test.\n",
        encoding="utf-8",
    )
    return run_dir
