from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StageClassifier:
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        seed = int(self.params.get("random_state", self.params.get("seed", 42)))
        self.model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=int(self.params.get("max_iter", 200)), random_state=seed)),
            ]
        )

    def fit(self, x: np.ndarray, stage_y: np.ndarray) -> "StageClassifier":
        self.model.fit(x, stage_y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)

