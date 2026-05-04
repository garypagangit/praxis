from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd


MAPPING_PATH = Path(__file__).with_name("stage_mapping.json")


@lru_cache(maxsize=1)
def load_stage_mapping() -> dict:
    return json.loads(MAPPING_PATH.read_text(encoding="utf-8"))


STAGE_NAMES = tuple(load_stage_mapping()["stages"])


def normalize_attack_label(label: object) -> str:
    text = str(label).strip()
    text = text.replace("�", "-")
    text = " ".join(text.split())
    aliases = {
        "FTP-BruteForce": "FTP-BruteForce",
        "SSH-Bruteforce": "SSH-BruteForce",
        "DDOS attack-HOIC": "DDoS-HOIC",
        "DDOS attack-LOIC-UDP": "DDoS-LOIC-UDP",
        "DoS attacks-GoldenEye": "DoS-GoldenEye",
        "DoS attacks-Slowloris": "DoS-Slowloris",
        "DoS attacks-Hulk": "DoS-Hulk",
        "DoS attacks-SlowHTTPTest": "DoS-SlowHTTPTest",
        "DDoS attacks-LOIC-HTTP": "DDoS-LOIC-HTTP",
        "DDOS attack-LOIC-HTTP": "DDoS-LOIC-HTTP",
        "Web Attack - Brute Force": "Brute Force -Web",
        "Web Attack - XSS": "Brute Force -XSS",
        "Web Attack - Sql Injection": "SQL Injection",
        "Web Attack - SQL Injection": "SQL Injection",
        "Infilteration": "Infiltration",
    }
    return aliases.get(text, text)


def map_attack_label(label: object, unknown_stage: str = "Unknown") -> str:
    normalized = normalize_attack_label(label)
    labels = load_stage_mapping()["labels"]
    if normalized in labels:
        return str(labels[normalized]["stage"])
    return unknown_stage


def map_attack_series(labels: pd.Series, unknown_stage: str = "Unknown") -> pd.Series:
    return labels.map(lambda value: map_attack_label(value, unknown_stage=unknown_stage))


def stage_to_id(stage: str) -> int:
    if stage not in STAGE_NAMES:
        raise KeyError(f"Unknown stage: {stage}")
    return STAGE_NAMES.index(stage)
