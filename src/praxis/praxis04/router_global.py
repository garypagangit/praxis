from __future__ import annotations

import numpy as np

from praxis.praxis04.routers import global_router_weights


class GlobalRouter:
    def __init__(self, n_experts: int = 3, seed: int = 42):
        self.n_experts = int(n_experts)
        self.seed = int(seed)

    def predict_weights(self, features: np.ndarray) -> np.ndarray:
        return global_router_weights(features, n_experts=self.n_experts, seed=self.seed)

