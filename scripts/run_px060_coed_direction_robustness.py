from __future__ import annotations

import argparse
import importlib.util
import json
import pickle
import random
import sys
import types
from pathlib import Path

import numpy as np
import torch
from scipy.stats import spearmanr
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader


def mse(model, theta, loader, edge_weight):
    model.eval()
    values = []
    with torch.no_grad():
        for batch in loader:
            pred = model(batch.x, batch.edge_index, theta, edge_weight)
            values.append(torch.mean((pred - batch.y) ** 2).item())
    return float(np.mean(values))


def loaders(data, edge_index, max_train, batch_size):
    def rows(x, y):
        return [Data(x=torch.tensor(a, dtype=torch.float32), y=torch.tensor(b, dtype=torch.float32),
                     edge_index=edge_index) for a, b in zip(x, y)]
    tx, ty = data["train_data"]
    vx, vy = data["val_data"]
    ex, ey = data["test_data"]
    return (
        DataLoader(rows(tx[:max_train], ty[:max_train]), batch_size=batch_size, shuffle=True),
        DataLoader(rows(vx, vy), batch_size=len(vx), shuffle=False),
        DataLoader(rows(ex, ey), batch_size=len(ex), shuffle=False),
    )


def perturb(edge_index, theta_true, kind, fraction, seed):
    edge = edge_index.clone()
    truth = theta_true.clone()
    keep_original = torch.arange(edge.shape[1])
    rng = np.random.default_rng(seed)
    n = int(round(fraction * edge.shape[1]))
    chosen = np.sort(rng.choice(edge.shape[1], n, replace=False)) if n else np.array([], dtype=int)
    if kind == "reverse":
        idx = torch.tensor(chosen, dtype=torch.long)
        edge[:, idx] = edge.flip(0)[:, idx]
        truth[idx] = torch.pi / 2 - truth[idx]
    elif kind == "delete":
        mask = torch.ones(edge.shape[1], dtype=torch.bool)
        mask[torch.tensor(chosen, dtype=torch.long)] = False
        edge, truth, keep_original = edge[:, mask], truth[mask], keep_original[mask]
    return edge, truth, keep_original


def one_run(Model, data, cfg, perturbation, seed, learn_theta):
    torch.manual_seed(seed)
    np.random.seed(seed)
    random.seed(seed)
    base_edge = torch.tensor(data["edge_index"], dtype=torch.long)
    base_truth = torch.tensor(data["theta"], dtype=torch.float32)
    edge, truth, kept = perturb(base_edge, base_truth, perturbation["kind"], perturbation["fraction"], seed)
    train, val, test = loaders(data, edge, cfg["training"]["max_train_graphs"], cfg["training"]["batch_size"])
    model = Model(
        in_channels=data["train_data"][0].shape[-1],
        hidden_channels=cfg["training"]["hidden_channels"],
        out_channels=data["train_data"][1].shape[-1],
        num_layers=cfg["training"]["num_layers"],
        num_nodes=data["train_data"][0].shape[1],
        num_edges=edge.shape[1],
        alpha=0.5,
        normalize=False,
        self_feature_transform=True,
        self_loop=False,
        layer_wise_theta=False,
        regression=True,
        dropout_rate=0.0,
        jumping_knowledge=None,
    )
    model.reset_parameters()
    theta = torch.full((edge.shape[1],), torch.pi / 4, requires_grad=learn_theta)
    edge_weight = torch.ones(edge.shape[1])
    groups = [{"params": model.parameters(), "lr": cfg["training"]["learning_rate"]}]
    if learn_theta:
        groups.append({"params": [theta], "lr": cfg["training"]["theta_learning_rate"]})
    opt = torch.optim.Adam(groups)
    best = {"val": float("inf"), "test": float("inf"), "theta": None, "epoch": 0}
    stale = 0
    for epoch in range(1, cfg["training"]["max_epochs"] + 1):
        model.train()
        for batch in train:
            opt.zero_grad()
            loss = torch.mean((model(batch.x, batch.edge_index, theta, edge_weight) - batch.y) ** 2)
            loss.backward()
            opt.step()
            if learn_theta:
                with torch.no_grad():
                    theta.clamp_(0, torch.pi / 2)
        score = mse(model, theta, val, edge_weight)
        if score < best["val"]:
            best = {"val": score, "test": mse(model, theta, test, edge_weight),
                    "theta": theta.detach().clone(), "epoch": epoch}
            stale = 0
        else:
            stale += 1
        if stale > cfg["training"]["patience"]:
            break
    rho = float(spearmanr(best["theta"].numpy(), truth.numpy()).statistic) if learn_theta else None
    return {
        "seed": seed, "perturbation": perturbation["kind"], "fraction": perturbation["fraction"],
        "learn_theta": learn_theta, "test_mse": best["test"], "best_epoch": best["epoch"],
        "theta_spearman": rho, "edges": int(edge.shape[1]), "retained_original_edges": int(len(kept)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    if args.smoke:
        cfg["seeds"] = cfg["seeds"][:1]
        cfg["perturbations"] = cfg["perturbations"][:1]
        cfg["training"].update(max_train_graphs=32, hidden_channels=16, num_layers=2, max_epochs=8, patience=3)
    # The upstream utils package imports optional JAX generation utilities
    # eagerly. The model itself only requires get_fuzzy_laplacian, so expose
    # that dependency without expanding the environment surface.
    fuzzy_path = args.repo / "src" / "utils" / "fuzzy_laplacian.py"
    spec = importlib.util.spec_from_file_location("px060_fuzzy_laplacian", fuzzy_path)
    fuzzy = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(fuzzy)
    upstream_utils = types.ModuleType("utils")
    upstream_utils.get_fuzzy_laplacian = fuzzy.get_fuzzy_laplacian
    sys.modules["utils"] = upstream_utils
    sys.path.insert(0, str((args.repo / "src").resolve()))
    from model import FuzzyDirGCN
    with (args.repo / "datasets" / cfg["dataset"]).open("rb") as handle:
        data = pickle.load(handle)
    rows = []
    for p in cfg["perturbations"]:
        for seed in cfg["seeds"]:
            rows.append(one_run(FuzzyDirGCN, data, cfg, p, seed, True))
            rows.append(one_run(FuzzyDirGCN, data, cfg, p, seed, False))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {"experiment_id": cfg["experiment_id"], "smoke": args.smoke, "rows": rows}
    (args.output_dir / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
