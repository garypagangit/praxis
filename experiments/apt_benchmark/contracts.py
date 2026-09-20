"""Small fail-closed contracts for benchmark data and causal decisions."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path


FORBIDDEN_FEATURES = {
    "label", "labels", "stage", "phase_name", "sequence_id", "rules",
    "ground_truth", "campaign_id", "scenario", "split", "line_number",
    "attack_onset", "impact_at", "future_label", "timestamp",
    "y", "target", "stages", "phase", "id", "record_id", "source_id", "host_id",
    "event_at", "feature_available_at", "score_available_at", "decision_at",
    "episode_id", "run_id", "attack_type", "kill_chain_all", "true_label",
}


def check_feature_names(names):
    names = list(names)
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("Nonempty feature names are required")
    bad = sorted({name.strip().casefold() for name in names} & FORBIDDEN_FEATURES)
    if bad:
        raise ValueError(f"Target, split or hindsight metadata in features: {bad}")


def check_availability(*, event_at, feature_available_at, decision_at):
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
           for x in (event_at, feature_available_at, decision_at)):
        raise ValueError("Finite, explicit timestamps are required")
    if event_at > feature_available_at or feature_available_at > decision_at:
        raise ValueError("Future event or feature is unavailable at decision time")


def split_index(protocol):
    splits = protocol.get("splits")
    if not isinstance(splits, dict) or set(splits) != {"fit", "development", "calibration", "test"}:
        raise ValueError("Four distinct data roles required")
    mapping = {}
    for role, groups in splits.items():
        if not isinstance(groups, list) or not groups:
            raise ValueError("Each role requires a nonempty list of whole-run groups")
        for group in groups:
            if (not isinstance(group, str) or not group.strip() or group != group.strip()
                    or group in {".", ".."} or any(char in group for char in "/\\:")):
                raise ValueError("Invalid whole-run group identifier")
            if group in mapping:
                raise ValueError(f"Run crosses forbidden split boundary: {group}")
            mapping[group] = role
    return mapping


def sha256_file(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
