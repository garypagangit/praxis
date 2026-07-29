"""Load and validate the normative PX-063 machine-readable rule manifest."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re
from typing import Any


RULE_PATH = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "px063_deterministic_rules_v1.json"
)


@lru_cache(maxsize=1)
def rule_manifest() -> dict[str, Any]:
    value = json.loads(RULE_PATH.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "protocol_version",
        "grammar",
        "classifiers",
        "block_checks",
        "evidence_contract",
        "review_checks",
        "decision_precedence",
    }
    missing = sorted(required - set(value))
    if missing:
        raise RuntimeError(f"PX-063 rule manifest is missing: {missing}")
    if value["linked_event_window_turns"] != 0:
        raise RuntimeError("PX-063 v1.5 requires same-turn linked evidence")
    return value


def expanded_pattern(name: str) -> str:
    grammar = rule_manifest()["grammar"]
    pattern = str(grammar[name])
    component = str(grammar["path_component"])
    path_token = str(grammar["path_token_template"]).replace(
        "%PATH_COMPONENT%", component
    )
    return pattern.replace("%PATH_COMPONENT%", component).replace(
        "%PATH_TOKEN%", path_token
    )


def compiled_grammar(name: str) -> re.Pattern[str]:
    return re.compile(expanded_pattern(name))


def compiled_classifier(name: str) -> re.Pattern[str]:
    return re.compile(str(rule_manifest()["classifiers"][name]))


def candidate_prefixes() -> tuple[re.Pattern[str], ...]:
    return tuple(
        re.compile(str(pattern))
        for pattern in rule_manifest()["grammar"]["candidate_prefixes"]
    )
