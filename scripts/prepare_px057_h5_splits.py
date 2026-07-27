#!/usr/bin/env python
"""Prepare outcome-unseen residual-population splits for a future PX-057 H5.

This module is deliberately separate from model collection.  It verifies the
frozen H4 inputs and generated-ID evidence, reconstructs the pinned source
populations, removes only the 500 IDs actually generated in H4 calibration,
and deterministically partitions the residual populations.  The core returns
an in-memory bundle.  Files are written only when a caller supplies a new
output directory; there is no default H5 output path and no overwrite mode.

The resulting files are draft split evidence.  Creating them does not
authorize H5 model generation or turn H4 outcome-exposed data into
confirmatory evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]

H4_CONFIG = "configs/px057_h4_ltt_transfer_20260725.json"
H4_CONFIG_SHA256 = "0df81f0bb86d60869424ba12156ccc306ce3df280d6cecd25857f98785d03317"
H4_SPLIT_FREEZE = "manifests/px057_h4_20260725/split_freeze.json"
H4_SPLIT_FREEZE_SHA256 = (
    "5b142b8c04376ecd9b3c6f80adc4204b9d6280450edabbd30198b80c65422972"
)

GSM8K_SOURCE_URL = (
    "https://raw.githubusercontent.com/openai/grade-school-math/"
    "3101c7d5072418e28b9008a6636bde82a006892c/"
    "grade_school_math/data/test.jsonl"
)
GSM8K_SOURCE_SHA256 = (
    "3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14"
)
GSM8K_REPOSITORY_REVISION = "3101c7d5072418e28b9008a6636bde82a006892c"
GSM8K_SOURCE_N = 1319
GSM8K_H4_ELIGIBLE_N = 1119
GSM8K_H5_RESIDUAL_N = 619

ARC_SOURCE_URL = (
    "https://huggingface.co/datasets/allenai/ai2_arc/resolve/"
    "210d026faf9955653af8916fad021475a3f00453/"
    "ARC-Challenge/test-00000-of-00001.parquet"
)
ARC_SOURCE_SHA256 = (
    "62f03257e737aed263f55c6abf87c7bb0028a44a6bdd2a26eb1279eb42c1d1e9"
)
ARC_DATASET_REVISION = "210d026faf9955653af8916fad021475a3f00453"
ARC_SOURCE_N = 1172
ARC_H5_RESIDUAL_N = 672

GATE2_SELECTED = (
    "reports/adaptive_stopping_overthinking/gate2_full_cloud_20260724/"
    "extracted/px057_gate1_gpu_pilot/selected_rows.json"
)
GATE2_SELECTED_SHA256 = (
    "6203c728f838fda9b932f69c83f7c90eb2e04c65045b24071d5347d4aaa6fc7e"
)
GATE2_SELECTED_N = 200

H4_CALIBRATION = {
    "gsm8k": {
        "path": "manifests/px057_h4_20260725/gsm8k_calibration.jsonl",
        "sha256": "a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef",
    },
    "arc_challenge": {
        "path": "manifests/px057_h4_20260725/arc_challenge_calibration.jsonl",
        "sha256": "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224",
    },
}

H4_HOLDOUT = {
    "gsm8k": {
        "path": "manifests/px057_h4_20260725/gsm8k_holdout.jsonl",
        "sha256": "48111d29fb29119a8838bad298e4639e3e59aaa345a88bf84f2704216574aa0f",
    },
    "arc_challenge": {
        "path": "manifests/px057_h4_20260725/arc_challenge_holdout.jsonl",
        "sha256": "406267317be881a73136642628c0692dcd284d62416287072e090a1e069a53c1",
    },
}

# The selected-row evidence is byte-identical to each corresponding frozen H4
# calibration manifest.  The trace evidence independently proves that every
# one of those 500 IDs received model generation.  Both ARC cells must agree.
H4_GENERATED_EVIDENCE = {
    "gsm8k": (
        {
            "kind": "selected_rows",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell1_llama31_gsm8k/calibration/selected_rows.jsonl"
            ),
            "sha256": "a48ef2c73edc6eec80428358feee3f38e1c5182dac441ca39c339fb9b54f00ef",
        },
        {
            "kind": "reasoning_traces",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell1_llama31_gsm8k/calibration/reasoning_traces.jsonl"
            ),
            "sha256": "08cf9d0df9d9f73ef793a10c3d65c06018a09b2bfb7e3f685cb272794d7ec4fa",
        },
    ),
    "arc_challenge": (
        {
            "kind": "cell2_selected_rows",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell2_qwen25_arc/calibration/selected_rows.jsonl"
            ),
            "sha256": "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224",
        },
        {
            "kind": "cell2_reasoning_traces",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell2_qwen25_arc/calibration/reasoning_traces.jsonl"
            ),
            "sha256": "966295c0b9b0f51bc1c34ff6f7029d95eb54f066b89d7342bf0aa3a40664740b",
        },
        {
            "kind": "cell3_selected_rows",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell3_llama31_arc/calibration/selected_rows.jsonl"
            ),
            "sha256": "90402e3c87598ef754583915508adea852362690b0da203f88ff8e9acd1a6224",
        },
        {
            "kind": "cell3_reasoning_traces",
            "path": (
                "reports/adaptive_stopping_overthinking/h4_20260725/"
                "cell3_llama31_arc/calibration/reasoning_traces.jsonl"
            ),
            "sha256": "5a43ea763555bd442f467276ca6326fae61214d08c9c5fbecbc7d65e733a8a99",
        },
    ),
}

CALIBRATION_SEED = 5751
HOLDOUT_SEED = 5752
UNUSED_SEED = 5753

SPLIT_SPECS = {
    "gsm8k": {"calibration": 435, "holdout": 150, "unused": 34},
    "arc_challenge": {"calibration": 489, "holdout": 150, "unused": 33},
}

OUTPUT_FILENAMES = {
    "gsm8k": {
        "calibration": "gsm8k_calibration.jsonl",
        "holdout": "gsm8k_holdout.jsonl",
        "unused": "gsm8k_unused.jsonl",
    },
    "arc_challenge": {
        "calibration": "arc_challenge_calibration.jsonl",
        "holdout": "arc_challenge_holdout.jsonl",
        "unused": "arc_challenge_unused.jsonl",
    },
}

# These byte and ordered-ID hashes were independently derived from the pinned
# sources, exact Gate-2 exclusion, exact H4 generated IDs, and seeds above.
EXPECTED_ARTIFACTS = {
    "gsm8k": {
        "residual": {
            "rows": 619,
            "sha256": "fb47377f64bef1c018ccd1e8d8b7adb23fd908e7b1cfdef60570632ff5f38c21",
            "id_sha256": "76aace9d9b2040295a90ec4f7b8c9e95a24b70b827e8b3a63e48045ffbf1c2f2",
        },
        "calibration": {
            "rows": 435,
            "sha256": "32d2bdc360c64437b35ca6570f2566ea931b6fcf4ab0eb12d9fbeac747789643",
            "id_sha256": "99700c6c320e505ab41c183e6c29032cc13a0b0a1c6d8a217e7887366a44675f",
        },
        "holdout": {
            "rows": 150,
            "sha256": "52c6f1ee567ffe8f67f593ce52b9dbd673c3a8ea91b47202539b0a6c112971d7",
            "id_sha256": "4fa69267fbb03f1593e92519bbe48ea9fd0bbb4e30f62e286953e6e009bf164a",
        },
        "unused": {
            "rows": 34,
            "sha256": "7095fea51f67ba257bdb49ad4ba4f83027834e3d120bb0ad30ef9da3dc964c9c",
            "id_sha256": "93a60d08602814a1339ffa79ed6ce24c35ba3207b18c9b3e8fbbc1e6c4df6dfc",
        },
    },
    "arc_challenge": {
        "residual": {
            "rows": 672,
            "sha256": "050b413597cc7892ac980ec5e47c242657d8969e2aac0b509ac034753ec847d8",
            "id_sha256": "2f4102f1dccef965ef2d6c72331495192ca93f173b1f8876059ffa947992c617",
        },
        "calibration": {
            "rows": 489,
            "sha256": "714472dadbd7491fc6120cc40438b84add7260300729db236d9fb7f8ceaec211",
            "id_sha256": "20bdfc3bd111959abe41e80adf486f11b58c1da5e8d73e06ccae191c59e3a46a",
        },
        "holdout": {
            "rows": 150,
            "sha256": "e8284d9b352cfe8092e5cfa43035d3e8a7dfbe33d11aa9e9fa04b2d38b1e0c0f",
            "id_sha256": "6ee6c2dd2f2207664e08d7457ba713073d00b6ca99f0cac3cb32d2bcba6b20ea",
        },
        "unused": {
            "rows": 33,
            "sha256": "9961700b299028e3e74c30ed9bf6257a2cccf005e1fd89401ede1561382d6ea2",
            "id_sha256": "c3f0bd3df42c7b95dd745a5fd3993431d86f08c4024723ce947750069ec17a16",
        },
    },
}


@dataclass(frozen=True)
class H4Evidence:
    calibration_rows: Mapping[str, tuple[dict[str, Any], ...]]
    generated_ids: Mapping[str, frozenset[str]]
    holdout_ids: Mapping[str, frozenset[str]]
    gate2_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PreparedSplitBundle:
    rows: Mapping[str, Mapping[str, tuple[dict[str, Any], ...]]]
    freeze: Mapping[str, Any]


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(dict(row)) for row in rows)


def ordered_id_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    return sha256_bytes(
        canonical_json_bytes([str(row["question_id"]) for row in rows])
    )


def _read_hash_bound(path: Path, expected_sha256: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"required frozen artifact is missing: {path}")
    content = path.read_bytes()
    observed = sha256_bytes(content)
    if observed != expected_sha256:
        raise ValueError(
            f"frozen artifact SHA-256 mismatch for {path}: "
            f"{observed} != {expected_sha256}"
        )
    return content


def _parse_jsonl(content: bytes, *, label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label}: not UTF-8") from exc
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"{label}:{line_number}: blank JSONL line")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label}:{line_number}: invalid JSON") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{label}:{line_number}: expected object")
        rows.append(row)
    if not rows:
        raise ValueError(f"{label}: empty JSONL")
    return rows


def _unique_ids(
    rows: Sequence[Mapping[str, Any]], *, label: str, expected_n: int | None = None
) -> tuple[str, ...]:
    ids: list[str] = []
    for index, row in enumerate(rows):
        question_id = str(row.get("question_id", "")).strip()
        if not question_id:
            raise ValueError(f"{label}: row {index} has no question_id")
        ids.append(question_id)
    if len(ids) != len(set(ids)):
        raise ValueError(f"{label}: duplicate question_id")
    if expected_n is not None and len(ids) != expected_n:
        raise ValueError(f"{label}: expected {expected_n} rows, observed {len(ids)}")
    return tuple(ids)


def _read_json_array(content: bytes, *, label: str) -> list[dict[str, Any]]:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label}: invalid UTF-8 JSON") from exc
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError(f"{label}: expected an array of objects")
    return value


def verify_h4_evidence(repo_root: Path = ROOT) -> H4Evidence:
    """Verify exact H4 identities and prove the generated calibration ID sets."""

    repo_root = repo_root.resolve()
    config_content = _read_hash_bound(repo_root / H4_CONFIG, H4_CONFIG_SHA256)
    split_freeze_content = _read_hash_bound(
        repo_root / H4_SPLIT_FREEZE, H4_SPLIT_FREEZE_SHA256
    )
    config = json.loads(config_content.decode("utf-8"))
    split_freeze = json.loads(split_freeze_content.decode("utf-8"))

    gsm_config = config.get("datasets", {}).get("gsm8k", {})
    arc_config = config.get("datasets", {}).get("arc_challenge", {})
    if (
        gsm_config.get("source_url") != GSM8K_SOURCE_URL
        or gsm_config.get("source_sha256") != GSM8K_SOURCE_SHA256
        or int(gsm_config.get("source_population_size", -1)) != GSM8K_SOURCE_N
        or int(gsm_config.get("eligible_population_size", -1))
        != GSM8K_H4_ELIGIBLE_N
        or arc_config.get("source_url") != ARC_SOURCE_URL
        or arc_config.get("source_sha256") != ARC_SOURCE_SHA256
        or int(arc_config.get("source_population_size", -1)) != ARC_SOURCE_N
    ):
        raise ValueError("frozen H4 config source bindings differ from H5 audit")
    if (
        split_freeze.get("gsm8k", {}).get("source_sha256")
        != GSM8K_SOURCE_SHA256
        or split_freeze.get("arc_challenge", {}).get("source_sha256")
        != ARC_SOURCE_SHA256
        or split_freeze.get("gsm8k", {})
        .get("gate2_selected_rows", {})
        .get("sha256")
        != GATE2_SELECTED_SHA256
    ):
        raise ValueError("frozen H4 split source identities differ from H5 audit")

    gate2_content = _read_hash_bound(
        repo_root / GATE2_SELECTED, GATE2_SELECTED_SHA256
    )
    gate2_rows = _read_json_array(gate2_content, label=GATE2_SELECTED)
    _unique_ids(gate2_rows, label=GATE2_SELECTED, expected_n=GATE2_SELECTED_N)

    calibration_rows: dict[str, tuple[dict[str, Any], ...]] = {}
    generated_ids: dict[str, frozenset[str]] = {}
    holdout_ids: dict[str, frozenset[str]] = {}
    for domain, metadata in H4_CALIBRATION.items():
        manifest_content = _read_hash_bound(
            repo_root / str(metadata["path"]), str(metadata["sha256"])
        )
        manifest_rows = _parse_jsonl(
            manifest_content, label=str(metadata["path"])
        )
        manifest_ids = _unique_ids(
            manifest_rows, label=str(metadata["path"]), expected_n=500
        )
        expected_freeze = split_freeze.get("files", {}).get(
            f"{domain}_calibration", {}
        )
        if (
            expected_freeze.get("sha256") != metadata["sha256"]
            or int(expected_freeze.get("rows", -1)) != 500
        ):
            raise ValueError(f"{domain}: H4 split freeze calibration mismatch")
        manifest_set = frozenset(manifest_ids)
        for evidence in H4_GENERATED_EVIDENCE[domain]:
            evidence_content = _read_hash_bound(
                repo_root / str(evidence["path"]), str(evidence["sha256"])
            )
            evidence_rows = _parse_jsonl(
                evidence_content, label=str(evidence["path"])
            )
            evidence_set = frozenset(
                _unique_ids(
                    evidence_rows,
                    label=str(evidence["path"]),
                    expected_n=500,
                )
            )
            if "reasoning_traces" in str(evidence["kind"]) and any(
                not isinstance(row.get("steps"), list)
                or len(row["steps"]) != 8
                for row in evidence_rows
            ):
                raise ValueError(
                    f"{domain}: generated trace evidence is not 500 by 8 rounds"
                )
            if evidence_set != manifest_set:
                raise ValueError(
                    f"{domain}: generated evidence {evidence['kind']} does not "
                    "equal the frozen H4 calibration IDs"
                )
        calibration_rows[domain] = tuple(manifest_rows)
        generated_ids[domain] = manifest_set

        holdout_metadata = H4_HOLDOUT[domain]
        holdout_content = _read_hash_bound(
            repo_root / str(holdout_metadata["path"]),
            str(holdout_metadata["sha256"]),
        )
        holdout_rows = _parse_jsonl(
            holdout_content, label=str(holdout_metadata["path"])
        )
        holdout_set = frozenset(
            _unique_ids(
                holdout_rows,
                label=str(holdout_metadata["path"]),
                expected_n=300,
            )
        )
        expected_holdout_freeze = split_freeze.get("files", {}).get(
            f"{domain}_holdout", {}
        )
        if (
            expected_holdout_freeze.get("sha256")
            != holdout_metadata["sha256"]
            or int(expected_holdout_freeze.get("rows", -1)) != 300
            or holdout_set & manifest_set
        ):
            raise ValueError(f"{domain}: H4 holdout identity or disjointness mismatch")
        holdout_ids[domain] = holdout_set

    return H4Evidence(
        calibration_rows=calibration_rows,
        generated_ids=generated_ids,
        holdout_ids=holdout_ids,
        gate2_rows=tuple(gate2_rows),
    )


def download_source(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "px057-h5-residual-splitter/20260727"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def _verified_source(
    fetcher: Callable[[str], bytes], url: str, expected_sha256: str
) -> bytes:
    content = fetcher(url)
    if not isinstance(content, bytes):
        raise TypeError("source fetcher must return bytes")
    observed = sha256_bytes(content)
    if observed != expected_sha256:
        raise ValueError(
            f"source SHA-256 mismatch for {url}: {observed} != {expected_sha256}"
        )
    return content


def _normalize_numeric(value: str) -> str:
    cleaned = value.replace(",", "").strip()
    try:
        number = float(cleaned)
    except ValueError:
        return cleaned.lower()
    if not number.is_integer():
        return f"{number:.10g}"
    return str(int(number))


def _gsm8k_gold(answer: str) -> str:
    parts = answer.rsplit("####", 1)
    if len(parts) != 2:
        raise ValueError("GSM8K source answer lacks #### marker")
    return _normalize_numeric(parts[1])


def build_gsm8k_population(
    content: bytes, gate2_rows: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Reconstruct the exact H4-eligible GSM8K population."""

    if sha256_bytes(content) != GSM8K_SOURCE_SHA256:
        raise ValueError("GSM8K source hash mismatch")
    try:
        source = [
            json.loads(line)
            for line in content.decode("utf-8").splitlines()
            if line.strip()
        ]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid pinned GSM8K source") from exc
    if len(source) != GSM8K_SOURCE_N or not all(
        isinstance(row, dict) for row in source
    ):
        raise ValueError("unexpected pinned GSM8K source population")

    gate2_ids = frozenset(
        _unique_ids(gate2_rows, label="Gate-2 exclusions", expected_n=200)
    )
    source_ids = {f"gsm8k-test-{index}" for index in range(len(source))}
    if not gate2_ids <= source_ids:
        raise ValueError("Gate-2 exclusions contain IDs outside pinned GSM8K")

    population: list[dict[str, Any]] = []
    for source_index, row in enumerate(source):
        question_id = f"gsm8k-test-{source_index}"
        if question_id in gate2_ids:
            continue
        if "question" not in row or "answer" not in row:
            raise ValueError("GSM8K source row lacks question or answer")
        population.append(
            {
                "question_id": question_id,
                "domain": "gsm8k",
                "answer_type": "numeric",
                "question": str(row["question"]),
                "gold_answer": _gsm8k_gold(str(row["answer"])),
                "source_index": source_index,
            }
        )
    _unique_ids(population, label="H4-eligible GSM8K", expected_n=1119)
    return population


