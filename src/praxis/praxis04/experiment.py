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
        sample_seed=seed,
        sample_strategy=str(config.get("sample_strategy", "head")),
        min_train_rows_per_label=int(config.get("min_train_rows_per_label", 0)),
        min_val_rows_per_label=int(config.get("min_val_rows_per_label", 0)),
        support_fraction_per_label=float(config.get("support_fraction_per_label", 0.0)),
    )
    matrices = split_to_matrices(split)

    expert_names, expert_train, expert_val, expert_test = train_experts(config, matrices)
    if config["model"] == "Baseline-Single":
        y_proba = expert_test[:, 0, :]
        gates = np.ones((len(matrices.x_test), 1), dtype=np.float32)
    else:
        train_router_input, val_router_input, test_router_input, stage_summary, router_shape = build_router_inputs(
            config,
            matrices,
            seed,
        )
        fit_router_input = val_router_input if len(matrices.y_val) else train_router_input
        fit_experts = expert_val if len(matrices.y_val) else expert_train
        fit_y = matrices.y_val if len(matrices.y_val) else matrices.y_train
        router = build_router(config, fit_router_input, expert_train.shape[1], seed, router_shape)
        if isinstance(router, AdditiveStageGateRouter):
            router.fit(
                fit_router_input[:, : router_shape["feature_dim"]],
                fit_router_input[:, router_shape["feature_dim"] :],
                fit_experts,
                fit_y,
            )
            gates = router.predict_weights(
                test_router_input[:, : router_shape["feature_dim"]],
                test_router_input[:, router_shape["feature_dim"] :],
            )
        else:
            router.fit(fit_router_input, fit_experts, fit_y)
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
        "expert_metrics": expert_diagnostics(matrices.y_test, expert_test, expert_names, matrices.label_names),
        "metrics": metrics,
    }
    if config["model"] != "Baseline-Single":
        payload["stage_signal_summary"] = stage_summary

    write_json(output_path / "metrics.json", payload)
    write_json(output_path / "config.json", config)
    write_predictions(output_path, matrices, y_pred, y_proba, gates, expert_names)
    return payload


def train_experts(config: dict[str, Any], matrices: MatrixSplit) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    seed = int(config["seed"])
    requested = config.get("submodels", ["RF", "MLP", "BiLSTM"])
    n_classes = len(matrices.label_names)
    expert_names = []
    train_probs = []
    val_probs = []
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
        if len(matrices.x_val):
            val_probs.append(align_proba(model.predict_proba(matrices.x_val), classes, n_classes))
        test_probs.append(align_proba(model.predict_proba(matrices.x_test), classes, n_classes))

    if len(matrices.x_val):
        expert_val = np.stack(val_probs, axis=1)
    else:
        expert_val = np.empty((0, len(expert_names), n_classes), dtype=np.float32)
    return expert_names, np.stack(train_probs, axis=1), expert_val, np.stack(test_probs, axis=1)


