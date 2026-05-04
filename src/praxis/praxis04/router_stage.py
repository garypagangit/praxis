from __future__ import annotations

import numpy as np

from praxis.praxis04.routers import stage_conditioned_router_weights


class StageRouter:
    def __init__(self, n_experts: int = 3, seed: int = 42):
        self.n_experts = int(n_experts)
        self.seed = int(seed)

    def predict_weights(self, features: np.ndarray, stage_logits: np.ndarray) -> np.ndarray:
        return stage_conditioned_router_weights(
            features,
            stage_logits,
            n_experts=self.n_experts,
            seed=self.seed,
        )