def build_arc_population(content: bytes) -> list[dict[str, Any]]:
    """Reconstruct the exact pinned ARC-Challenge test population."""

    if sha256_bytes(content) != ARC_SOURCE_SHA256:
        raise ValueError("ARC-Challenge source hash mismatch")
    import pandas as pd

    try:
        frame = pd.read_parquet(io.BytesIO(content))
    except Exception as exc:
        raise ValueError("invalid pinned ARC-Challenge parquet") from exc
    if len(frame) != ARC_SOURCE_N:
        raise ValueError("unexpected pinned ARC-Challenge source population")

    rows: list[dict[str, Any]] = []
    for source_index, record in frame.iterrows():
        try:
            choices = record["choices"]
            labels = [str(value) for value in list(choices["label"])]
            texts = [str(value) for value in list(choices["text"])]
            if not labels or len(labels) != len(texts):
                raise ValueError("invalid ARC choices")
            rows.append(
                {
                    "question_id": f"arc-challenge-test-{record['id']}",
                    "domain": "arc_challenge",
                    "answer_type": "choice",
                    "question": str(record["question"]),
                    "choice_labels": labels,
                    "choices": [
                        {"label": label, "text": text}
                        for label, text in zip(labels, texts)
                    ],
                    "gold_answer": str(record["answerKey"]),
                    "source_index": int(source_index),
                    "source_id": str(record["id"]),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"invalid ARC source row at {source_index}") from exc
    _unique_ids(rows, label="ARC-Challenge population", expected_n=1172)
    return rows


def _verify_generated_rows_match_source(
    generated_rows: Sequence[Mapping[str, Any]],
    population: Sequence[Mapping[str, Any]],
    *,
    label: str,
) -> None:
    source_by_id = {str(row["question_id"]): dict(row) for row in population}
    for row in generated_rows:
        question_id = str(row["question_id"])
        if question_id not in source_by_id:
            raise ValueError(f"{label}: generated ID is not in pinned population")
        if dict(row) != source_by_id[question_id]:
            raise ValueError(
                f"{label}: frozen H4 row differs from pinned source for {question_id}"
            )


def residual_population(
    population: Sequence[Mapping[str, Any]],
    generated_ids: Iterable[str],
    *,
    expected_n: int,
    label: str,
) -> list[dict[str, Any]]:
    """Subtract exactly the proven H4-generated IDs, preserving source order."""

    _unique_ids(population, label=f"{label} source population")
    removed = frozenset(str(value) for value in generated_ids)
    if len(removed) != 500:
        raise ValueError(f"{label}: exactly 500 generated IDs are required")
    population_ids = {str(row["question_id"]) for row in population}
    if not removed <= population_ids:
        raise ValueError(f"{label}: generated IDs are outside the source population")
    residual = [
        dict(row)
        for row in population
        if str(row["question_id"]) not in removed
    ]
    _unique_ids(residual, label=f"{label} residual", expected_n=expected_n)
    return residual


def hash_rank(
    rows: Sequence[Mapping[str, Any]], seed: int
) -> list[dict[str, Any]]:
    return sorted(
        (dict(row) for row in rows),
        key=lambda row: (
            hashlib.sha256(
                f"{seed}:{row['question_id']}".encode("utf-8")
            ).hexdigest(),
            str(row["question_id"]),
        ),
    )


def partition_residual(
    residual: Sequence[Mapping[str, Any]],
    *,
    calibration_n: int,
    holdout_n: int,
    unused_n: int,
    calibration_seed: int = CALIBRATION_SEED,
    holdout_seed: int = HOLDOUT_SEED,
    unused_seed: int = UNUSED_SEED,
) -> dict[str, list[dict[str, Any]]]:
    """Pure three-stage hash partition with explicit disjointness checks."""

    residual_ids = frozenset(_unique_ids(residual, label="residual population"))
    if min(calibration_n, holdout_n, unused_n) < 0:
        raise ValueError("split sizes must be nonnegative")
    if calibration_n + holdout_n + unused_n != len(residual):
        raise ValueError("split sizes must exhaust the residual population")

    calibration = hash_rank(residual, calibration_seed)[:calibration_n]
    calibration_ids = {str(row["question_id"]) for row in calibration}
    after_calibration = [
        row for row in residual if str(row["question_id"]) not in calibration_ids
    ]
    holdout = hash_rank(after_calibration, holdout_seed)[:holdout_n]
    holdout_ids = {str(row["question_id"]) for row in holdout}
    after_holdout = [
        row
        for row in after_calibration
        if str(row["question_id"]) not in holdout_ids
    ]
    unused = hash_rank(after_holdout, unused_seed)
    if len(unused) != unused_n:
        raise AssertionError("unused split length differs from frozen design")

    partitions = {
        "calibration": calibration,
        "holdout": holdout,
        "unused": unused,
    }
    id_sets = {
        name: {str(row["question_id"]) for row in rows}
        for name, rows in partitions.items()
    }
    if (
        id_sets["calibration"] & id_sets["holdout"]
        or id_sets["calibration"] & id_sets["unused"]
        or id_sets["holdout"] & id_sets["unused"]
        or set().union(*id_sets.values()) != residual_ids
    ):
        raise AssertionError("residual partitions are not a disjoint exhaustion")
    return partitions


def verify_expected_artifacts(
    domain: str,
    residual: Sequence[Mapping[str, Any]],
    partitions: Mapping[str, Sequence[Mapping[str, Any]]],
) -> None:
    expected = EXPECTED_ARTIFACTS[domain]
    observed_groups: dict[str, Sequence[Mapping[str, Any]]] = {
        "residual": residual,
        **partitions,
    }
    for name, rows in observed_groups.items():
        metadata = expected[name]
        observed = {
            "rows": len(rows),
            "sha256": sha256_bytes(jsonl_bytes(rows)),
            "id_sha256": ordered_id_sha256(rows),
        }
        if observed != metadata:
            raise ValueError(
                f"{domain} {name} differs from the audited expected artifact: "
                f"{observed} != {metadata}"
            )


def _freeze_manifest(
    rows: Mapping[str, Mapping[str, tuple[dict[str, Any], ...]]]
) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for domain, partitions in rows.items():
        for split_name, split_rows in partitions.items():
            key = f"{domain}_{split_name}"
            files[key] = {
                "path": OUTPUT_FILENAMES[domain][split_name],
                "rows": len(split_rows),
                "sha256": sha256_bytes(jsonl_bytes(split_rows)),
                "id_sha256": ordered_id_sha256(split_rows),
            }

    return {
        "px_id": "PX-057",
        "stage": "H5_draft_residual_population_split",
        "status": "DRAFT_NOT_AUTHORIZED_FOR_GENERATION",
        "confirmatory_evidence": False,
        "claim_boundary": (
            "This deterministic draft excludes every H4-generated calibration "
            "ID. It does not authorize model generation or constitute H5 evidence."
        ),
        "selection_algorithm": (
            "Subtract exact H4-generated calibration IDs; select calibration by "
            "SHA256('5751:<question_id>') ascending; select holdout from the "
            "remainder by SHA256('5752:<question_id>') ascending; order the "
            "unused remainder by SHA256('5753:<question_id>') ascending; use "
            "question_id as every collision tie-break."
        ),
        "seeds": {
            "calibration": CALIBRATION_SEED,
            "holdout": HOLDOUT_SEED,
            "unused": UNUSED_SEED,
        },
        "h4_bindings": {
            "config": {"path": H4_CONFIG, "sha256": H4_CONFIG_SHA256},
            "split_freeze": {
                "path": H4_SPLIT_FREEZE,
                "sha256": H4_SPLIT_FREEZE_SHA256,
            },
            "gate2_selected": {
                "path": GATE2_SELECTED,
                "rows": GATE2_SELECTED_N,
                "sha256": GATE2_SELECTED_SHA256,
            },
            "calibration_manifests": H4_CALIBRATION,
            "untouched_holdout_manifests": H4_HOLDOUT,
            "generated_evidence": H4_GENERATED_EVIDENCE,
        },
        "populations": {
            "gsm8k": {
                "source_url": GSM8K_SOURCE_URL,
                "repository_revision": GSM8K_REPOSITORY_REVISION,
                "source_sha256": GSM8K_SOURCE_SHA256,
                "source_n": GSM8K_SOURCE_N,
                "gate2_excluded_n": GATE2_SELECTED_N,
                "h4_eligible_n": GSM8K_H4_ELIGIBLE_N,
                "h4_generated_calibration_n": 500,
                "h5_residual_n": GSM8K_H5_RESIDUAL_N,
                "residual_sha256": EXPECTED_ARTIFACTS["gsm8k"]["residual"][
                    "sha256"
                ],
                "residual_id_sha256": EXPECTED_ARTIFACTS["gsm8k"]["residual"][
                    "id_sha256"
                ],
            },
            "arc_challenge": {
                "source_url": ARC_SOURCE_URL,
                "dataset_revision": ARC_DATASET_REVISION,
                "source_sha256": ARC_SOURCE_SHA256,
                "source_n": ARC_SOURCE_N,
                "h4_generated_calibration_n": 500,
                "h5_residual_n": ARC_H5_RESIDUAL_N,
                "residual_sha256": EXPECTED_ARTIFACTS["arc_challenge"][
                    "residual"
                ]["sha256"],
                "residual_id_sha256": EXPECTED_ARTIFACTS["arc_challenge"][
                    "residual"
                ]["id_sha256"],
            },
        },
        "files": files,
        "cells": {
            "cell1_llama31_gsm8k": {
                "calibration": OUTPUT_FILENAMES["gsm8k"]["calibration"],
                "holdout": OUTPUT_FILENAMES["gsm8k"]["holdout"],
                "unused": OUTPUT_FILENAMES["gsm8k"]["unused"],
            },
            "cell2_qwen25_arc": {
                "calibration": OUTPUT_FILENAMES["arc_challenge"]["calibration"],
                "holdout": OUTPUT_FILENAMES["arc_challenge"]["holdout"],
                "unused": OUTPUT_FILENAMES["arc_challenge"]["unused"],
            },
            "cell3_llama31_arc": {
                "calibration": OUTPUT_FILENAMES["arc_challenge"]["calibration"],
                "holdout": OUTPUT_FILENAMES["arc_challenge"]["holdout"],
                "unused": OUTPUT_FILENAMES["arc_challenge"]["unused"],
            },
        },
        "checks": {
            "exact_h4_hashes": True,
            "exact_h4_generated_id_sets": True,
            "source_hashes_and_membership": True,
            "only_h4_generated_calibration_ids_subtracted": True,
            "expected_residual_sizes": True,
            "partitions_disjoint_and_exhaustive": True,
            "expected_partition_hashes": True,
            "arc_partitions_reused_by_c2_c3": True,
            "h4_holdouts_untouched": True,
        },
    }


def prepare_split_bundle(
    repo_root: Path = ROOT,
    *,
    source_fetcher: Callable[[str], bytes] = download_source,
) -> PreparedSplitBundle:
    """Verify every input and return the exact deterministic split bundle."""

    h4 = verify_h4_evidence(repo_root)
    gsm_content = _verified_source(
        source_fetcher, GSM8K_SOURCE_URL, GSM8K_SOURCE_SHA256
    )
    arc_content = _verified_source(source_fetcher, ARC_SOURCE_URL, ARC_SOURCE_SHA256)
    populations = {
        "gsm8k": build_gsm8k_population(gsm_content, h4.gate2_rows),
        "arc_challenge": build_arc_population(arc_content),
    }
    expected_residual_n = {
        "gsm8k": GSM8K_H5_RESIDUAL_N,
        "arc_challenge": ARC_H5_RESIDUAL_N,
    }

    frozen_rows: dict[str, dict[str, tuple[dict[str, Any], ...]]] = {}
    for domain, population in populations.items():
        _verify_generated_rows_match_source(
            h4.calibration_rows[domain], population, label=domain
        )
        residual = residual_population(
            population,
            h4.generated_ids[domain],
            expected_n=expected_residual_n[domain],
            label=domain,
        )
        residual_ids = {str(row["question_id"]) for row in residual}
        if not h4.holdout_ids[domain] <= residual_ids:
            raise ValueError(f"{domain}: an untouched H4 holdout ID left the residual")
        spec = SPLIT_SPECS[domain]
        partitions = partition_residual(
            residual,
            calibration_n=spec["calibration"],
            holdout_n=spec["holdout"],
            unused_n=spec["unused"],
        )
        verify_expected_artifacts(domain, residual, partitions)
        frozen_rows[domain] = {
            name: tuple(rows) for name, rows in partitions.items()
        }

    freeze = _freeze_manifest(frozen_rows)
    if (
        freeze["cells"]["cell2_qwen25_arc"]
        != freeze["cells"]["cell3_llama31_arc"]
    ):
        raise AssertionError("C2 and C3 must reuse identical ARC partitions")
    return PreparedSplitBundle(rows=frozen_rows, freeze=freeze)


def _is_relative_to(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def write_split_bundle(
    bundle: PreparedSplitBundle,
    output_dir: Path,
    *,
    repo_root: Path = ROOT,
) -> dict[str, Any]:
    """Write a verified bundle only to a caller-supplied, new draft directory."""

    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    protected = (
        (repo_root / "manifests/px057_h4_20260725").resolve(),
        (
            repo_root
            / "reports/adaptive_stopping_overthinking/h4_20260725"
        ).resolve(),
    )
    if any(_is_relative_to(output_dir, path) for path in protected):
        raise ValueError("output directory may not be inside protected H4 evidence")
    if output_dir.exists():
        raise FileExistsError(f"draft output already exists: {output_dir}")

    payloads: dict[str, bytes] = {}
    for domain, partitions in bundle.rows.items():
        for split_name, rows in partitions.items():
            filename = OUTPUT_FILENAMES[domain][split_name]
            content = jsonl_bytes(rows)
            expected = EXPECTED_ARTIFACTS[domain][split_name]["sha256"]
            if sha256_bytes(content) != expected:
                raise ValueError(f"refusing to write unexpected {filename} bytes")
            payloads[filename] = content
    payloads["split_freeze.json"] = canonical_json_bytes(bundle.freeze)

    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, content in payloads.items():
        path = output_dir / filename
        with path.open("xb") as handle:
            handle.write(content)
        if path.read_bytes() != content:
            raise OSError(f"post-write byte verification failed: {path}")
    return {
        "output_dir": str(output_dir),
        "files": {
            filename: {
                "bytes": len(content),
                "sha256": sha256_bytes(content),
            }
            for filename, content in sorted(payloads.items())
        },
        "status": "DRAFT_WRITTEN_NOT_AUTHORIZED_FOR_GENERATION",
    }


def _check_summary(bundle: PreparedSplitBundle) -> dict[str, Any]:
    return {
        "status": "PASS_NO_FILES_WRITTEN",
        "stage": bundle.freeze["stage"],
        "populations": bundle.freeze["populations"],
        "files": bundle.freeze["files"],
        "checks": bundle.freeze["checks"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="New caller-selected draft H5 directory; no default is provided.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify and derive all hashes in memory without writing files.",
    )
    args = parser.parse_args()
    if args.check_only and args.output_dir is not None:
        parser.error("--check-only and --output-dir are mutually exclusive")
    if not args.check_only and args.output_dir is None:
        parser.error("either --check-only or --output-dir is required")

    bundle = prepare_split_bundle(args.repo_root)
    result = (
        _check_summary(bundle)
        if args.check_only
        else write_split_bundle(
            bundle, args.output_dir, repo_root=args.repo_root
        )
    )
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
