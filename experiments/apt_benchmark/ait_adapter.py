"""Exact source-line labels for the publicly documented AIT-LDS source view.

This does not assign author interval labels to unrelated alerts. Source line
numbers are retained until after the join, and no label metadata enters text.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import ipaddress
import json
import math
from pathlib import Path
import re

import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from .contracts import split_index, sha256_file


HASH_DIMENSIONS = 128


def normalized_text(raw: str, source_type: str) -> str:
    text = re.sub(r"msg=audit\([0-9.]+:\d+\)", "audit_event", raw)
    text = re.sub(r"^[A-Z][a-z]{2}\s+\d+\s+\d\d:\d\d:\d\d\s+\S+\s+", "", text)
    text = re.sub(r"\[\d{2}/[A-Za-z]{3}/\d{4}:[^\]]+\]", " TIME ", text)
    text = re.sub(r"\[(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) [^\]]+\]", " TIME ", text)
    text = re.sub(r'\b(hostname|host|node|addr|saddr|daddr|src_ip|dst_ip)=(?:"[^"\n]*"|\'[^\'\n]*\'|[^\s]+)',
                  lambda m: m[1].casefold() + "=HOST", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", " IP ", text)
    text = re.sub(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b", " MAC ", text)
    def mask_ipv6(match):
        try:
            ipaddress.IPv6Address(match[0])
        except ValueError:
            return match[0]
        return " IP "
    text = re.sub(r"(?<![\w:])[0-9A-Fa-f:]*:[0-9A-Fa-f:]+(?![\w:])", mask_ipv6, text)
    text = re.sub(r"\b(pid|ppid|ses|session|inode)=[^\s]+", r"\1=ID", text)
    text = re.sub(r"\b(auid|uid|gid|euid|egid|suid|fsuid|fsgid)=([0-9]+)",
                  lambda m: m[1] + ("=root" if m[2] == "0" else "=user"), text)
    text = re.sub(r"\b[0-9A-Fa-f]{32,}\b", " LONG_HEX ", text)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", " NUM ", text)
    return "source_" + source_type + " " + text[:8192]


def source_timestamp(raw, source_type):
    if source_type == "audit":
        match = re.search(r"msg=audit\(([0-9.]+):\d+\)", raw)
        if match:
            value = float(match[1])
            if not math.isfinite(value):
                raise ValueError("Nonfinite source timestamp")
            return value
        return None
    if source_type == "apache_access":
        match = re.search(r"\[(\d{2}/[A-Za-z]{3}/\d{4}:\d{2}:\d{2}:\d{2} [+-]\d{4})\]", raw)
        if match:
            return datetime.strptime(match[1], "%d/%b/%Y:%H:%M:%S %z").timestamp()
    # Syslog and Apache error time zones are not guessed.
    return None


def classify_source(path):
    if path.name.endswith((".gz", ".bz2", ".xz", ".zip")):
        raise ValueError(f"Compressed source requires separate qualification: {path}")
    if re.fullmatch(r"audit\.log(?:\.\d+)?", path.name):
        return "audit"
    if re.fullmatch(r"auth\.log(?:\.\d+)?", path.name):
        return "auth"
    if "access" in path.name:
        return "apache_access"
    if "error" in path.name:
        return "apache_error"
    raise ValueError(f"Unqualified source type: {path}")


def load_ait(root: Path, protocol):
    root = Path(root)
    roles = split_index(protocol)
    rows, texts, files, source_keys = [], [], [], set()
    for scenario, role in roles.items():
        scenario_root = root / scenario
        label_root = scenario_root / "labels" / "intranet_server" / "logs"
        if not label_root.exists():
            raise ValueError(f"Missing qualified labels: {scenario}")
        paired_file_count = 0
        for label_path in sorted(label_root.rglob("*")):
            if not label_path.is_file():
                continue
            relative = label_path.relative_to(scenario_root / "labels")
            raw_path = scenario_root / "gather" / relative
            if not raw_path.is_file():
                raise ValueError(f"Label file lacks matching raw source: {relative}")
            source_type = classify_source(raw_path)
            paired_file_count += 1
            annotations = {}
            for line in label_path.read_text(encoding="utf-8").splitlines():
                value = json.loads(line)
                if not isinstance(value, dict) or "line" not in value or "labels" not in value:
                    raise ValueError("Invalid original source annotation schema")
                number = value["line"]
                if type(number) is not int or number < 1 or number in annotations:
                    raise ValueError("Invalid/duplicate original source line")
                labels = value["labels"]
                if not isinstance(labels, list) or not labels or not all(isinstance(x, str) and x.strip() for x in labels):
                    raise ValueError("Unknown/empty annotation cannot be made benign")
                annotations[number] = sorted(set(labels))
            line_count = 0
            with raw_path.open(encoding="utf-8", errors="strict") as handle:
                for number, raw in enumerate(handle, 1):
                    line_count = number
                    key = f"{scenario}/{relative.as_posix()}:{number}"
                    if key in source_keys:
                        raise ValueError("Duplicate source record")
                    source_keys.add(key)
                    labels = annotations.get(number, [])
                    rows.append({"id": key, "scenario": scenario, "split": role,
                                 "source_type": source_type, "line_number": number,
                                 "y": int(bool(labels)), "stages": labels,
                                 "event_at": source_timestamp(raw, source_type)})
                    texts.append(normalized_text(raw, source_type))
            if annotations and max(annotations) > line_count:
                raise ValueError("Annotation beyond end of original source file")
            files.append({"scenario": scenario, "source": relative.as_posix(),
                          "source_sha256": sha256_file(raw_path),
                          "labels_sha256": sha256_file(label_path),
                          "rows": line_count, "annotated_rows": len(annotations)})
        if not paired_file_count:
            raise ValueError(f"No qualified raw/label source pairs: {scenario}")
    vectorizer = HashingVectorizer(n_features=HASH_DIMENSIONS, alternate_sign=False,
                                  ngram_range=(1, 2), norm="l2", dtype=np.float32)
    X = vectorizer.transform(texts).toarray()
    y = np.array([r["y"] for r in rows], dtype=np.int8)
    qualification = {"rows": len(rows), "attack_rows": int(y.sum()),
                     "benign_rows": int((1-y).sum()), "files": files,
                     "feature_dimensions": HASH_DIMENSIONS,
                     "negative_label_basis": "Explicit author closed-world policy for paired raw logs, Zenodo19483937",
                     "source": "https://zenodo.org/records/19483937",
                     "stage_counts": dict(Counter(s for r in rows for s in r["stages"])),
                     "parseable_event_time_rows": sum(r["event_at"] is not None for r in rows),
                     "feature_text_is_label_blind": True,
                     "remaining_limitations": ["Source annotation rules are not independent analyst gold",
                         "Repeated attack recipes and lexical templates across runs",
                         "One selected intranet host and four log types; not whole enterprise telemetry",
                         "Line-level duplicates and multi-line audit events are correlated",
                         "Recognized identity patterns are masked; unstructured usernames, paths and payloads may retain lexical identity",
                         "No inferred time zone for auth/Apache error logs; no host-hour exposure claim"]}
    return X, y, rows, qualification