def build_router_inputs(
    config: dict[str, Any],
    matrices: MatrixSplit,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any], dict[str, int]]:
    mode = config.get("router_input", ["features"])
    train_parts = [matrices.x_train]
    val_parts = [matrices.x_val]
    test_parts = [matrices.x_test]
    summary: dict[str, Any] = {"router_input": mode}
    stage_dim = 0

    if "predicted_stage_logits" in mode:
        clf = StageClassifier({"seed": seed, "max_iter": int(config.get("stage_max_iter", 200))})
        clf.fit(matrices.x_train, matrices.stage_train)
        train_stage = align_proba(clf.predict_proba(matrices.x_train), clf.model.classes_, len(matrices.stage_names))
        val_stage = (
            align_proba(clf.predict_proba(matrices.x_val), clf.model.classes_, len(matrices.stage_names))
            if len(matrices.x_val)
            else np.empty((0, len(matrices.stage_names)), dtype=np.float32)
        )
        test_stage = align_proba(clf.predict_proba(matrices.x_test), clf.model.classes_, len(matrices.stage_names))
        train_parts.append(train_stage.astype(np.float32))
        val_parts.append(val_stage.astype(np.float32))
        test_parts.append(test_stage.astype(np.float32))
        stage_dim = len(matrices.stage_names)
        summary["stage_classifier_train_accuracy"] = float((train_stage.argmax(axis=1) == matrices.stage_train).mean())
        if len(matrices.stage_val):
            summary["stage_classifier_val_accuracy"] = float((val_stage.argmax(axis=1) == matrices.stage_val).mean())
        summary["stage_classifier_test_accuracy"] = float((test_stage.argmax(axis=1) == matrices.stage_test).mean())
    elif "random_stage_noise" in mode:
        rng = np.random.default_rng(seed)
        train_parts.append(rng.normal(size=(len(matrices.x_train), len(matrices.stage_names))).astype(np.float32))
        val_parts.append(rng.normal(size=(len(matrices.x_val), len(matrices.stage_names))).astype(np.float32))
        test_parts.append(rng.normal(size=(len(matrices.x_test), len(matrices.stage_names))).astype(np.float32))
        stage_dim = len(matrices.stage_names)
    elif "ground_truth_stage_onehot" in mode:
        train_parts.append(onehot(matrices.stage_train, len(matrices.stage_names)))
        val_parts.append(onehot(matrices.stage_val, len(matrices.stage_names)))
        test_parts.append(onehot(matrices.stage_test, len(matrices.stage_names)))
        stage_dim = len(matrices.stage_names)

    shape = {"feature_dim": matrices.x_train.shape[1], "stage_dim": stage_dim}
    return (
        np.concatenate(train_parts, axis=1),
        np.concatenate(val_parts, axis=1),
        np.concatenate(test_parts, axis=1),
        summary,
        shape,
    )


def build_router(config: dict[str, Any], router_input: np.ndarray, n_experts: int, seed: int, shape: dict[str, int]):
    architecture = config.get("router_architecture")
    if architecture is None:
        architecture = "additive_stage" if shape.get("stage_dim", 0) > 0 else "linear"
    common = {
        "n_experts": n_experts,
        "seed": seed,
        "lr": float(config.get("router_lr", 5e-2)),
        "epochs": int(config.get("router_epochs", 120)),
        "init_temperature": float(config.get("router_init_temperature", 0.1)),
        "init_metric": str(config.get("router_init_metric", "macro_f1")),
    }
    if architecture == "additive_stage" and shape.get("stage_dim", 0) > 0:
        return AdditiveStageGateRouter(
            n_features=shape["feature_dim"],
            n_stage=shape["stage_dim"],
            stage_scale=float(config.get("router_stage_scale", 2.0)),
            class_weight=config.get("router_class_weight", "balanced"),
            **common,
        )
    return TorchGateRouter(n_inputs=router_input.shape[1], class_weight=config.get("router_class_weight", "balanced"), **common)


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


def expert_diagnostics(
    y_true: np.ndarray,
    expert_probs: np.ndarray,
    expert_names: list[str],
    label_names: list[str],
) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    for idx, expert_name in enumerate(expert_names):
        proba = expert_probs[:, idx, :]
        diagnostics[expert_name] = classification_metrics(
            y_true,
            proba.argmax(axis=1),
            y_proba=proba,
            labels=label_names,
        )
    if len(expert_names) > 1:
        best_expert = expert_probs[np.arange(len(y_true)), :, y_true].argmax(axis=1)
        oracle_pred = expert_probs[np.arange(len(y_true)), best_expert, :].argmax(axis=1)
        diagnostics["oracle_per_sample_expert"] = classification_metrics(
            y_true,
            oracle_pred,
            labels=label_names,
        )
    return diagnostics


