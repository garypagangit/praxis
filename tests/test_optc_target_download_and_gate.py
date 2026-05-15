from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts import download_optc_target_ecar
from scripts.run_optc_cross_host_gate import build_label_support


def test_resolve_target_accepts_red_team_day(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        download_optc_target_ecar,
        "load_url_map",
        lambda: {"optc_h501": [("evaluation/24Sep19/", "https://example.test/day2")]},
    )

    target = download_optc_target_ecar.resolve_target(
        "sysclient0501",
        tmp_path / "ecar",
        day="2",
    )

    assert target["pidmaker_key"] == "optc_h501"
    assert target["relative_dir"] == "evaluation/24Sep19/"
    assert target["url"] == "https://example.test/day2"
    assert target["output_dir"].endswith("evaluation\\24Sep19") or target[
        "output_dir"
    ].endswith("evaluation/24Sep19")


def test_resolve_target_accepts_benign_relative_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        download_optc_target_ecar,
        "load_url_map",
        lambda: {"optc_h201": [("benign/20-23Sep19/", "https://example.test/benign")]},
    )

    target = download_optc_target_ecar.resolve_target(
        "sysclient0201",
        tmp_path / "ecar",
        relative_dir="benign/20-23Sep19",
    )

    assert target["pidmaker_key"] == "optc_h201"
    assert target["day"] == ""
    assert target["relative_dir"] == "benign/20-23Sep19/"
    assert target["url"] == "https://example.test/benign"


def test_label_support_treats_benign_baselines_as_background_only() -> None:
    frame = pd.DataFrame(
        [
            *[
                {"slice": "red", "host": "sysclient0001", "day": "1", "slice_kind": "red_team", "label": "attack"}
                for _ in range(20)
            ],
            *[
                {
                    "slice": "red",
                    "host": "sysclient0001",
                    "day": "1",
                    "slice_kind": "red_team",
                    "label": "background",
                }
                for _ in range(20)
            ],
            *[
                {
                    "slice": "benign",
                    "host": "sysclient0001",
                    "day": "benign",
                    "slice_kind": "benign_baseline",
                    "label": "background",
                }
                for _ in range(50)
            ],
        ]
    )

    support = build_label_support(frame)

    assert support["red_slice_support_ready"]
    assert support["benign_baseline_support_ready"]
    assert support["support_ready"]
