from __future__ import annotations

import numpy as np


def softmax(logits: np.ndarray) -> np.ndarray:
    logits = np.asarray(logits, dtype=float)
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def global_router_weights(features: np.ndarray, n_experts: int = 3, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    projection = rng.normal(scale=0.01, size=(features.shape[1], n_experts))
    return softmax(features @ projection)


def stage_conditioned_router_weights(
    features: np.ndarray,
    stage_logits: np.ndarray,
    n_experts: int = 3,
    seed: int = 42,
) -> np.ndarray:
    combined = np.concatenate([features, stage_logits], axis=1)
    rng = np.random.default_rng(seed)
    projection = rng.normal(scale=0.01, size=(combined.shape[1], n_experts))
    return softmax(combined @ projection)

