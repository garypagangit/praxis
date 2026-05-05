from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class StageClassifier:
    params: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        model_type = str(self.params.get("model_type", "logistic")).lower()
        seed = int(self.params.get("random_state", self.params.get("seed", 42)))
        if model_type in {"rf", "random_forest", "randomforest"}:
            from sklearn.ensemble import RandomForestClassifier

            self.model = RandomForestClassifier(
                n_estimators=int(self.params.get("n_estimators", 160)),
                max_depth=self.params.get("max_depth", None),
                random_state=seed,
                n_jobs=int(self.params.get("n_jobs", 1)),
                class_weight=self.params.get("class_weight", "balanced"),
            )
            return

        from sklearn.linear_model import LogisticRegression

        self.model = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=int(self.params.get("max_iter", 200)),
                        random_state=seed,
                        class_weight=self.params.get("class_weight", None),
                    ),
                ),
            ]
        )

    def fit(self, x: np.ndarray, stage_y: np.ndarray) -> "StageClassifier":
        self.model.fit(x, stage_y)
        return self

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)
