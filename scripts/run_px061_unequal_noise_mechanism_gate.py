from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def haar_matrix(n: int) -> np.ndarray:
    if n == 1:
        return np.ones((1, 1))
    h = haar_matrix(n // 2)
    top = np.kron(h, np.array([[1.0, 1.0]])) / np.sqrt(2)
    bottom = np.kron(np.eye(n // 2), np.array([[1.0, -1.0]])) / np.sqrt(2)
    return np.vstack([top, bottom])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--dimension", type=int, default=256)
    ap.add_argument("--rho", type=float, default=1.0)
    ap.add_argument("--draws", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=610)
    args = ap.parse_args()
    if args.dimension & (args.dimension - 1):
        raise ValueError("dimension must be a power of two")

    h = haar_matrix(args.dimension)
    orthogonality_error = float(np.max(np.abs(h @ h.T - np.eye(args.dimension))))

    # Frozen heterogeneous per-coefficient sensitivity envelope. This is a
    # mechanism audit, not a learned or data-dependent sensitivity estimate.
    levels = np.floor(np.log2(np.arange(args.dimension) + 1)).astype(int)
    delta = 1.0 / np.sqrt(2.0 ** levels)
    equal_variance = np.sum(delta**2) / (2 * args.rho)
    unequal_variance = np.abs(delta) * np.sum(np.abs(delta)) / (2 * args.rho)

    equal_rho = float(np.sum(delta**2 / (2 * equal_variance)))
    unequal_rho = float(np.sum(delta**2 / (2 * unequal_variance)))
    equal_total = float(args.dimension * equal_variance)
    unequal_total = float(np.sum(unequal_variance))

    rng = np.random.default_rng(args.seed)
    equal_noise = rng.normal(size=(args.draws, args.dimension)) * np.sqrt(equal_variance)
    unequal_noise = rng.normal(size=(args.draws, args.dimension)) * np.sqrt(unequal_variance)
    # Orthonormal inverse Haar transform preserves total energy.
    equal_recon = equal_noise @ h
    unequal_recon = unequal_noise @ h
    empirical_equal = float(np.mean(np.sum(equal_recon**2, axis=1)))
    empirical_unequal = float(np.mean(np.sum(unequal_recon**2, axis=1)))

    checks = {
        "haar_orthonormal_error_below_1e_10": orthogonality_error < 1e-10,
        "equal_rho_matches_target": abs(equal_rho - args.rho) < 1e-10,
        "unequal_rho_matches_target": abs(unequal_rho - args.rho) < 1e-10,
        "unequal_total_variance_lower": unequal_total < equal_total,
        "monte_carlo_order_matches": empirical_unequal < empirical_equal,
        "monte_carlo_relative_error_below_0_02": (
            abs(empirical_equal / equal_total - 1) < 0.02
            and abs(empirical_unequal / unequal_total - 1) < 0.02
        ),
    }
    result = {
        "experiment_id": "PX-061",
        "stage": "gate0_unequal_gaussian_mechanism_audit",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "dimension": args.dimension,
        "target_zcdp_rho": args.rho,
        "equal_realized_rho": equal_rho,
        "unequal_realized_rho": unequal_rho,
        "equal_total_coefficient_variance": equal_total,
        "unequal_total_coefficient_variance": unequal_total,
        "analytical_variance_reduction": 1 - unequal_total / equal_total,
        "empirical_equal_reconstruction_energy": empirical_equal,
        "empirical_unequal_reconstruction_energy": empirical_unequal,
        "haar_orthogonality_error": orthogonality_error,
        "checks": checks,
        "boundary": "This validates a matched-zCDP anisotropic Gaussian allocation under a frozen coordinate sensitivity envelope. It is not an FL utility result and does not validate data-dependent clipping.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