class TorchGateRouter:
    def __init__(
        self,
        n_inputs: int,
        n_experts: int,
        seed: int,
        lr: float,
        epochs: int,
        class_weight: str | None = "balanced",
        init_temperature: float = 0.5,
        init_metric: str = "macro_f1",
    ):
        self.n_inputs = n_inputs
        self.n_experts = n_experts
        self.seed = seed
        self.lr = lr
        self.epochs = epochs
        self.class_weight = class_weight
        self.init_temperature = init_temperature
        self.init_metric = init_metric
        self.model = None

    def fit(self, x: np.ndarray, expert_probs: np.ndarray, y: np.ndarray) -> "TorchGateRouter":
        import torch
        from torch import nn

        torch.manual_seed(self.seed)
        self.model = nn.Linear(self.n_inputs, self.n_experts)
        xb = torch.from_numpy(x.astype(np.float32))
        experts = torch.from_numpy(expert_probs.astype(np.float32))
        yb = torch.from_numpy(y.astype(np.int64))
        weights = torch.from_numpy(router_class_weights(y, expert_probs.shape[2], self.class_weight))
        initial_weights = expert_prior(expert_probs, y, weights.numpy(), self.init_temperature, self.init_metric)
        with torch.no_grad():
            self.model.weight.zero_()
            self.model.bias.copy_(torch.log(torch.from_numpy(initial_weights).clamp_min(1e-8)))
        if self.epochs <= 0:
            return self
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        for _ in range(self.epochs):
            optimizer.zero_grad()
            gates = torch.softmax(self.model(xb), dim=1)
            probs = torch.einsum("ne,ned->nd", gates, experts).clamp_min(1e-8)
            per_sample_loss = -torch.log(probs[torch.arange(len(yb)), yb])
            loss = (per_sample_loss * weights[yb]).mean()
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


