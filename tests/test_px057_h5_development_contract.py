from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.px057_h5_development_contract import (
    CELL_ID,
    EXPECTED_CONFIG,
    require_c1,
    validate_frozen_development_config,
)
from scripts.submit_px057_h5_development_pilot import job_name


ROOT = Path(__file__).resolve().parents[1]


def test_committed_config_exactly_matches_the_single_machine_contract() -> None:
    config = json.loads(
        (ROOT / "configs/px057_h5_development_pilot_20260727.json").read_text(
            encoding="utf-8"
        )
    )

    validate_frozen_development_config(config)
    assert config == EXPECTED_CONFIG


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("generation", "seed"), 5756),
        (("generation", "sample_seed"), 5759),
        (("generation", "max_new_tokens"), 97),
        (("prompts", "initial_template"), "drifted"),
        (("models", "llama31", "revision"), "drifted"),
        (("primary_development_policy", "patience"), 3),
        (("primary_development_policy", "confidence_threshold"), 0.5),
        (("one_look_mechanism_selection_gate", "early_stop_harms_max"), 5),
        (("mechanism_sentinels", 0, "gold_answer"), "9"),
        (("aws", "instance_type"), "ml.g5.4xlarge"),
        (("aws", "volume_size_gb"), 201),
        (("aws", "max_runtime_seconds"), 43201),
    ],
)
def test_any_protocol_constant_drift_fails_closed(
    path: tuple[object, ...], replacement: object
) -> None:
    config = copy.deepcopy(EXPECTED_CONFIG)
    target: object = config
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = replacement  # type: ignore[index]

    with pytest.raises(ValueError, match="contract mismatch"):
        validate_frozen_development_config(config)


def test_extra_cell_or_field_fails_closed() -> None:
    extra_cell = copy.deepcopy(EXPECTED_CONFIG)
    extra_cell["cells"].append({"cell_id": "cell2_qwen25_arc"})
    extra_field = copy.deepcopy(EXPECTED_CONFIG)
    extra_field["unregistered"] = True

    with pytest.raises(ValueError, match="contract mismatch"):
        validate_frozen_development_config(extra_cell)
    with pytest.raises(ValueError, match="contract mismatch"):
        validate_frozen_development_config(extra_field)


def test_c1_is_the_only_callable_cell() -> None:
    require_c1(CELL_ID)
    with pytest.raises(ValueError, match="permits only"):
        require_c1("cell2_qwen25_arc")
    with pytest.raises(ValueError, match="permits only"):
        job_name({"cell_id": "cell2_qwen25_arc", "job_code": "c2"})
