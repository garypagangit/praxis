from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split


def haar_forward(x):
    x = x.copy()
    details = []
    while len(x) > 1:
        a = (x[0::2] + x[1::2]) / np.sqrt(2)
        d = (x[0::2] - x[1::2]) / np.sqrt(2)
        details.append(d)
        x = a
    return np.concatenate([x] + details[::-1])


def haar_inverse(c):
    pos, a = 1, c[:1].copy()
    size = 1
    while size < len(c):
        d = c[pos:pos + size]
        pos += size
        out = np.empty(size * 2)
        out[0::2] = (a + d) / np.sqrt(2)
        out[1::2] = (a - d) / np.sqrt(2)
        a, size = out, size * 2
    return a


def level_slices(n):
    # Packed order from haar_forward is:
    # [one approximation, 1, 2, 4, ..., n/2 detail coefficients].
    out, pos, size = [slice(0, 1)], 1, 1
    while pos < n:
        out.append(slice(pos, min(pos + size, n)))
        pos += size
        size *= 2
    return out


def coefficient_groups(n, band_count):
    levels = level_slices(n)
    if band_count is None or band_count >= len(levels):
        return levels
    partitions = np.array_split(np.arange(len(levels)), band_count)
    return [
        slice(levels[int(part[0])].start, levels[int(part[-1])].stop)
        for part in partitions
    ]


def softmax(z):
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def gradient(theta, x, y, classes=10):
    d = x.shape[1]
    w, b = theta[:d * classes].reshape(d, classes), theta[d * classes:d * classes + classes]
    p = softmax(x @ w + b)
    target = np.eye(classes)[y]
    return np.concatenate([(x.T @ (p - target) / len(x)).ravel(), (p - target).mean(axis=0)])


def accuracy(theta, x, y):
    d, k = x.shape[1], 10
    w, b = theta[:d * k].reshape(d, k), theta[d * k:d * k + k]
    return float(np.mean(np.argmax(x @ w + b, axis=1) == y))


def partition_clients(y, clients, alpha, rng):
    buckets = [[] for _ in range(clients)]
    for label in range(10):
        idx = np.where(y == label)[0]
        rng.shuffle(idx)
        proportions = rng.dirichlet(np.full(clients, alpha))
        cuts = np.cumsum(proportions)[:-1] * len(idx)
        for bucket, part in zip(buckets, np.split(idx, cuts.astype(int))):
            bucket.extend(part.tolist())
    return [np.array(v, dtype=int) for v in buckets]


def run_seed(cfg, seed, arm):
    rng = np.random.default_rng(seed)
    x, y = load_digits(return_X_y=True)
    x = x.astype(float) / 16.0
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=seed, stratify=y
    )
    clients = partition_clients(y_train, cfg["clients"], cfg["dirichlet_alpha"], rng)
    raw_dim = x.shape[1] * 10 + 10
    padded = 1 << (raw_dim - 1).bit_length()
    slices = coefficient_groups(padded, cfg.get("coefficient_bands"))
    # Per-level replace-one clipping caps and initial bounds are public.
    sizes = np.array([s.stop - s.start for s in slices])
    levels = np.arange(len(slices))
    public_caps = np.array([0.04 * np.sqrt(n) for n in sizes])
    decay = cfg.get("level_bound_decay", 0.0)
    static_bounds = public_caps / (1.0 + decay * levels)
    current_bounds = static_bounds.copy()
    theta = np.zeros(raw_dim)
    total_rho = cfg["privacy"]["total_zcdp_rho"]
    adaptive = arm == "adaptive_unequal_wavelet"
    adapt_fraction = cfg.get("adaptive", {}).get("rho_fraction", 0.0) if adaptive else 0.0
    train_rho = total_rho * (1 - adapt_fraction)
    rho_round = train_rho / cfg["rounds"]
    adapt_interval = cfg.get("adaptive", {}).get("interval_rounds", 5)
    adapt_queries = int(np.ceil(cfg["rounds"] / adapt_interval))
    rho_adapt_query = total_rho * adapt_fraction / adapt_queries if adaptive else 0.0

    clipping_events = 0
    clipping_total = 0
    for round_idx in range(cfg["rounds"]):
        available = np.array([i for i, rows in enumerate(clients) if len(rows)])
        chosen = rng.choice(available, cfg["clients_per_round"], replace=False)
        transformed = []
        capped_norm_vectors = []
        for client in chosen:
            rows = clients[client]
            delta = -cfg["local_learning_rate"] * gradient(theta, x_train[rows], y_train[rows])
            padded_delta = np.pad(delta, (0, padded - raw_dim))
            coeff = haar_forward(padded_delta)
            capped_norm_vectors.append([
                min(np.linalg.norm(coeff[s]), public_caps[level])
                for level, s in enumerate(slices)
            ])
            for level, s in enumerate(slices):
                norm = np.linalg.norm(coeff[s])
                clipping_total += 1
                if norm > current_bounds[level]:
                    clipping_events += 1
                    coeff[s] *= current_bounds[level] / norm
            transformed.append(coeff)
        mean_coeff = np.mean(transformed, axis=0)
        if arm != "nonprivate":
            sensitivity = 2 * current_bounds / len(chosen)
            if arm == "equal_wavelet":
                variance = np.full(len(slices), np.sum(sensitivity**2) / (2 * rho_round))
            else:
                scale = np.sum(sensitivity * np.sqrt(sizes))
                variance = sensitivity * scale / (2 * rho_round * np.sqrt(sizes))
            for level, s in enumerate(slices):
                mean_coeff[s] += rng.normal(0, np.sqrt(variance[level]), s.stop - s.start)
        theta += haar_inverse(mean_coeff)[:raw_dim]
        if adaptive and round_idx % adapt_interval == 0:
            # One vector Gaussian release. Replace-one L2 sensitivity is
            # ||public_caps||_2 / participating_clients.
            query_sensitivity = np.linalg.norm(public_caps) / len(chosen)
            query_sigma = query_sensitivity / np.sqrt(2 * rho_adapt_query)
            released = np.mean(capped_norm_vectors, axis=0) + rng.normal(
                0, query_sigma, len(slices)
            )
            multiplier = cfg["adaptive"].get("released_mean_multiplier", 1.5)
            floor_fraction = cfg["adaptive"].get("floor_fraction", 0.05)
            current_bounds = np.clip(
                multiplier * released,
                floor_fraction * public_caps,
                public_caps,
            )
    return {
        "accuracy": accuracy(theta, x_test, y_test),
        "clipping_rate": clipping_events / clipping_total,
        "final_bounds": current_bounds.tolist(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    rows = []
    for seed in cfg["seeds"]:
        for arm in cfg["arms"]:
            outcome = run_seed(cfg, seed, arm)
            rows.append({"seed": seed, "arm": arm, **outcome})
    by_arm = {
        arm: float(np.mean([r["accuracy"] for r in rows if r["arm"] == arm]))
        for arm in cfg["arms"]
    }
    rho = cfg["privacy"]["total_zcdp_rho"]
    delta = cfg["privacy"]["delta"]
    epsilon = rho + 2 * np.sqrt(rho * np.log(1 / delta))
    result = {
        "experiment_id": "PX-061",
        "stage": cfg["stage"],
        "rows": rows,
        "mean_accuracy": by_arm,
        "conservative_epsilon": float(epsilon),
        "delta": delta,
        "status": "DEVELOPMENT_COMPLETE",
        "boundary": cfg["boundary"],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