class AdditiveStageGateRouter:
    def __init__(
        self,
        n_features: int,
        n_stage: int,
        n_experts: int,
        seed: int,
        lr: float,
        epochs: int,
        stage_scale: float = 2.0,
        class_weight: str | None = "balanced",
        init_temperature: float = 0.5,
        init_metric: str = "macro_f1",
    ):
        self.n_features = n_features
        self.n_stage = n_stage
        self.n_experts = n_experts
        self.seed = seed
        self.lr = lr
        self.epochs = epochs
        self.stage_scale = stage_scale
        self.class_weight = class_weight
        self.init_temperature = init_temperature
        self.init_metric = init_metric
        self.model = None

    def fit(self, x: np.ndarray, stage_signal: np.ndarray, expert_probs: np.ndarray, y: np.ndarray) -> "AdditiveStageGateRouter":
        import torch
        from torch import nn

        torch.manual_seed(self.seed)

        class Router(nn.Module):
            def __init__(self, n_features: int, n_stage: int, n_experts: int, stage_scale: float):
                super().__init__()
                self.feature_gate = nn.Linear(n_features, n_experts)
                self.stage_gate = nn.Linear(n_stage, n_experts, bias=False)
                self.stage_scale = float(stage_scale)

            def forward(self, xb, sb):
                return self.feature_gate(xb) + self.stage_scale * self.stage_gate(sb)

        self.model = Router(self.n_features, self.n_stage, self.n_experts, self.stage_scale)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)
        xb = torch.from_numpy(x.astype(np.float32))
        sb = torch.from_numpy(stage_signal.astype(np.float32))
        experts = torch.from_numpy(expert_probs.astype(np.float32))
        yb = torch.from_numpy(y.astype(np.int64))
        weights = torch.from_numpy(router_class_weights(y, expert_probs.shape[2], self.class_weight))
        global_weights = expert_prior(expert_probs, y, weights.numpy(), self.init_temperature, self.init_metric)
        stage_deltas = stage_prior_deltas(
            expert_probs,
            y,
            stage_signal,
            weights.numpy(),
            global_weights,
            self.init_temperature,
            self.init_metric,
        )
        with torch.no_grad():
            self.model.feature_gate.weight.zero_()
            self.model.feature_gate.bias.copy_(torch.log(torch.from_numpy(global_weights).clamp_min(1e-8)))
            self.model.stage_gate.weight.copy_(torch.from_numpy(stage_deltas / max(self.stage_scale, 1e-6)))
        if self.epochs <= 0:
            return self
        for _ in range(self.epochs):
            optimizer.zero_grad()
            gates = torch.softmax(self.model(xb, sb), dim=1)
            probs = torch.einsum("ne,ned->nd", gates, experts).clamp_min(1e-8)
            per_sample_loss = -torch.log(probs[torch.arange(len(yb)), yb])
            loss = (per_sample_loss * weights[yb]).mean()
            loss.backward()
            optimizer.step()
        return self

    def predict_weights(self, x: np.ndarray, stage_signal: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("Router must be fit before prediction.")
        import torch

        self.model.eval()
        with torch.no_grad():
            logits = self.model(
                torch.from_numpy(x.astype(np.float32)),
                torch.from_numpy(stage_signal.astype(np.float32)),
            )
            weights = torch.softmax(logits, dim=1)
        return weights.cpu().numpy()


def router_class_weights(y: np.ndarray, n_classes: int, class_weight: str | None) -> np.ndarray:
    weights = np.ones(n_classes, dtype=np.float32)
    if class_weight != "balanced":
        return weights
    observed, counts = np.unique(y.astype(int), return_counts=True)
    if len(observed) == 0:
        return weights
    scale = len(y) / max(1, len(observed))
    for class_id, count in zip(observed, counts):
        if 0 <= class_id < n_classes and count > 0:
            weights[int(class_id)] = scale / float(count)
    weights /= max(float(weights.mean()), 1e-8)
    return weights


def expert_prior(
    expert_probs: np.ndarray,
    y: np.ndarray,
    sample_class_weights: np.ndarray,
    temperature: float,
    metric: str = "macro_f1",
) -> np.ndarray:
    n_experts = expert_probs.shape[1]
    y = y.astype(int)
    scores = []
    if metric == "nll":
        sample_weights = sample_class_weights[y]
        for expert_idx in range(n_experts):
            probs = np.clip(expert_probs[np.arange(len(y)), expert_idx, y], 1e-8, 1.0)
            scores.append(float(-(((-np.log(probs)) * sample_weights).mean())))
    elif metric == "macro_f1":
        from sklearn.metrics import f1_score

        for expert_idx in range(n_experts):
            scores.append(float(f1_score(y, expert_probs[:, expert_idx, :].argmax(axis=1), average="macro", zero_division=0)))
    else:
        raise ValueError("router_init_metric must be 'macro_f1' or 'nll'.")
    scores_arr = np.asarray(scores, dtype=np.float32)
    scale = max(float(temperature), 1e-6)
    logits = scores_arr / scale
    logits -= logits.max()
    weights = np.exp(logits)
    weights /= weights.sum()
    return weights.astype(np.float32)


def stage_prior_deltas(
    expert_probs: np.ndarray,
    y: np.ndarray,
    stage_signal: np.ndarray,
    sample_class_weights: np.ndarray,
    global_weights: np.ndarray,
    temperature: float,
    metric: str,
) -> np.ndarray:
    n_experts = expert_probs.shape[1]
    n_stage = stage_signal.shape[1]
    deltas = np.zeros((n_experts, n_stage), dtype=np.float32)
    if n_stage == 0 or len(y) == 0:
        return deltas
    stage_ids = stage_signal.argmax(axis=1)
    global_log = np.log(np.clip(global_weights, 1e-8, 1.0))
    for stage_idx in range(n_stage):
        mask = stage_ids == stage_idx
        if not np.any(mask):
            continue
        stage_weights = expert_prior(
            expert_probs[mask],
            y[mask],
            sample_class_weights,
            temperature,
            metric,
        )
        deltas[:, stage_idx] = np.log(np.clip(stage_weights, 1e-8, 1.0)) - global_log
    return deltas


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
