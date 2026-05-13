from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DetectorSpec:
    name: str
    family: str
    purpose: str
    supports_proba: bool
    needs_scaling: bool
    notes: str


DETECTOR_SPECS: dict[str, DetectorSpec] = {
    "logreg_balanced": DetectorSpec(
        name="logreg_balanced",
        family="linear",
        purpose="fast calibrated baseline for provenance-window features",
        supports_proba=True,
        needs_scaling=True,
        notes="Good first comparator for drift, watermark, and MIA protocols.",
    ),
    "random_forest_balanced": DetectorSpec(
        name="random_forest_balanced",
        family="tree_ensemble",
        purpose="nonlinear tabular baseline with class balancing",
        supports_proba=True,
        needs_scaling=False,
        notes="Use as stable detector-zoo member before neural graph models.",
    ),
    "extra_trees_balanced": DetectorSpec(
        name="extra_trees_balanced",
        family="tree_ensemble",
        purpose="high-variance tree ensemble comparator",
        supports_proba=True,
        needs_scaling=False,
        notes="Useful for surrogate/ownership and robustness checks.",
    ),
    "mlp_small": DetectorSpec(
        name="mlp_small",
        family="neural_tabular",
        purpose="small neural baseline for extraction/watermark/MIA protocols",
        supports_proba=True,
        needs_scaling=True,
        notes="CPU-smokeable; GPU variants should freeze architecture in a run spec.",
    ),
}


def list_detector_specs() -> list[DetectorSpec]:
    return [DETECTOR_SPECS[name] for name in sorted(DETECTOR_SPECS)]


def detector_table() -> list[dict[str, Any]]:
    return [asdict(spec) for spec in list_detector_specs()]


def make_detector(name: str, random_state: int = 0) -> Any:
    """Instantiate a registered sklearn-compatible detector."""

    if name == "logreg_balanced":
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return make_pipeline(
            StandardScaler(),
            LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                n_jobs=None,
                random_state=random_state,
            ),
        )
    if name == "random_forest_balanced":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(
            n_estimators=300,
            class_weight="balanced_subsample",
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=random_state,
        )
    if name == "extra_trees_balanced":
        from sklearn.ensemble import ExtraTreesClassifier

        return ExtraTreesClassifier(
            n_estimators=300,
            class_weight="balanced",
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=random_state,
        )
    if name == "mlp_small":
        from sklearn.neural_network import MLPClassifier
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        return make_pipeline(
            StandardScaler(),
            MLPClassifier(
                hidden_layer_sizes=(128, 64),
                alpha=1e-4,
                batch_size=256,
                early_stopping=True,
                max_iter=200,
                random_state=random_state,
            ),
        )
    valid = ", ".join(sorted(DETECTOR_SPECS))
    raise KeyError(f"Unknown detector '{name}'. Valid detectors: {valid}")
