from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MLPModel:
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        seed = int(self.params.get("random_state", self.params.get("seed", 42)))
        hidden_layers = tuple(self.params.get("hidden_layer_sizes", [128, 64]))
        max_iter = int(self.params.get("max_iter", 100))
        self.model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "mlp",
                    MLPClassifier(
                        hidden_layer_sizes=hidden_layers,
                        max_iter=max_iter,
                        random_state=seed,
                        early_stopping=bool(self.params.get("early_stopping", True)),
                    ),
                ),
            ]
        )

    def fit(self, x: np.ndarray, y: np.ndarray) -> "MLPModel":
        self.model.fit(x, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)

