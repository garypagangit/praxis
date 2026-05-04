from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.datasets import make_classification
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

from praxis.praxis04.evaluate import router_entropy
from praxis.praxis04.reproducibility import json_safe, seed_everything
from praxis.praxis04.routers import global_router_weights, stage_conditioned_router_weights
from praxis.praxis04.submodels import RFModel


def run_smoke(config: dict, output_dir: str | Path) -> dict:
    seed = int(config["seed"])
    seed_state = seed_everything(seed, deterministic_torch=bool(config.get("seed_torch", False)))
    n_samples = int(config.get("smoke_n_samples", 1200))
    n_features = int(config.get("smoke_n_features", 20))
    n_classes = int(config.get("n_classes", 5))

    x, y = make_classification(
        n_samples=n_samples,
        n_features=n_features,
        n_informative=10,
        n_redundant=2,
        n_classes=n_classes,
        weights=[0.58, 0.18, 0.12, 0.08, 0.04],
        random_state=seed,
    )
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        stratify=y,
        random_state=seed,
    )

    rf = RFModel({"n_estimators": 40, "max_depth": 8, "random_state": seed, "n_jobs": 1})
    rf.fit(x_train, y_train)
    proba = rf.predict_proba(x_test)
    pred = proba.argmax(axis=1)

    stage_logits = np.eye(n_classes)[pred]
    global_gates = global_router_weights(x_test, seed=seed)
    stage_gates = stage_conditioned_router_weights(x_test, stage_logits, seed=seed)

    payload = {
        "config_name": config["name"],
        "seed": seed,
        "macro_f1": float(f1_score(y_test, pred, average="macro", zero_division=0)),
        "global_router_entropy_mean": float(router_entropy(global_gates).mean()),
        "stage_router_entropy_mean": float(router_entropy(stage_gates).mean()),
        "seed_state": seed_state.__dict__,
    }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "metrics.json").write_text(json.dumps(json_safe(payload), indent=2), encoding="utf-8")
    (out / "config.json").write_text(json.dumps(json_safe(config), indent=2), encoding="utf-8")
    return payload
