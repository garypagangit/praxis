"""Executable, fail-closed development engine for the APT-final graph study.

GIN is the implemented graph model. All models use fixed-epoch CPU training.
E2 changes edge availability, not node-feature availability. E3 replays paired
predictions; its routed compute numbers are proxies, not deployed measurements.
Synthetic runs are marked SMOKE_NOT_EVIDENCE throughout their descendants.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import threading
import time as clock
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

SPLITS = {"train", "gate_train", "calibration", "development", "confirmation"}
QUALITY_FEATURES = ("edge_retention", "mean_in_degree", "isolated_fraction", "mean_arrival_lag")
ARMS = ("mlp", "gin_real", "gin_shuffled", "gin_self")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_jsonl(path):
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def write_jsonl(path, values):
    with Path(path).open("x", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def _output(path):
    path = Path(path)
    if path.exists() and any(path.iterdir()):
        raise ValueError("Output must be absent or empty; experiment artifacts are immutable")
    path.mkdir(parents=True, exist_ok=True)
    return path


def validate_data(rows, edges, require_splits=True):
    """Validate schema and causal, campaign-isolated topology before fitting."""
    if not rows:
        raise ValueError("No observations")
    by_id, groups, widths = {}, {}, set()
    for row in rows:
        required = {"id", "group_id", "split", "time", "host_id", "features", "label"}
        if not required.issubset(row):
            raise ValueError(f"Missing row keys: {required - row.keys()}")
        if not isinstance(row["id"], str) or not row["id"] or row["id"] in by_id:
            raise ValueError("IDs must be unique nonempty strings")
        if not isinstance(row["group_id"], str) or not row["group_id"]:
            raise ValueError("Each row needs a stable campaign/group identifier")
        if not isinstance(row["host_id"], str) or not row["host_id"]:
            raise ValueError("Each row needs a host identifier")
        if row["split"] not in SPLITS:
            raise ValueError("Unknown split")
        if row["group_id"] in groups and groups[row["group_id"]] != row["split"]:
            raise ValueError("Group crosses splits")
        groups[row["group_id"]] = row["split"]
        if isinstance(row["label"], bool) or not isinstance(row["label"], int) or row["label"] < 0:
            raise ValueError("Labels must be nonnegative integers")
        if not isinstance(row["time"], (int, float)) or not math.isfinite(row["time"]):
            raise ValueError("time must be finite seconds")
        if not isinstance(row["features"], list) or not row["features"]:
            raise ValueError("Empty feature vector")
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in row["features"]):
            raise ValueError("Features must be finite numeric values")
        widths.add(len(row["features"]))
        by_id[row["id"]] = row
    if len(widths) != 1:
        raise ValueError("Inconsistent feature widths")
    if require_splits and not (SPLITS - {"confirmation"}).issubset(set(groups.values())):
        raise ValueError("All four development campaign-disjoint splits are required")
    seen = set()
    for edge in edges:
        if not {"source", "target", "relation", "available_at"}.issubset(edge):
            raise ValueError("Incomplete edge")
        if edge["source"] not in by_id or edge["target"] not in by_id:
            raise ValueError("Unknown edge endpoint")
        source, target = by_id[edge["source"]], by_id[edge["target"]]
        if source["group_id"] != target["group_id"] or source["split"] != target["split"]:
            raise ValueError("Cross-group or cross-split edges are prohibited")
        if source["time"] > target["time"]:
            raise ValueError("Future-source edge")
        available = edge["available_at"]
        if not isinstance(available, (int, float)) or not math.isfinite(available):
            raise ValueError("Nonfinite availability")
        if available < source["time"] or available > target["time"]:
            raise ValueError("Edge unavailable at target decision time")
        if not isinstance(edge["relation"], str) or not edge["relation"]:
            raise ValueError("Empty relation")
        key = (edge["source"], edge["target"], edge["relation"])
        if key in seen:
            raise ValueError("Duplicate edge")
        seen.add(key)
    train_labels = {r["label"] for r in rows if r["split"] == "train"}
    if require_splits and (len(train_labels) < 2 or any(r["label"] not in train_labels for r in rows)):
        raise ValueError("Every evaluation label must be represented in training")
    return {"rows": len(rows), "edges": len(edges), "groups": len(groups),
            "feature_width": next(iter(widths)), "labels": sorted(train_labels),
            "split_counts": dict(Counter(r["split"] for r in rows))}


def _authorize(rows_path, edges_path, receipt_path, smoke):
    if not smoke:
        from experiments.apt_final.readiness import require_data_release
        require_data_release(receipt_path, rows=rows_path, edges=edges_path)
    hashes = {"rows_sha256": sha256(rows_path), "edges_sha256": sha256(edges_path)}
    rows, edges = read_jsonl(rows_path), read_jsonl(edges_path)
    if smoke:
        if not rows or not all(r.get("synthetic") is True for r in rows):
            raise ValueError("Smoke requires every row to be explicitly synthetic")
        return rows, edges, hashes
    if receipt_path is None:
        raise ValueError("Scientific execution requires an E0 PASS receipt")
    receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    if receipt.get("status") not in ("PASS", "E0_PASS"):
        raise ValueError("E0 has not passed")
    for key, digest in hashes.items():
        if receipt.get(key) != digest:
            raise ValueError("E0 receipt does not bind the exact input bytes")
    if any(r.get("synthetic") for r in rows):
        raise ValueError("Synthetic data cannot run as scientific evidence")
    return rows, edges, hashes


def rewire_edges(rows, edges, seed, attempts_per_edge=30):
    """Directed swaps preserve in/out degrees per campaign and relation.

    Synthetic swapped relationships preserve their availability lead time before
    the target decision, rather than the old relationship's absolute timestamp.
    Both new endpoints must remain causal. This is a restricted causal null,
    not a uniform graph draw or a reconstruction of real observed relationships.
    """
    rng, by_id = random.Random(seed), {r["id"]: r for r in rows}
    result = [dict(e) for e in edges]
    partitions = defaultdict(list)
    for i, edge in enumerate(result):
        partitions[(by_id[edge["source"]]["group_id"], edge["relation"])].append(i)
    accepted = 0
    for indices in partitions.values():
        if len(indices) < 2:
            continue
        existing = {(result[i]["source"], result[i]["target"]) for i in indices}
        for _ in range(attempts_per_edge * len(indices)):
            i, j = rng.sample(indices, 2)
            a, b = result[i], result[j]
            if a["source"] == b["source"] or a["target"] == b["target"]:
                continue
            new_a, new_b = (a["source"], b["target"]), (b["source"], a["target"])
            if new_a in existing or new_b in existing or new_a[0] == new_a[1] or new_b[0] == new_b[1]:
                continue
            lead_a = by_id[a["target"]]["time"] - a["available_at"]
            lead_b = by_id[b["target"]]["time"] - b["available_at"]
            available_a = by_id[new_a[1]]["time"] - lead_a
            available_b = by_id[new_b[1]]["time"] - lead_b
            if available_a < by_id[new_a[0]]["time"] or available_b < by_id[new_b[0]]["time"]:
                continue
            existing.remove((a["source"], a["target"]))
            existing.remove((b["source"], b["target"]))
            result[i], result[j] = dict(a, target=new_a[1], available_at=available_a), dict(b, target=new_b[1], available_at=available_b)
            existing.update((new_a, new_b))
            accepted += 1
    original = {(e["source"], e["target"], e["relation"]) for e in edges}
    changed = sum((e["source"], e["target"], e["relation"]) not in original for e in result)
    validate_data(rows, result)
    return result, {"accepted_swaps": accepted, "edges_changed": changed,
                    "changed_fraction": changed / len(edges) if edges else 0,
                    "null_scope": "causal directed degree/relation-preserving swaps; target-relative availability lead times preserved",
                    "uniform_random_graph_claim": False}


def fit_scaler(rows):
    import numpy as np
    train = np.asarray([r["features"] for r in rows if r["split"] == "train"], dtype=np.float64)
    if not len(train):
        raise ValueError("No training observations")
    scale = train.std(axis=0)
    scale[scale < 1e-12] = 1
    return {"mean": train.mean(axis=0).tolist(), "scale": scale.tolist(), "fit_split": "train"}


def _model(kind, width, hidden, classes):
    import torch
    from torch import nn

    class Detector(nn.Module):
        def __init__(self):
            super().__init__()
            self.kind = kind
            self.first = nn.Sequential(nn.Linear(width, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
            self.second = nn.Sequential(nn.Linear(hidden, hidden), nn.ReLU(), nn.Linear(hidden, hidden))
            self.head = nn.Linear(hidden, classes)
            if kind == "gin":
                self.epsilon = nn.Parameter(torch.zeros(2))

        def aggregate(self, x, edge_index, layer):
            if self.kind == "mlp":
                return x
            aggregate = torch.zeros_like(x)
            if edge_index.shape[1]:
                aggregate.index_add_(0, edge_index[1], x[edge_index[0]])
            return (1 + self.epsilon[layer]) * x + aggregate

        def forward(self, x, edge_index):
            x = torch.relu(self.first(self.aggregate(x, edge_index, 0)))
            x = torch.relu(self.second(self.aggregate(x, edge_index, 1)))
            return self.head(x)

    return Detector()


def _tensor_data(rows, edges, scaler, labels):
    import torch
    by_id = {r["id"]: i for i, r in enumerate(rows)}
    x = torch.tensor([r["features"] for r in rows], dtype=torch.float32)
    x = (x - torch.tensor(scaler["mean"])) / torch.tensor(scaler["scale"])
    mapping = {value: i for i, value in enumerate(labels)}
    y = torch.tensor([mapping[r["label"]] for r in rows], dtype=torch.long)
    links = [(by_id[e["source"]], by_id[e["target"]]) for e in edges if e["source"] != e["target"]]
    edge_index = torch.tensor(links, dtype=torch.long).T.contiguous() if links else torch.empty((2, 0), dtype=torch.long)
    return x, y, edge_index


class _RSS:
    """Sample process RSS; includes shared data/runtime, not isolated tensor peak."""
    def __enter__(self):
        self.peak, self.done = None, threading.Event()
        try:
            import psutil
            process = psutil.Process()
            self.peak = process.memory_info().rss
            def sample():
                while not self.done.wait(.01):
                    self.peak = max(self.peak, process.memory_info().rss)
            self.thread = threading.Thread(target=sample, daemon=True)
            self.thread.start()
        except ImportError:
            self.thread = None
        return self

    def __exit__(self, *args):
        self.done.set()
        if self.thread:
            self.thread.join()


def metrics(records, labels, prefix="probabilities", benign_label=0):
    import numpy as np
    from sklearn.metrics import average_precision_score, f1_score
    if not records:
        raise ValueError("Cannot score an empty denominator")
    truth = np.asarray([r["label"] for r in records])
    probs = np.asarray([r[prefix] for r in records])
    predictions = np.asarray(labels)[probs.argmax(axis=1)]
    per_class = f1_score(truth, predictions, labels=labels, average=None, zero_division=0)
    ap = {}
    for i, label in enumerate(labels):
        binary = truth == label
        ap[str(label)] = float(average_precision_score(binary, probs[:, i])) if binary.any() and (~binary).any() else None
    return {"n": len(records), "macro_f1": float(per_class.mean()),
            "per_stage_f1": dict(zip(map(str, labels), map(float, per_class))),
            "per_stage_pr_auc_average_precision": ap,
            "accuracy": float((truth == predictions).mean()),
            "false_alerts_argmax": int(((truth == benign_label) & (predictions != benign_label)).sum()),
            "attack_recall_argmax": float((predictions[truth != benign_label] != benign_label).mean()) if (truth != benign_label).any() else None}


def paired_intervals(records, arm_a, arm_b, labels, replicates=500, seed=20260919):
    """Separate seed and campaign intervals; repeated seeds are not new events."""
    import numpy as np
    seeds = sorted({r["seed"] for r in records})
    groups = sorted({r["group_id"] for r in records})
    sidx, gidx = {s: i for i, s in enumerate(seeds)}, {g: i for i, g in enumerate(groups)}
    lidx = {label: i for i, label in enumerate(labels)}
    lookup = {(r["seed"], r["arm"], r["id"]): r for r in records}
    if len(lookup) != len(records):
        raise ValueError("Duplicate seed/arm/ID in paired comparison")
    cubes = np.zeros((2, len(seeds), len(groups), len(labels), len(labels)), dtype=np.int64)
    for r in records:
        if r["arm"] != arm_a:
            continue
        other = lookup.get((r["seed"], arm_b, r["id"]))
        if other is None or other["label"] != r["label"] or other["group_id"] != r["group_id"]:
            raise ValueError("Unpaired model predictions")
        for a, row in enumerate((r, other)):
            cubes[a, sidx[row["seed"]], gidx[row["group_id"]], lidx[row["label"]], int(np.argmax(row["probabilities"]))] += 1
    if not cubes.sum():
        raise ValueError("Empty paired comparison")
    def macro(confusion):
        diagonal = np.diagonal(confusion, axis1=-2, axis2=-1)
        denominator = confusion.sum(axis=-2) + confusion.sum(axis=-1)
        return np.divide(2 * diagonal, denominator, out=np.zeros_like(diagonal, dtype=float), where=denominator != 0).mean(axis=-1)
    fixed = macro(cubes.sum(axis=2))
    seed_deltas = fixed[0] - fixed[1]
    point = float(seed_deltas.mean())
    rng = np.random.default_rng(seed)
    seed_draws, group_draws = [], []
    for _ in range(replicates):
        if len(seeds) >= 2:
            seed_draws.append(float(seed_deltas[rng.integers(len(seeds), size=len(seeds))].mean()))
        if len(groups) >= 2:
            resampled = macro(cubes[:, :, rng.integers(len(groups), size=len(groups))].sum(axis=2))
            group_draws.append(float((resampled[0] - resampled[1]).mean()))
    interval = lambda values: list(map(float, np.quantile(values, [.025, .975]))) if values else None
    return {"delta_macro_f1": point, "seed_bootstrap_ci95": interval(seed_draws),
            "group_block_bootstrap_ci95": interval(group_draws), "seeds": len(seeds),
            "independent_groups": len(groups), "replicates": replicates,
            "scope": "Separate conditional intervals; no joint seed/group or multiplicity claim"}


def run_e1(config, rows_path, edges_path, output_dir, e0_receipt_path=None, smoke=False):
    import numpy as np
    import torch
    rows, edges, hashes = _authorize(rows_path, edges_path, e0_receipt_path, smoke)
    if any(r.get("split") == "confirmation" for r in rows):
        raise ValueError("Confirmation must remain in a separate sealed input file")
    audit = validate_data(rows, edges)
    labels = config.get("include_labels", audit["labels"])
    if labels != audit["labels"]:
        raise ValueError("This implementation requires the frozen label schema to equal all training labels")
    seeds = list(config.get("seeds", range(10)))
    if not seeds or len(set(seeds)) != len(seeds) or (not smoke and len(seeds) < 10):
        raise ValueError("Distinct seeds required; scientific E1 requires at least ten")
    if config.get("graph_model", "gin").lower() != "gin":
        raise ValueError("Only GIN is implemented; GATv2 is a planned secondary comparator")
    epochs, hidden = int(config.get("epochs", 20)), int(config.get("hidden_dim", 32))
    if epochs < 1 or hidden < 1:
        raise ValueError("Positive epoch and hidden-dimension budgets required")
    torch.set_num_threads(int(config.get("threads", 2)))
    torch.use_deterministic_algorithms(True)
    scaler = fit_scaler(rows)
    shuffled, rewiring = {}, {}
    for seed in seeds:
        shuffled[seed], rewiring[str(seed)] = rewire_edges(rows, edges, seed)
        if not smoke and rewiring[str(seed)]["changed_fraction"] < config.get("min_rewired_fraction", .5):
            raise ValueError("Insufficient causal rewiring: shuffled control is invalid; do not train")
    out = _output(output_dir)
    (out / "checkpoints").mkdir()
    predictions, costs = [], []
    train_mask = torch.tensor([r["split"] == "train" for r in rows])
    for seed in seeds:
        for arm in ARMS:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            kind = "mlp" if arm == "mlp" else "gin"
            arm_edges = edges if arm == "gin_real" else shuffled[seed] if arm == "gin_shuffled" else []
            x, y, edge_index = _tensor_data(rows, arm_edges, scaler, labels)
            model = _model(kind, audit["feature_width"], hidden, len(labels))
            optimizer = torch.optim.Adam(model.parameters(), lr=config.get("learning_rate", .01))
            started = clock.perf_counter()
            with _RSS() as rss:
                model.train()
                for _ in range(epochs):
                    optimizer.zero_grad(set_to_none=True)
                    loss = torch.nn.functional.cross_entropy(model(x, edge_index)[train_mask], y[train_mask])
                    if not torch.isfinite(loss):
                        raise ValueError("Nonfinite training loss")
                    loss.backward(); optimizer.step()
                fit_seconds = clock.perf_counter() - started
                model.eval()
                infer_started = clock.perf_counter()
                with torch.no_grad():
                    probs = torch.softmax(model(x, edge_index), dim=-1).tolist()
                inference_seconds = clock.perf_counter() - infer_started
            for row, probability in zip(rows, probs):
                if row["split"] in ("gate_train", "calibration", "development"):
                    predictions.append({k: row[k] for k in ("id", "group_id", "split", "time", "label")} | {"seed": seed, "arm": arm, "probabilities": probability})
            checkpoint = {"state_dict": model.state_dict(), "kind": kind, "width": audit["feature_width"],
                          "hidden": hidden, "labels": labels, "scaler": scaler, "seed": seed, "arm": arm}
            checkpoint_path = out / "checkpoints" / f"{arm}_{seed}.pt"
            torch.save(checkpoint, checkpoint_path)
            costs.append({"seed": seed, "arm": arm, "fit_seconds": fit_seconds,
                          "inference_seconds_all_input_rows": inference_seconds,
                          "process_rss_sampled_peak_bytes": rss.peak,
                          "parameters": sum(p.numel() for p in model.parameters()),
                          "epochs": epochs, "checkpoint": checkpoint_path.relative_to(out).as_posix(),
                          "checkpoint_sha256": sha256(checkpoint_path)})
    write_jsonl(out / "predictions.jsonl", predictions)
    development = [r for r in predictions if r["split"] == "development"]
    comparisons = {name: paired_intervals(development, "gin_real", other, labels, config.get("bootstrap_replicates", 500), config.get("bootstrap_seed", 20260919))
                   for name, other in (("H1a_real_vs_shuffled", "gin_shuffled"), ("H1b_real_vs_mlp", "mlp"), ("real_vs_self", "gin_self"))}
    report = {"stage": "E1", "status": "SMOKE_NOT_EVIDENCE" if smoke else "DEVELOPMENT_ONLY",
              "input_hashes": hashes, "schema": audit, "config": config, "seeds": seeds,
              "development_group_ids": sorted({r["group_id"] for r in rows}),
              "labels": labels, "scaler": scaler, "rewiring": rewiring, "costs": costs,
              "comparisons": comparisons, "predictions_sha256": sha256(out / "predictions.jsonl"),
              "confirmation_revealed": False,
              "limitations": ["GIN primary; GATv2 not implemented", "Fixed epochs are matched; parameter count, FLOPs and wall time are not equalized",
                              "Process RSS includes shared runtime/data and is sampled, not an isolated allocation peak",
                              "No confirmation predictions are emitted or used for fitting/selection"]}
    write_json(out / "RESULTS.json", report)
    return report


def _bound_report(directory, expected_stage):
    directory = Path(directory)
    report = json.loads((directory / "RESULTS.json").read_text(encoding="utf-8"))
    if report["stage"] != expected_stage or report.get("predictions_sha256") != sha256(directory / "predictions.jsonl"):
        raise ValueError("Stage or prediction artifact integrity mismatch")
    if report.get("status") not in ("SMOKE_NOT_EVIDENCE", "DEVELOPMENT_ONLY"):
        raise ValueError("Unrecognized upstream execution status")
    return report


def degrade_edges(rows, edges, scenario, seed):
    rng, by_id = random.Random(seed), {r["id"]: r for r in rows}
    kind = scenario["kind"]
    if kind not in ("clean", "edge_drop", "relation_outage", "arrival_delay"):
        raise ValueError("Unsupported degradation; full source/feature outage requires richer input")
    fraction = scenario.get("fraction", 0)
    if not 0 <= fraction <= 1:
        raise ValueError("Invalid degradation fraction")
    kept = []
    for edge in edges:
        if kind == "edge_drop" and rng.random() < fraction:
            continue
        if kind == "relation_outage" and edge["relation"] == scenario["relation"]:
            continue
        changed = dict(edge)
        if kind == "arrival_delay" and rng.random() < fraction:
            delay = scenario.get("seconds", 60)
            if delay < 0:
                raise ValueError("Negative delay")
            changed["available_at"] += delay
            if changed["available_at"] > by_id[edge["target"]]["time"]:
                continue
        kept.append(changed)
    return kept


def quality_features(rows, original_edges, observed_edges):
    """Past-only, label-free measurements available at each decision time.

    Retention uses a training/reference graph's expected degree schedule only in
    this controlled simulator: it is not a deployable missing-log detector.
    Actual deployment must supply a previously frozen expectation estimator.
    """
    by_id = {r["id"]: r for r in rows}
    original, observed = defaultdict(list), defaultdict(list)
    for e in original_edges:
        original[e["target"]].append(e)
    for e in observed_edges:
        observed[e["target"]].append(e)
    result = {}
    # Only the current target's causal incident edges are inspected.
    for row in rows:
        available = observed[row["id"]]
        expected = len(original[row["id"]])
        result[row["id"]] = [len(available) / expected if expected else 1., float(len(available)),
                              float(not available),
                              sum(e["available_at"] - by_id[e["source"]]["time"] for e in available) / len(available) if available else 0.]
    return result


def _predict_checkpoint(path, rows, edges, expected_sha):
    import torch
    if sha256(path) != expected_sha:
        raise ValueError("Frozen checkpoint hash mismatch")
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    if any(len(r["features"]) != checkpoint["width"] or r["label"] not in checkpoint["labels"] for r in rows):
        raise ValueError("Confirmation feature/label schema differs from frozen model")
    x, _, edge_index = _tensor_data(rows, edges if checkpoint["kind"] == "gin" else [], checkpoint["scaler"], checkpoint["labels"])
    model = _model(checkpoint["kind"], checkpoint["width"], checkpoint["hidden"], len(checkpoint["labels"]))
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    started = clock.perf_counter()
    with torch.no_grad():
        probabilities = torch.softmax(model(x, edge_index), dim=-1).tolist()
    return probabilities, clock.perf_counter() - started


def _scenarios(config, edges):
    default = [{"name": "clean", "kind": "clean"}]
    default += [{"name": f"edge_drop_{int(p * 100)}", "kind": "edge_drop", "fraction": p} for p in config.get("drop_rates", (.05, .1, .25, .5)) if p > 0]
    default += [{"name": f"relation_outage_{r}", "kind": "relation_outage", "relation": r} for r in sorted({e["relation"] for e in edges})]
    default += [{"name": f"delay_{seconds}s_half", "kind": "arrival_delay", "fraction": .5, "seconds": seconds} for seconds in config.get("delay_seconds", [60])]
    result = config.get("scenarios", default)
    if not result or len({r["name"] for r in result}) != len(result):
        raise ValueError("Nonempty uniquely named scenarios required")
    return result


def _paired_replay(config, e1_dir, rows, edges, splits):
    e1 = _bound_report(e1_dir, "E1")
    results, costs = [], []
    scenarios = _scenarios(config, edges)
    for seed in e1["seeds"]:
        for scenario in scenarios:
            # Identical perturbations for both models, independently replicated per seed.
            damaged = degrade_edges(rows, edges, scenario, seed)
            quality = quality_features(rows, edges, damaged)
            paired = {}
            for arm in ("mlp", "gin_real"):
                checkpoint = next(c for c in e1["costs"] if c["seed"] == seed and c["arm"] == arm)
                paired[arm], seconds = _predict_checkpoint(Path(e1_dir) / checkpoint["checkpoint"], rows, damaged, checkpoint["checkpoint_sha256"])
                costs.append({"seed": seed, "scenario": scenario["name"], "arm": arm, "inference_seconds_all_input_rows": seconds,
                              "rows_measured": len(rows), "edges_observed": len(damaged)})
            for i, row in enumerate(rows):
                if row["split"] in splits:
                    result = {k: row[k] for k in ("id", "group_id", "split", "time", "label")}
                    result.update(seed=seed, scenario=scenario["name"], quality=quality[row["id"]],
                                  mlp_probabilities=paired["mlp"][i], gin_probabilities=paired["gin_real"][i])
                    results.append(result)
    return e1, scenarios, results, costs


def run_e2(config, e1_dir, rows_path, edges_path, output_dir, e0_receipt_path=None, smoke=False):
    rows, edges, hashes = _authorize(rows_path, edges_path, e0_receipt_path, smoke)
    if any(r.get("split") == "confirmation" for r in rows):
        raise ValueError("Confirmation must remain in a separate sealed input file")
    validate_data(rows, edges)
    e1 = _bound_report(e1_dir, "E1")
    if hashes != e1["input_hashes"]:
        raise ValueError("E2 must replay the exact E1 input, using frozen models")
    if config != e1["config"]:
        raise ValueError("E2 config differs from frozen E1 development configuration")
    if (e1["status"] == "SMOKE_NOT_EVIDENCE") != bool(smoke):
        raise ValueError("Cannot promote synthetic smoke into evidence")
    e1, scenarios, predictions, costs = _paired_replay(config, e1_dir, rows, edges, {"gate_train", "calibration", "development"})
    out = _output(output_dir)
    write_jsonl(out / "predictions.jsonl", predictions)
    summaries = {}
    for scenario in scenarios:
        subset = [r for r in predictions if r["split"] == "development" and r["scenario"] == scenario["name"]]
        summaries[scenario["name"]] = {arm: {str(seed): metrics([r for r in subset if r["seed"] == seed], e1["labels"], arm + "_probabilities") for seed in e1["seeds"]} for arm in ("mlp", "gin")}
    report = {"stage": "E2", "status": "SMOKE_NOT_EVIDENCE" if smoke else "DEVELOPMENT_ONLY", "config": config,
              "e0_receipt_path": str(Path(e0_receipt_path).resolve()) if e0_receipt_path else None,
              "input_hashes": hashes, "e1_results_sha256": sha256(Path(e1_dir) / "RESULTS.json"),
              "labels": e1["labels"], "seeds": e1["seeds"], "scenarios": scenarios, "costs": costs,
              "development_metrics": summaries, "predictions_sha256": sha256(out / "predictions.jsonl"),
              "quality_features": list(QUALITY_FEATURES), "confirmation_revealed": False,
              "limitations": ["Only edge telemetry is degraded; node features remain fixed",
                              "edge_retention uses simulator pre-degradation degree and is excluded from deployable policies",
                              "No full host/flow feature outage or operational alerts/day claim"]}
    write_json(out / "RESULTS.json", report)
    return report


def policy_inputs(records, indices=(1, 2, 3)):
    """Allowlist quality inputs; exclude simulator-only edge_retention."""
    if any(i not in (1, 2, 3) for i in indices):
        raise ValueError("Unobservable simulator retention cannot drive the deployable gate")
    return [[r["quality"][i] for i in indices] for r in records]


def _fit_policies(records, labels):
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    if not records or {r["split"] for r in records} != {"gate_train"}:
        raise ValueError("Gate fitting is restricted to gate_train campaigns")
    label_index = {label: i for i, label in enumerate(labels)}
    usefulness = np.asarray([int(np.argmax(r["gin_probabilities"]) == label_index[r["label"]]) - int(np.argmax(r["mlp_probabilities"]) == label_index[r["label"]]) for r in records])
    x = np.asarray(policy_inputs(records), dtype=float)
    mean, scale = x.mean(axis=0), x.std(axis=0)
    scale[scale < 1e-12] = 1
    disagreements = usefulness != 0
    if disagreements.any() and len(set(usefulness[disagreements])) == 2:
        estimator = LogisticRegression(C=1, random_state=20260919, max_iter=1000)
        estimator.fit(((x - mean) / scale)[disagreements], (usefulness[disagreements] > 0).astype(int))
        learned = {"kind": "logistic", "coefficients": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0]), "mean": mean.tolist(), "scale": scale.tolist()}
    else:
        learned = {"kind": "constant", "use_gin": bool(usefulness.sum() > 0)}
    # Predetermined, small rule grid; choose net benefit, ties favor fewer GIN calls.
    candidates = [(float("-inf"), False), (float("inf"), True)]
    candidates += [(threshold, True) for threshold in (1., 2., 4., 8.)]
    scored = []
    for threshold, high in candidates:
        if math.isinf(threshold):
            chosen = np.full(len(records), threshold > 0)
        else:
            chosen = x[:, 0] >= threshold
        scored.append((int(usefulness[chosen].sum()), -int(chosen.sum()), threshold, chosen))
    _, _, threshold, selected = max(scored, key=lambda c: (c[0], c[1], c[2]))
    static = {"kind": "constant", "use_gin": threshold > 0} if math.isinf(threshold) else {"kind": "degree_threshold", "minimum_observed_in_degree": threshold}
    # Confidence control uses only MLP uncertainty; selection is fit in the same split.
    candidates = []
    confidence = np.asarray([max(r["mlp_probabilities"]) for r in records])
    for threshold in (0., .5, .6, .7, .8, .9, 1.000001):
        selected = confidence < threshold
        candidates.append((int(usefulness[selected].sum()), -int(selected.sum()), threshold))
    confidence_threshold = max(candidates)[2]
    return {"learned": learned, "static": static, "confidence": {"kind": "confidence", "maximum_mlp_confidence": confidence_threshold},
            "feature_indices": [1, 2, 3], "fit_split": "gate_train", "fit_rows": len(records),
            "utility_target": "GIN correctness minus MLP correctness; correctness ties excluded from logistic fitting"}


def route(records, policy, arm):
    import numpy as np
    if arm == "mlp":
        return [False] * len(records)
    if arm == "gin":
        return [True] * len(records)
    spec = policy[arm]
    if spec["kind"] == "constant":
        return [spec["use_gin"]] * len(records)
    if spec["kind"] == "degree_threshold":
        return [r["quality"][1] >= spec["minimum_observed_in_degree"] for r in records]
    if spec["kind"] == "confidence":
        return [max(r["mlp_probabilities"]) < spec["maximum_mlp_confidence"] for r in records]
    if spec["kind"] == "logistic":
        x = (np.asarray(policy_inputs(records, tuple(policy["feature_indices"]))) - spec["mean"]) / spec["scale"]
        return (x @ np.asarray(spec["coefficients"]) + spec["intercept"] > 0).tolist()
    raise ValueError("Unknown frozen policy")


def _random_routes(records, rate, salt="frozen-calibration-rate"):
    return [int.from_bytes(hashlib.sha256(f"{salt}|{r['seed']}|{r['scenario']}|{r['id']}".encode()).digest()[:8], "big") / 2 ** 64 < rate for r in records]


def _chosen(records, choices):
    return [dict(r, probabilities=r["gin_probabilities"] if choose else r["mlp_probabilities"], use_gin=bool(choose)) for r, choose in zip(records, choices)]


def _calibrate_alerts(records, config, labels, split="calibration"):
    """Freeze thresholds only on calibration; count equal-score ties conservatively."""
    import numpy as np
    if {r["split"] for r in records} != {split} or split != "calibration":
        raise ValueError("Alert thresholds may be fit only on calibration")
    benign = config.get("benign_label", 0)
    if benign not in labels:
        return {"status": "NO_BENIGN_LABEL"}
    exposure = config.get("observation_days", {}).get("calibration")
    if not exposure or exposure <= 0 or "alert_budget_per_day" not in config:
        return {"status": "ALERT_RATE_NOT_ESTIMABLE", "reason": "Authoritative calibration exposure days and false-alert budget/day are required"}
    allowed = math.floor(float(config["alert_budget_per_day"]) * exposure)
    if allowed < 0:
        raise ValueError("Negative alert budget")
    result = {"status": "FROZEN", "fit_split": "calibration", "thresholds": {}, "false_alert_budget_per_day": config["alert_budget_per_day"], "calibration_exposure_days_per_scenario": exposure}
    index = labels.index(benign)
    # Each scenario is an alternative replay of the same exposure, not additional days.
    for seed in sorted({r["seed"] for r in records}):
        thresholds = []
        for scenario in sorted({r["scenario"] for r in records}):
            negative = sorted((1 - r["probabilities"][index] for r in records if r["seed"] == seed and r["scenario"] == scenario and r["label"] == benign), reverse=True)
            if not negative:
                raise ValueError("Calibration scenario has no benign records")
            thresholds.append(float(np.nextafter(negative[allowed], math.inf)) if allowed < len(negative) else 0.)
        result["thresholds"][str(seed)] = max(thresholds)
    return result


def _evaluate_routes(records, policy, config, labels, frozen_alerts=None):
    import numpy as np
    output, summary, alerts = [], {}, {}
    label_index = {label: i for i, label in enumerate(labels)}
    arms = ("mlp", "gin", "static", "learned", "confidence", "random", "oracle_descriptive")
    for arm in arms:
        if arm == "oracle_descriptive":
            choices = [int(np.argmax(r["gin_probabilities"]) == label_index[r["label"]]) > int(np.argmax(r["mlp_probabilities"]) == label_index[r["label"]]) for r in records]
        elif arm == "random":
            choices = _random_routes(records, policy["random_rate"])
        else:
            choices = route(records, policy, arm)
        selected = _chosen(records, choices)
        for record in selected:
            record["arm"] = arm
        output += selected
        if frozen_alerts is None:
            alerts[arm] = _calibrate_alerts([r for r in selected if r["split"] == "calibration"], config, labels)
        else:
            alerts[arm] = frozen_alerts[arm]
        summary[arm] = {}
        for split in sorted({r["split"] for r in records} - {"calibration", "gate_train"}):
            summary[arm][split] = {}
            for scenario in sorted({r["scenario"] for r in records}):
                by_seed = {}
                for seed in sorted({r["seed"] for r in records}):
                    subset = [r for r in selected if r["split"] == split and r["scenario"] == scenario and r["seed"] == seed]
                    result = metrics(subset, labels, benign_label=config.get("benign_label", 0))
                    result["gin_fraction"] = sum(r["use_gin"] for r in subset) / len(subset)
                    if alerts[arm]["status"] == "FROZEN":
                        benign = config.get("benign_label", 0)
                        threshold = alerts[arm]["thresholds"][str(seed)]
                        flags = [1 - r["probabilities"][labels.index(benign)] >= threshold for r in subset]
                        false_alerts = sum(flag and r["label"] == benign for flag, r in zip(flags, subset))
                        exposure = config.get("observation_days", {}).get(split)
                        positives = sum(r["label"] != benign for r in subset)
                        result["frozen_alert_threshold"] = threshold
                        result["false_alerts"] = false_alerts
                        result["false_alerts_per_day"] = false_alerts / exposure if exposure else None
                        result["recall_at_frozen_threshold"] = sum(flag and r["label"] != benign for flag, r in zip(flags, subset)) / positives if positives else None
                        result["false_alert_budget_met"] = false_alerts / exposure <= config["alert_budget_per_day"] if exposure else None
                    by_seed[str(seed)] = result
                summary[arm][split][scenario] = by_seed
    return output, summary, alerts


def run_e3(config, e2_dir, output_dir, smoke=False):
    e2 = _bound_report(e2_dir, "E2")
    if config != e2["config"]:
        raise ValueError("E3 config differs from frozen E2 development configuration")
    if not smoke:
        from experiments.apt_final.readiness import require_data_release
        require_data_release(e2.get("e0_receipt_path"))
    if (e2["status"] == "SMOKE_NOT_EVIDENCE") != bool(smoke):
        raise ValueError("Cannot promote synthetic smoke into evidence")
    records = read_jsonl(Path(e2_dir) / "predictions.jsonl")
    if any(r["split"] in ("train", "confirmation") for r in records):
        raise ValueError("E3 input contains forbidden training/confirmation observations")
    labels = e2["labels"]
    policy = _fit_policies([r for r in records if r["split"] == "gate_train"], labels)
    calibration = [r for r in records if r["split"] == "calibration"]
    if not calibration:
        raise ValueError("No calibration records")
    policy["random_rate"] = sum(route(calibration, policy, "learned")) / len(calibration)
    policy.update(labels=labels, seeds=e2["seeds"], e2_predictions_sha256=e2["predictions_sha256"], e1_results_sha256=e2["e1_results_sha256"],
                  status="SMOKE_NOT_EVIDENCE" if smoke else "FROZEN_DEVELOPMENT_POLICY", config=config,
                  feature_names=[QUALITY_FEATURES[i] for i in policy["feature_indices"]],
                  random_rate_source="calibration learned-policy routes, no oracle or outcome labels",
                  created_at_unix=clock.time())
    predictions, summary, alerts = _evaluate_routes([r for r in records if r["split"] != "gate_train"], policy, config, labels)
    policy["alert_thresholds"] = alerts
    out = _output(output_dir)
    write_json(out / "POLICY_FREEZE.json", policy)
    write_jsonl(out / "predictions.jsonl", predictions)
    intervals = {}
    for scenario in e2["scenarios"]:
        subset = [r for r in predictions if r["split"] == "development" and r["scenario"] == scenario["name"]]
        intervals[scenario["name"]] = {f"{arm}_vs_{baseline}": paired_intervals(subset, arm, baseline, labels, config.get("bootstrap_replicates", 500), config.get("bootstrap_seed", 20260919)) for arm in ("static", "learned") for baseline in ("mlp", "gin", "confidence", "random")}
    report = {"stage": "E3", "status": "SMOKE_NOT_EVIDENCE" if smoke else "DEVELOPMENT_ONLY", "labels": labels,
              "policy_sha256": sha256(out / "POLICY_FREEZE.json"), "predictions_sha256": sha256(out / "predictions.jsonl"),
              "metrics": summary, "paired_intervals": intervals, "confirmation_revealed": False,
              "hypotheses": "NOT_CONFIRMED: offline development replay; operational costs and independent confirmation pending",
              "limitations": ["Gate learns from gate_train; calibration only sets alert thresholds and random route rate",
                              "Oracle chooses per-record correctness using outcome labels: descriptive ceiling, never deployable",
                              "No real-time routing cost is measured: both classifiers were evaluated offline",
                              "No 50% oracle-gap or 80% static-benefit success claim is automated when ratios are unstable",
                              "Observed degree/isolation/lag may correlate with attacks; cross-environment confirmation is required"]}
    write_json(out / "RESULTS.json", report)
    return report


def run_e4(config, e1_dir, policy_path, rows_path, edges_path, output_dir,
           e0_receipt_path=None, readiness_path=None, smoke=False):
    policy_path = Path(policy_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    if policy.get("status") not in ("SMOKE_NOT_EVIDENCE", "FROZEN_DEVELOPMENT_POLICY"):
        raise ValueError("Unrecognized frozen-policy status")
    e1 = _bound_report(e1_dir, "E1")
    if policy.get("e1_results_sha256") != sha256(Path(e1_dir) / "RESULTS.json"):
        raise ValueError("Policy belongs to different frozen base models")
    if (policy["status"] == "SMOKE_NOT_EVIDENCE") != bool(smoke):
        raise ValueError("Cannot promote smoke policy into evidence")
    if not smoke:
        if readiness_path is None:
            raise ValueError("Confirmation remains sealed: readiness receipt required")
        ready = json.loads(Path(readiness_path).read_text(encoding="utf-8"))
        if ready.get("status") != "READY_FOR_CONFIRMATION" or ready.get("policy_sha256") != sha256(policy_path):
            raise ValueError("Confirmation readiness does not bind the frozen policy")
        if ready.get("config_sha256") != hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest():
            raise ValueError("Readiness does not bind the exact E4 config")
        if not ready.get("preregistered_commit"):
            raise ValueError("Record the committed pre-registration before confirmation")
    rows, edges, hashes = _authorize(rows_path, edges_path, e0_receipt_path, smoke)
    validate_data(rows, edges, require_splits=False)
    confirmation = [r for r in rows if r["split"] == "confirmation"]
    if not confirmation:
        raise ValueError("No held-out confirmation observations")
    if len(confirmation) != len(rows):
        raise ValueError("E4 accepts only the separately sealed confirmation input")
    if {r["group_id"] for r in rows} & set(e1["development_group_ids"]):
        raise ValueError("Confirmation campaigns overlap development campaigns")
    # Same dataset replay is permitted only for its sealed confirmation campaigns.
    original = e1["input_hashes"] == hashes
    if not original:
        if any(r["split"] != "confirmation" for r in rows):
            raise ValueError("An external dataset must contain confirmation-only observations")
        if not smoke and (not config.get("external_schema_id") or config.get("external_schema_id") != e1["config"].get("feature_schema_id")):
            raise ValueError("External dataset requires an identical, explicit frozen feature schema")
    if policy["labels"] != e1["labels"] or policy["seeds"] != e1["seeds"]:
        raise ValueError("Frozen model/policy schema mismatch")
    _, scenarios, paired, costs = _paired_replay(config, e1_dir, rows, edges, {"confirmation"})
    # Operational thresholds and budget are frozen from E3; only exposure days may differ.
    evaluation_config = dict(policy["config"])
    evaluation_config["observation_days"] = config.get("observation_days", evaluation_config.get("observation_days", {}))
    output, summary, _ = _evaluate_routes(paired, policy, evaluation_config, policy["labels"], policy["alert_thresholds"])
    out = _output(output_dir)
    write_jsonl(out / "predictions.jsonl", output)
    report = {"stage": "E4", "status": "SMOKE_NOT_EVIDENCE" if smoke else "FROZEN_CONFIRMATION_EVALUATED",
              "input_hashes": hashes, "policy_sha256": sha256(policy_path), "scenarios": scenarios,
              "metrics": summary, "costs": costs, "refitted": False,
              "predictions_sha256": sha256(out / "predictions.jsonl"), "confirmation_revealed": True,
              "scope": "Frozen same-schema model and gate; operational cost superiority not established by replay"}
    write_json(out / "RESULTS.json", report)
    return report
