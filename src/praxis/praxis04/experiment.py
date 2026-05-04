from __future__ import annotations

import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from praxis.praxis04.data_loader import MatrixSplit, load_preprocessed_split, split_to_matrices
from praxis.praxis04.evaluate import classification_metrics, fpr_at_recall, router_entropy
from praxis.praxis04.reproducibility import json_safe, seed_everything
from praxis.praxis04.stage_classifier import StageClassifier
from praxis.praxis04.submodels import BiLSTMModel, MLPModel, RFModel


def run_experiment(config: dict[str, Any], output_dir: str | Path) -> dict[str, Any]:
    seed = int(config["seed"])
    seed_state = seed_everything(seed, deterministic_torch=bool(config.get("deterministic_torch", True)))
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    data_dir = Path(config.get("data_dir", "data/cic-ids-2018"))
    sample_rows = config.get("sample_rows_per_file")
    split = load_preprocessed_split(
        data_dir,
        sample_rows_per_file=int(sample_rows) if sample_rows else None,
        chunksize=int(config.get("chunksize", 200_000)),
    )
    matrices = split_to_matrices(split)

    expert_names, expert_train, expert_test = train_experts(config, matrices)
    if config["model"] == "Baseline-Single":
        y_proba = expert_test[:, 0, :]
        gates = np.ones((len(matrices.x_test), 1), dtype=np.float32)
    else:
        train_router_input, test_router_input, stage_summary = build_router_inputs(config, matrices, seed)
        router = TorchGateRouter(
            n_inputs=train_router_input.shape[1],
            n_experts=expert_train.shape[1],
            seed=seed,
            lr=float(config.get("router_lr", 5e-2)),
            epochs=int(config.get("router_epochs", 120)),
        )
        router.fit(train_router_input, expert_train, matrices.y_train)
        gates = router.predict_weights(test_router_input)
        y_proba = combine_experts(expert_test, gates)

    y_pred = y_proba.argmax(axis=1)
    metrics = classification_metrics(
        matrices.y_test,
        y_pred,
        y_proba=y_proba,
        labels=matrices.label_names,
    )
    benign_id = matrices.label_names.index("Benign") if "Benign" in matrices.label_names else 0
    metrics["fpr_at_95_recall_benign"] = fpr_at_recall(
        (matrices.y_test == benign_id).astype(int),
        y_proba[:, benign_id],
        target_recall=0.95,
    )
    entropy = router_entropy(gates)
    metrics["router_entropy_mean"] = float(entropy.mean())
    metrics["router_entropy_by_stage"] = {
        stage: float(entropy[matrices.stage_test == idx].mean())
        for idx, stage in enumerate(matrices.stage_names)
        if np.any(matrices.stage_test == idx)
    }

    payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_name": config["name"],
        "model": config["model"],
        "seed": seed,
        "git_sha": git_sha(),
        "environment": environment_summary(),
        "seed_state": seed_state.__dict__,
        "data_summary": matrices.summary,
        "feature_count": len(matrices.feature_names),
        "label_names": matrices.label_names,
        "stage_names": matrices.stage_names,
        "expert_names": expert_names,
        "metrics": metrics,
    }
    if config["model"] != "Baseline-Single":
        payload["stage_signal_summary"] = stage_summary

    write_json(output_path / "metrics.json", payload)
    write_json(output_path / "config.json", config)
    write_predictions(output_path, matrices, y_pred, y_proba, gates, expert_names)
    return payload


def train_experts(config: dict[str, Any], matrices: MatrixSplit) -> tuple[list[str], np.ndarray, np.ndarray]:
    seed = int(config["seed"])
    requested = config.get("submodels", ["RF", "MLP", "BiLSTM"])
    n_classes = len(matrices.label_names)
    expert_names = []
    train_probs = []
    test_probs = []

    for name in requested:
        if name == "RF":
            model = RFModel(
                {
                    "n_estimators": int(config.get("rf_n_estimators", 120)),
                    "max_depth": config.get("rf_max_depth", None),
                    "random_state": seed,
                    "n_jobs": int(config.get("n_jobs", 1)),
                    "class_weight": config.get("rf_class_weight", "balanced"),
                }
            )
        elif name == "MLP":
            model = MLPModel(
                {
                    "hidden_layer_sizes": config.get("mlp_hidden_layers", [128, 64]),
                    "max_iter": int(config.get("mlp_max_iter", 100)),
                    "random_state": seed,
                    "early_stopping": bool(config.get("mlp_early_stopping", True)),
                }
            )
        elif name == "BiLSTM":
            model = BiLSTMModel(
                {
                    "seed": seed,
                    "seq_len": int(config.get("bilstm_seq_len", 4)),
                    "hidden_dim": int(config.get("bilstm_hidden_dim", 32)),
                    "epochs": int(config.get("bilstm_epochs", 8)),
                    "batch_size": int(config.get("bilstm_batch_size", 128)),
                    "lr": float(config.get("bilstm_lr", 1e-3)),
                }
            )
        else:
            raise ValueError(f"Unsupported submodel: {name}")

        model.fit(matrices.x_train, matrices.y_train)
        expert_names.append(name)
        classes = getattr(model, "classes_", None)
        if classes is None:
            classes = getattr(getattr(model, "model", None), "classes_", None)
        train_probs.append(align_proba(model.predict_proba(matrices.x_train), classes, n_classes))
        test_probs.append(align_proba(model.predict_proba(matrices.x_test), classes, n_classes))

    return expert_names, np.stack(train_probs, axis=1), np.stack(test_probs, axis=1)


