"""Registered static native-graph development pilot; no attack labels in fitting.

This is a new small reconstruction diagnostic, not a MAGIC reproduction. Both
neural arms consume node type plus counts recomputed from the observed graph.
Consequently the MLP is message-passing-free, not independent of telemetry loss.
"""
from __future__ import annotations

import os
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import argparse
import hashlib
import json
import math
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np
import sklearn
import torch
from sklearn.ensemble import IsolationForest
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score
from torch import nn


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def synchronize(device):
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def select_device(requested):
    if requested not in ("cpu", "cuda", "auto"):
        raise ValueError("device must be cpu, cuda, or auto")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA explicitly requested but unavailable; no CPU fallback")
    return torch.device("cuda" if requested != "cpu" and torch.cuda.is_available() else "cpu")


def seed_everything(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def configure_reproducibility(threads):
    torch.set_num_threads(int(threads))
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.allow_tf32 = False
    if hasattr(torch.backends, "cuda"):
        torch.backends.cuda.matmul.allow_tf32 = False


def load_graph(path):
    """Intentionally does not load y; fitting has no label parameter."""
    with np.load(path, allow_pickle=False) as arrays:
        return {name: np.asarray(arrays[name], dtype=np.int64)
                for name in ("node_type", "src", "dst", "relation")}


def observed_features(graph, node_types, relations, keep=None):
    """Fixed-width one-hot type and log1p incoming/outgoing relation counts."""
    types = graph["node_type"]
    n = len(types)
    if np.any(types < 0) or np.any(types >= node_types):
        raise ValueError("node type outside declared dataset vocabulary")
    src, dst, rel = (graph[k] for k in ("src", "dst", "relation"))
    if not (len(src) == len(dst) == len(rel)):
        raise ValueError("edge arrays differ in length")
    if keep is not None:
        keep = np.asarray(keep, dtype=bool)
        if keep.shape != src.shape:
            raise ValueError("edge mask shape mismatch")
        src, dst, rel = src[keep], dst[keep], rel[keep]
    if len(src) and (min(src.min(), dst.min(), rel.min()) < 0 or
                     max(src.max(), dst.max()) >= n or rel.max() >= relations):
        raise ValueError("invalid edge endpoint or relation vocabulary")
    x = np.zeros((n, node_types + 2 * relations), dtype=np.float32)
    x[np.arange(n), types] = 1
    np.add.at(x, (dst, node_types + rel), 1)
    np.add.at(x, (src, node_types + relations + rel), 1)
    degree = x[:, node_types:].sum(axis=1).astype(np.int64)
    np.log1p(x[:, node_types:], out=x[:, node_types:])
    return x, degree, src, dst


def fit_scaler(paths, node_types, relations):
    width = node_types + 2 * relations
    total = np.zeros(width, dtype=np.float64)
    square = np.zeros(width, dtype=np.float64)
    count = 0
    type_counts = np.zeros(node_types, dtype=np.int64)
    for path in paths:
        graph = load_graph(path)
        features, _, _, _ = observed_features(graph, node_types, relations)
        total += features.sum(axis=0, dtype=np.float64)
        # Sum squares in bounded row chunks, avoiding a second full float64 array.
        for start in range(0, len(features), 16384):
            chunk = features[start:start + 16384].astype(np.float64)
            square += np.square(chunk).sum(axis=0)
        type_counts += np.bincount(graph["node_type"], minlength=node_types)
        count += len(features)
    if count == 0:
        raise ValueError("empty training data")
    mean = total / count
    scale = np.sqrt(np.maximum(0, square / count - mean ** 2))
    scale = np.maximum(scale, 1e-3)
    return mean.astype(np.float32), scale.astype(np.float32), type_counts


def scale_features(features, mean, scale):
    return (features - mean) / scale


class ReconstructionModel(nn.Module):
    def __init__(self, input_dim, hidden_dim=32, bottleneck_dim=8, graph=False):
        super().__init__()
        self.graph = bool(graph)
        self.first = nn.Linear(input_dim, hidden_dim)
        self.first_norm = nn.LayerNorm(hidden_dim)
        self.second = nn.Linear(hidden_dim, bottleneck_dim)
        self.second_norm = nn.LayerNorm(bottleneck_dim)
        self.decoder = nn.Sequential(nn.Linear(bottleneck_dim, hidden_dim), nn.ReLU(),
                                     nn.Linear(hidden_dim, input_dim))
        self.epsilon = nn.Parameter(torch.zeros(2)) if graph else None

    @staticmethod
    def aggregate(x, src, dst):
        result = torch.zeros_like(x)
        result.index_add_(0, dst, x[src])
        return result

    def forward(self, x, src, dst):
        if self.graph:
            x = (1 + self.epsilon[0]) * x + self.aggregate(x, src, dst)
        h = torch.relu(self.first_norm(self.first(x)))
        if self.graph:
            h = (1 + self.epsilon[1]) * h + self.aggregate(h, src, dst)
        z = self.second_norm(self.second(h))
        return self.decoder(z)


def qualify_device(device):
    """Exercise the actual architecture on CPU/CUDA, including repeated CUDA calls."""
    if device.type == "cpu":
        return {"status": "CPU_SELECTED", "cuda_parity_executed": False}
    seed_everything(90210)
    x = torch.tensor([[0.2, -0.3, 1.1, 0.4], [1.3, 0.7, -0.4, 0.5],
                      [-0.1, 0.9, 0.2, -0.8], [0.3, 0.2, 0.4, 0.7]])
    src = torch.tensor([0, 1, 0, 2, 3, 3], dtype=torch.long)
    dst = torch.tensor([1, 2, 2, 3, 0, 2], dtype=torch.long)
    checks = []
    for graph in (False, True):
        model = ReconstructionModel(4, 8, 3, graph).eval()
        with torch.no_grad():
            expected = model(x, src, dst)
            model = model.to(device)
            actual = model(x.to(device), src.to(device), dst.to(device)).cpu()
            again = model(x.to(device), src.to(device), dst.to(device)).cpu()
        difference = float((expected - actual).abs().max())
        repeat = bool(torch.equal(actual, again))
        parity = bool(torch.allclose(expected, actual, rtol=1e-4, atol=1e-5))
        model.train()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        optimizer.zero_grad(set_to_none=True)
        reconstructed = model(x.to(device), src.to(device), dst.to(device))
        loss = torch.mean((reconstructed - x.to(device)) ** 2)
        loss.backward()
        finite_gradients = all(parameter.grad is None or torch.isfinite(parameter.grad).all().item()
                               for parameter in model.parameters())
        optimizer.step()
        synchronize(device)
        checks.append({"arm": "gin" if graph else "mlp", "max_absolute_error": difference,
                       "cpu_cuda_allclose": parity, "cuda_repeat_exact": repeat,
                       "deterministic_backward_optimizer_step": True,
                       "finite_gradients": finite_gradients})
        if not parity or not repeat or not finite_gradients:
            raise RuntimeError("GPU qualification failed: " + json.dumps(checks[-1]))
    return {"status": "PASS", "cuda_parity_executed": True, "rtol": 1e-4,
            "atol": 1e-5, "checks": checks}


def fit_neural(paths, node_types, relations, mean, scale, config, seed, arm, device):
    seed_everything(seed)
    model = ReconstructionModel(len(mean), config["hidden_dim"],
                                config["bottleneck_dim"], arm == "gin").to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"],
                                 weight_decay=config["weight_decay"])
    rng = np.random.default_rng(seed)
    losses = []
    model.train()
    synchronize(device)
    started = time.perf_counter()
    for epoch in range(config["epochs"]):
        epoch_losses = []
        for path in paths:
            graph = load_graph(path)
            features, _, src, dst = observed_features(graph, node_types, relations)
            features = scale_features(features, mean, scale)
            root = rng.choice(len(features), min(len(features), config["max_loss_nodes"]), replace=False)
            if arm == "mlp":
                # MLP needs no graph context; use exactly the sampled loss roots.
                x = torch.from_numpy(features[root]).to(device)
                source = target = torch.empty(0, dtype=torch.long, device=device)
                loss_root = slice(None)
            else:
                # GIN keeps the entire original context; only its loss is sampled.
                x = torch.from_numpy(features).to(device)
                source = torch.from_numpy(src).to(device)
                target = torch.from_numpy(dst).to(device)
                loss_root = torch.from_numpy(root).to(device)
            optimizer.zero_grad(set_to_none=True)
            noisy = x * (torch.rand_like(x) >= config["feature_mask_rate"])
            predicted = model(noisy, source, target)
            loss = torch.mean((predicted[loss_root] - x[loss_root]) ** 2)
            if not torch.isfinite(loss):
                raise RuntimeError(f"nonfinite {arm} training loss")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()
            epoch_losses.append(float(loss.detach().cpu()))
            del graph, features, x, noisy, predicted, loss, source, target
        losses.append(float(np.mean(epoch_losses)))
    synchronize(device)
    seconds = time.perf_counter() - started
    model.eval()
    return model, {"fit_seconds": seconds, "epoch_mean_loss": losses,
                   "sampled_roots_per_graph_step_cap": config["max_loss_nodes"],
                   "graph_context": "all retained edges" if arm == "gin" else "none"}


