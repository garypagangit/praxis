from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier


@dataclass
class RFModel:
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.model = RandomForestClassifier(**self.params)

    def fit(self, x: np.ndarray, y: np.ndarray) -> "RFModel":
        self.model.fit(x, y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict(x)