def build_router_inputs(config: dict[str, Any], matrices: MatrixSplit, seed: int) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    mode = config.get("router_input", ["features"])
    train_parts = [matrices.x_train]
    test_parts = [matrices.x_test]
    summary: dict[str, Any] = {"router_input": mode}

    if "predicted_stage_logits" in mode:
        clf = StageClassifier({"seed": seed, "max_iter": int(config.get("stage_max_iter", 200))})
        clf.fit(matrices.x_train, matrices.stage_train)
        train_stage = align_proba(clf.predict_proba(matrices.x_train), clf.model.classes_, len(matrices.stage_names))
        test_stage = align_proba(clf.predict_proba(matrices.x_test), clf.model.classes_, len(matrices.stage_names))
        train_parts.append(train_stage.astype(np.float32))
        test_parts.append(test_stage.astype(np.float32))
        summary["stage_classifier_train_accuracy"] = float((train_stage.argmax(axis=1) == matrices.stage_train).mean())
        summary["stage_classifier_test_accuracy"] = float((test_stage.argmax(axis=1) == matrices.stage_test).mean())
    elif "random_stage_noise" in mode:
        rng = np.random.default_rng(seed)
        train_parts.append(rng.normal(size=(len(matrices.x_train), len(matrices.stage_names))).astype(np.float32))
        test_parts.append(rng.normal(size=(len(matrices.x_test), len(matrices.stage_names))).astype(np.float32))
    elif "ground_truth_stage_onehot" in mode:
        train_parts.append(onehot(matrices.stage_train, len(matrices.stage_names)))
        test_parts.append(onehot(matrices.stage_test, len(matrices.stage_names)))

    return np.concatenate(train_parts, axis=1), np.concatenate(test_parts, axis=1), summary


def align_proba(proba: np.ndarray, classes: Any, n_classes: int) -> np.ndarray:
    proba = np.asarray(proba, dtype=np.float32)
    if proba.shape[1] == n_classes and classes is None:
        return proba
    if classes is None:
        classes = np.arange(proba.shape[1])
    aligned = np.zeros((proba.shape[0], n_classes), dtype=np.float32)
    for idx, class_id in enumerate(np.asarray(classes, dtype=int)):
        if 0 <= class_id < n_classes:
            aligned[:, class_id] = proba[:, idx]
    row_sum = aligned.sum(axis=1, keepdims=True)
    return np.divide(aligned, row_sum, out=np.full_like(aligned, 1.0 / n_classes), where=row_sum > 0)


def onehot(values: np.ndarray, n_classes: int) -> np.ndarray:
    output = np.zeros((len(values), n_classes), dtype=np.float32)
    output[np.arange(len(values)), values.astype(int)] = 1.0
    return output


def combine_experts(expert_probs: np.ndarray, gates: np.ndarray) -> np.ndarray:
    return np.einsum("ne,ned->nd", gates, expert_probs)


class TorchGateRouter:
    def __init__(self, n_inputs: int, n_experts: int, seed: int, lr: float, epochs: int):
        self.n_inputs = n_inputs
        self.n_experts = n_experts
        self.seed = seed
        self.lr = lr
        self.epochs = epochs
        self.model = None

    def fit(self, x: np.ndarray, expert_probs: np.ndarray, y: np.ndarray) -> "TorchGateRouter":
        import torch
        from torch import nn

        torch.manual_seed(self.seed)
        self.model = nn.Linear(self.n_inputs, self.n_experts)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        xb = torch.from_numpy(x.astype(np.float32))
        experts = torch.from_numpy(expert_probs.astype(np.float32))
        yb = torch.from_numpy(y.astype(np.int64))
        for _ in range(self.epochs):
            optimizer.zero_grad()
            gates = torch.softmax(self.model(xb), dim=1)
            probs = torch.einsum("ne,ned->nd", gates, experts).clamp_min(1e-8)
            loss = -torch.log(probs[torch.arange(len(yb)), yb]).mean()
            loss.backward()
            optimizer.step()
        return self

    def predict_weights(self, x: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Router must be fit before prediction.")
        import torch

        self.model.eval()
        with torch.no_grad():
            weights = torch.softmax(self.model(torch.from_numpy(x.astype(np.float32))), dim=1)
        return weights.cpu().numpy()


def write_predictions(
    output_path: Path,
    matrices: MatrixSplit,
    y_pred: np.ndarray,
    y_proba: np.ndarray,
    gates: np.ndarray,
    expert_names: list[str],
) -> None:
    np.savez_compressed(
        output_path / "predictions.npz",
        y_true=matrices.y_test,
        y_pred=y_pred,
        y_proba=y_proba.astype(np.float32),
        stage_true=matrices.stage_test,
        gates=gates.astype(np.float32),
    )
    preview_count = min(25, len(y_pred))
    write_json(
        output_path / "predictions_preview.json",
        {
            "preview_count": preview_count,
            "y_true": matrices.y_test[:preview_count].tolist(),
            "y_pred": y_pred[:preview_count].tolist(),
            "y_proba": y_proba[:preview_count].tolist(),
            "stage_true": matrices.stage_test[:preview_count].tolist(),
            "gates": gates[:preview_count].tolist(),
            "expert_names": expert_names,
            "label_names": matrices.label_names,
            "stage_names": matrices.stage_names,
            "full_predictions_file": "predictions.npz",
        },
    )


def git_sha() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return None


def environment_summary() -> dict[str, Any]:
    payload = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import torch

        payload["torch"] = torch.__version__
        payload["cuda_available"] = bool(torch.cuda.is_available())
        payload["cuda_device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except Exception:
        payload["torch"] = None
        payload["cuda_available"] = False
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