def score_neural(model, features, src, dst, device, batch_size=32768):
    synchronize(device)
    started = time.perf_counter()
    with torch.no_grad():
        if model.graph:
            x = torch.from_numpy(features).to(device)
            source = torch.from_numpy(src).to(device)
            target = torch.from_numpy(dst).to(device)
            score = torch.mean((model(x, source, target) - x) ** 2, dim=1).cpu().numpy()
        else:
            parts = []
            empty = torch.empty(0, dtype=torch.long, device=device)
            for start in range(0, len(features), batch_size):
                x = torch.from_numpy(features[start:start + batch_size]).to(device)
                parts.append(torch.mean((model(x, empty, empty) - x) ** 2, dim=1).cpu().numpy())
            score = np.concatenate(parts)
    synchronize(device)
    if not np.all(np.isfinite(score)):
        raise RuntimeError("nonfinite reconstruction anomaly scores")
    return score, time.perf_counter() - started


def fit_forest(paths, node_types, relations, mean, scale, config, seed):
    rng = np.random.default_rng(seed)
    samples = []
    per_graph = max(1, int(config.get("forest_fit_nodes", 100000)) // len(paths))
    started = time.perf_counter()
    for path in paths:
        graph = load_graph(path)
        features, _, _, _ = observed_features(graph, node_types, relations)
        idx = rng.choice(len(features), min(per_graph, len(features)), replace=False)
        samples.append(scale_features(features[idx], mean, scale))
    samples = np.concatenate(samples)
    model = IsolationForest(n_estimators=config["isolation_trees"],
                            max_samples=min(config["isolation_max_samples"], len(samples)),
                            random_state=seed, n_jobs=config["cpu_threads"], contamination="auto")
    model.fit(samples)
    return model, {"fit_seconds": time.perf_counter() - started,
                   "fit_rows": len(samples), "labels_used": False}


def empirical_tail(calibration, scores):
    calibration = np.sort(np.asarray(calibration, dtype=np.float64))
    scores = np.asarray(scores, dtype=np.float64)
    if not len(calibration) or not np.all(np.isfinite(calibration)) or not np.all(np.isfinite(scores)):
        raise ValueError("calibration and scores must be nonempty/finite")
    smaller = np.searchsorted(calibration, scores, side="left")
    return (1 + len(calibration) - smaller) / (len(calibration) + 1)


def margin_from_calibration(calibration, scores, alpha):
    if not 0 < alpha < 1:
        raise ValueError("calibration_fpr must be strictly between 0 and 1")
    p = empirical_tail(calibration, scores)
    return np.log(alpha / p), p


def strict_threshold(calibration, alpha):
    values = np.sort(np.asarray(calibration))
    rank = math.ceil((1 - alpha) * (len(values) + 1))
    if rank > len(values):
        return None  # +infinity: no finite score can meet the chosen empirical level.
    return float(values[max(0, rank - 1)])


def quality_selector(degree, gin_margin, mlp_margin, min_degree=2):
    select_graph = np.asarray(degree) >= min_degree
    return np.where(select_graph, gin_margin, mlp_margin), select_graph


def confidence_selector(gin_margin, mlp_margin):
    select_graph = np.abs(gin_margin) >= np.abs(mlp_margin)
    return np.where(select_graph, gin_margin, mlp_margin), select_graph


def binary_metrics(y, score, pred):
    y = np.asarray(y, dtype=np.int8)
    pred = np.asarray(pred, dtype=np.int8)
    if set(np.unique(y)) - {0, 1} or len(y) != len(pred):
        raise ValueError("invalid binary labels/predictions")
    tp = int(np.sum((y == 1) & (pred == 1)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    tn = int(np.sum((y == 0) & (pred == 0)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    negatives = tn + fp
    return {"n": len(y), "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": float(precision_score(y, pred, zero_division=0)),
            "recall": float(recall_score(y, pred, zero_division=0)),
            "f1": float(f1_score(y, pred, zero_division=0)),
            "false_positive_rate": fp / negatives if negatives else None,
            "false_positives_per_10000_benign_nodes": 10000 * fp / negatives if negatives else None,
            "average_precision": float(average_precision_score(y, score)) if tp + fn else None,
            "accuracy": (tp + tn) / len(y) if len(y) else None,
            "predicted_positive": tp + fp}


def error_changes(y, candidate, reference):
    candidate_correct = np.asarray(candidate) == y
    reference_correct = np.asarray(reference) == y
    return {"corrected_errors": int(np.sum(candidate_correct & ~reference_correct)),
            "introduced_errors": int(np.sum(~candidate_correct & reference_correct)),
            "both_wrong": int(np.sum(~candidate_correct & ~reference_correct))}


def scenario_masks(edge_count, rates, seeds):
    yield {"drop_rate": 0.0, "mask_seed": None, "name": "clean"}, None
    for seed in seeds:
        uniforms = np.random.default_rng(seed).random(edge_count)
        for rate in rates:
            if rate == 0:
                continue
            if not 0 <= rate <= 1:
                raise ValueError("invalid drop rate")
            yield {"drop_rate": float(rate), "mask_seed": int(seed),
                   "name": f"drop_{rate:g}_mask_{seed}"}, uniforms >= rate


def score_fixed(models, forest, rarity, graph, features, src, dst, device):
    scores, timing = {}, {}
    for arm, model in models.items():
        model.to(device)
        scores[arm], timing[arm] = score_neural(model, features, src, dst, device)
        model.cpu()
    started = time.perf_counter()
    scores["isolation_forest"] = -forest.score_samples(features)
    timing["isolation_forest"] = time.perf_counter() - started
    scores["type_rarity"] = rarity[graph["node_type"]]
    timing["type_rarity"] = 0.0
    return scores, timing


def load_dataset_spec(data_dir, dataset, config):
    manifest = json.loads((data_dir / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "STATIC_DEVELOPMENT_ONLY":
        raise ValueError("native graph audit has not released static development data")
    matches = [d for d in manifest["datasets"] if d["dataset"] == dataset]
    if len(matches) != 1:
        raise ValueError("dataset missing or duplicated in manifest")
    spec = matches[0]
    inventory = {Path(g["npz"]).stem: g for g in spec["graphs"]}
    names = config["train_graphs"] + [config["calibration_graph"], config["evaluation_graph"]]
    if len(names) != len(set(names)):
        raise ValueError("train/calibration/evaluation graphs must be distinct")
    paths = {}
    for name in names:
        entry = inventory[name]
        path = (data_dir / entry["npz"]).resolve()
        if not path.is_relative_to(data_dir.resolve()) or sha256(path) != entry["npz_sha256"]:
            raise ValueError("normalized graph hash or path mismatch")
        paths[name] = path
    return spec, paths


def run_pilot(config_path, data_dir, dataset, output, device_name, registration_path):
    """Real runs always validate frozen code/config/data before loading or fitting."""
    from experiments.apt_final.native_graph.provenance import verify_registration
    registration = verify_registration(Path(config_path), Path(data_dir), Path(registration_path))
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if config.get("scope") != "DEVELOPMENT_ONLY":
        raise ValueError("this pilot supports DEVELOPMENT_ONLY scope")
    output = Path(output)
    if output.exists():
        raise FileExistsError("output must be new; prior evidence is never overwritten")
    data_dir = Path(data_dir)
    spec, paths = load_dataset_spec(data_dir, dataset, config)
    configure_reproducibility(config["cpu_threads"])
    device = select_device(device_name)
    qualification = qualify_device(device)
    output.mkdir(parents=True)
    private = output / "private"
    private.mkdir()
    status = {"status": "RUNNING", "scope": "DEVELOPMENT_ONLY", "dataset": dataset,
              "device_requested": device_name, "device_actual": str(device),
              "gpu_qualification": qualification,
              "versions": {"python": platform.python_version(), "numpy": np.__version__,
                           "torch": torch.__version__, "sklearn": sklearn.__version__,
                           "cuda": torch.version.cuda},
              "reproducibility": {"deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
                                  "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
                                  "cudnn_benchmark": torch.backends.cudnn.benchmark,
                                  "cuda_matmul_tf32": torch.backends.cuda.matmul.allow_tf32,
                                  "seed_variability_is_not_campaign_uncertainty": True},
              "registration_sha256": sha256(registration_path),
              "registration_git_commit": registration.get("git_commit"),
              "config_sha256": sha256(config_path),
              "data_manifest_sha256": sha256(data_dir / "MANIFEST.json")}
    if device.type == "cuda":
        status["gpu_name"] = torch.cuda.get_device_name(device)
        torch.cuda.reset_peak_memory_stats(device)
    write_json(output / "RUN_STATUS.json", status)
    started = time.perf_counter()
    node_types = int(spec["metadata"]["node_feature_dim"])
    relations = int(spec["metadata"]["edge_feature_dim"])
    train_paths = [paths[name] for name in config["train_graphs"]]
    mean, scale, type_counts = fit_scaler(train_paths, node_types, relations)
    rarity = -np.log((type_counts + 1) / (type_counts.sum() + len(type_counts)))
    np.savez_compressed(private / "PREPROCESSING.npz", mean=mean, scale=scale,
                        type_counts=type_counts, type_rarity=rarity)
    fitted = []
    fit_records = []
    # All fitting and calibration complete before any evaluation y is loaded.
    for seed in config["seeds"]:
        print(json.dumps({"stage": "fit", "dataset": dataset, "seed": seed}), flush=True)
        models, fit = {}, {}
        for arm in ("mlp", "gin"):
            model, fit[arm] = fit_neural(train_paths, node_types, relations, mean, scale,
                                        config, seed, arm, device)
            models[arm] = model.cpu()
            torch.save({"state_dict": models[arm].state_dict(), "arm": arm,
                        "input_dim": len(mean), "hidden_dim": config["hidden_dim"],
                        "bottleneck_dim": config["bottleneck_dim"], "seed": seed},
                       private / f"{arm}_{seed}.pt")
        forest, fit["isolation_forest"] = fit_forest(train_paths, node_types, relations,
                                                    mean, scale, config, seed)
        import joblib
        joblib.dump(forest, private / f"isolation_forest_{seed}.joblib")
        graph = load_graph(paths[config["calibration_graph"]])
        raw, degree, src, dst = observed_features(graph, node_types, relations)
        features = scale_features(raw, mean, scale)
        calibration, calibration_timing = score_fixed(models, forest, rarity, graph, features, src, dst, device)
        margins = {arm: margin_from_calibration(scores, scores, config["calibration_fpr"])[0]
                   for arm, scores in calibration.items()}
        quality, _ = quality_selector(degree, margins["gin"], margins["mlp"], config["gate_min_degree"])
        confidence, _ = confidence_selector(margins["gin"], margins["mlp"])
        calibration_report = {arm: {"strict_score_threshold": strict_threshold(scores, config["calibration_fpr"]),
                                   "threshold_infinite": strict_threshold(scores, config["calibration_fpr"]) is None,
                                   "achieved_clean_benign_fpr": float(np.mean(margins[arm] >= 0)),
                                   "unique_calibration_scores": int(len(np.unique(scores)))}
                              for arm, scores in calibration.items()}
        calibration_report["quality_gate"] = {"achieved_clean_benign_fpr": float(np.mean(quality >= 0))}
        calibration_report["confidence_selector"] = {"achieved_clean_benign_fpr": float(np.mean(confidence >= 0))}
        np.savez_compressed(private / f"calibration_{seed}.npz", **calibration)
        fit_records.append({"seed": seed, "fit": fit, "calibration": calibration_report,
                            "calibration_inference_seconds": calibration_timing})
        fitted.append((seed, models, forest, calibration))
        del graph, raw, features, degree, src, dst, margins
    freeze = {"status": "FITTED_BEFORE_EVALUATION_LABEL_ACCESS", "fit_labels_used": False,
              "calibration_graph": config["calibration_graph"],
              "train_graphs": config["train_graphs"], "seeds": config["seeds"],
              "artifacts": {p.name: sha256(p) for p in private.iterdir() if p.is_file()},
              "fit_records": fit_records}
    write_json(output / "FIT_FREEZE.json", freeze)
    with np.load(paths[config["evaluation_graph"]], allow_pickle=False) as arrays:
        y = np.asarray(arrays["y"], dtype=np.int8)
    graph = load_graph(paths[config["evaluation_graph"]])
    if len(y) != len(graph["node_type"]) or set(np.unique(y)) != {0, 1}:
        raise ValueError("evaluation must contain aligned benign and attack labels")
    records = []
    for scenario, keep in scenario_masks(len(graph["src"]), config["drop_rates"], config["mask_seeds"]):
        raw, degree, src, dst = observed_features(graph, node_types, relations, keep)
        features = scale_features(raw, mean, scale)
        print(json.dumps({"stage": "evaluate", "dataset": dataset, **scenario}), flush=True)
        for seed, models, forest, calibration in fitted:
            scores, timing = score_fixed(models, forest, rarity, graph, features, src, dst, device)
            margins = {arm: margin_from_calibration(calibration[arm], value, config["calibration_fpr"])[0]
                       for arm, value in scores.items()}
            quality, quality_graph = quality_selector(degree, margins["gin"], margins["mlp"], config["gate_min_degree"])
            confidence, confidence_graph = confidence_selector(margins["gin"], margins["mlp"])
            margins["quality_gate"] = quality
            margins["confidence_selector"] = confidence
            predictions = {arm: value >= 0 for arm, value in margins.items()}
            metrics = {arm: binary_metrics(y, scores.get(arm, value), predictions[arm])
                       for arm, value in margins.items()}
            changes = {arm: {ref: error_changes(y, predictions[arm], predictions[ref])
                             for ref in ("gin", "mlp", "isolation_forest", "type_rarity")}
                       for arm in ("quality_gate", "confidence_selector")}
            oracle_correct = (predictions["gin"] == y) | (predictions["mlp"] == y)
            record = {"seed": seed, **scenario, "observed_edges": len(src),
                      "isolated_nodes": int(np.sum(degree == 0)), "metrics": metrics,
                      "error_changes": changes,
                      "routing": {"quality_graph_fraction": float(np.mean(quality_graph)),
                                  "confidence_graph_fraction": float(np.mean(confidence_graph))},
                      "oracle_mlp_gin_accuracy_descriptive": float(np.mean(oracle_correct)),
                      "fixed_arm_inference_seconds": timing}
            records.append(record)
            prediction_path = private / f"predictions_{seed}_{scenario['name']}.npz"
            np.savez_compressed(prediction_path, y=y, degree=degree,
                                **{f"margin_{arm}": value for arm, value in margins.items()},
                                **{f"score_{arm}": value for arm, value in scores.items()})
        write_json(output / "RESULTS.partial.json",
                   {**status, "status": "PARTIAL_DEVELOPMENT_ONLY",
                    "completed_scenarios": len(records) // len(config["seeds"]),
                    "fit_freeze_sha256": sha256(output / "FIT_FREEZE.json"),
                    "fit_records": fit_records, "records": records,
                    "elapsed_seconds": time.perf_counter() - started})
        del raw, features, degree, src, dst
    summary = []
    for rate in config["drop_rates"]:
        matches = [r for r in records if r["drop_rate"] == rate]
        for arm in matches[0]["metrics"]:
            metrics = {}
            for name in ("f1", "precision", "recall", "false_positive_rate", "average_precision", "accuracy"):
                values = [r["metrics"][arm][name] for r in matches]
                metrics[name] = {"mean": float(np.mean(values)), "min": float(min(values)), "max": float(max(values))}
            summary.append({"drop_rate": rate, "arm": arm, "descriptive_runs": len(matches), **metrics})
    results = {**status, "status": "COMPLETE_DEVELOPMENT_ONLY", "elapsed_seconds": time.perf_counter() - started,
               "target": "binary anomalous entity detection under retained-relationship removal",
               "features": "node type + log1p observed incoming/outgoing counts by relation, recomputed after removal",
               "mlp_is_feature_only_independent_of_edges": False,
               "type_rarity_is_feature_only": True,
               "graph_encoder": "two directed incoming-sum GIN layers with self terms and LayerNorm",
               "calibration": "clean held-out benign graph empirical tail p=(1+#calibration>=score)/(n+1); positive iff p<=alpha",
               "routing_calibration_fpr_guaranteed": False,
               "inference_cost_claim": "offline all-arm timings; selectors do not establish deployed compute savings",
               "claim_scope": "separate dataset fit/replication; no frozen-model transfer, temporal detection or campaign CI",
               "fit_freeze_sha256": sha256(output / "FIT_FREEZE.json"), "fit_records": fit_records,
               "records": records, "descriptive_summary": summary,
               "cuda_peak_allocated_bytes": torch.cuda.max_memory_allocated(device) if device.type == "cuda" else None,
               "cuda_peak_reserved_bytes": torch.cuda.max_memory_reserved(device) if device.type == "cuda" else None,
               "predictions_public": False,
               "private_artifact_sha256": {p.name: sha256(p) for p in private.iterdir() if p.is_file()}}
    write_json(output / "RESULTS.json", results)
    write_json(output / "RUN_STATUS.json", {**status, "status": "COMPLETE_DEVELOPMENT_ONLY",
                                             "elapsed_seconds": results["elapsed_seconds"]})
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--dataset", choices=("cadets", "theia"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="cpu")
    parser.add_argument("--registration", required=True)
    args = parser.parse_args(argv)
    result = run_pilot(args.config, args.data_dir, args.dataset, args.output, args.device, args.registration)
    print(json.dumps({"status": result["status"], "dataset": args.dataset,
                      "output": str(Path(args.output).resolve()), "elapsed_seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    # Also support direct script invocation from any working directory.
    repo_root = Path(__file__).resolve().parents[3]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    main()
