from __future__ import annotations

from praxis.detectors import detector_table, list_detector_specs, make_detector


def test_detector_registry_lists_expected_baselines() -> None:
    names = {spec.name for spec in list_detector_specs()}
    assert "logreg_balanced" in names
    assert "random_forest_balanced" in names
    assert "mlp_small" in names
    assert all(row["supports_proba"] for row in detector_table())


def test_detector_factory_instantiates_registered_model() -> None:
    detector = make_detector("random_forest_balanced", random_state=7)
    assert detector.__class__.__name__ == "RandomForestClassifier"
