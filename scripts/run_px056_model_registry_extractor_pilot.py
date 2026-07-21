#!/usr/bin/env python
"""PX-056 Gate 1 extractor and verifier pilot.

This runner uses controlled fixtures only. It validates the deterministic
identifier extractor and registry verifier before any model-output collection.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


USER_AGENT = "praxis-px056-model-registry-extractor-pilot/20260721"

HF_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)?$")
NGC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
LOCAL_PREFIX_RE = re.compile(r"^(?:\.{1,2}[\\/]|[A-Za-z]:[\\/]|/|~[\\/])")
CALL_RE = re.compile(
    r"\b(?P<func>(?:[A-Za-z_][A-Za-z0-9_]*\.)?(?:from_pretrained|load_dataset)|snapshot_download|hf_hub_download)"
    r"\s*\((?P<args>[^)]{0,800})\)",
    re.IGNORECASE | re.DOTALL,
)
STRING_RE = re.compile(r"(?P<quote>['\"])(?P<value>.*?)(?P=quote)")
KEYWORD_STRING_RE = re.compile(
    r"\b(?P<key>repo_id|repo_type|model_id|dataset_id|path_or_repo_id|pretrained_model_name_or_path)"
    r"\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
FIELD_RE = re.compile(
    r"(?im)^\s*['\"]?(?P<field>model_id|model_name|base_model|pretrained_model_name_or_path|repo_id|"
    r"dataset_id|dataset_name|dataset_repo|hf_model|hf_dataset|ngc_model|ngc_resource|ngc_model_id)['\"]?"
    r"\s*[:=]\s*['\"]?(?P<value>[^'\"\s,#}\]]+)"
)
HF_CLI_RE = re.compile(
    r"\b(?:hf|huggingface-cli)\s+download\b(?P<options>(?:\s+--[A-Za-z0-9_-]+(?:\s+[A-Za-z0-9_.-]+)?)*?)"
    r"\s+(?P<identifier>[A-Za-z0-9][A-Za-z0-9_.-]*(?:/[A-Za-z0-9][A-Za-z0-9_.-]*)?)",
    re.IGNORECASE,
)
NGC_URI_RE = re.compile(
    r"\bngc://(?:models?/)?(?P<identifier>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)",
    re.IGNORECASE,
)
NGC_CLI_RE = re.compile(
    r"\bngc\s+registry\s+model\s+download(?:-version)?\s+"
    r"(?P<identifier>[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)(?::[A-Za-z0-9_.-]+)?",
    re.IGNORECASE,
)

FIELD_NAMES = {
    "model_id",
    "model_name",
    "base_model",
    "pretrained_model_name_or_path",
    "repo_id",
    "dataset_id",
    "dataset_name",
    "dataset_repo",
    "hf_model",
    "hf_dataset",
    "ngc_model",
    "ngc_resource",
    "ngc_model_id",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def clean_identifier(value: str, registry: str) -> str:
    cleaned = value.strip().strip("'\"`")
    cleaned = cleaned.rstrip(".,;)]}\"'")
    if registry == "ngc" and ":" in cleaned:
        cleaned = cleaned.split(":", 1)[0]
    return cleaned


def is_local_or_url(value: str) -> bool:
    if LOCAL_PREFIX_RE.search(value):
        return True
    return value.startswith(("http://", "https://", "s3://", "gs://", "azure://"))


def valid_identifier(registry: str, kind: str, identifier: str) -> bool:
    if not identifier or is_local_or_url(identifier):
        return False
    if registry == "hf":
        if not HF_ID_RE.fullmatch(identifier):
            return False
        if kind == "model" and "/" not in identifier:
            return False
        return True
    if registry == "ngc":
        return bool(NGC_ID_RE.fullmatch(identifier))
    return False


def determine_hf_call_kind(func: str, args: str) -> str:
    if func.lower().endswith("load_dataset"):
        return "dataset"
    repo_type = None
    for match in KEYWORD_STRING_RE.finditer(args):
        if match.group("key").lower() == "repo_type":
            repo_type = match.group("value").lower()
    return "dataset" if repo_type == "dataset" else "model"


def registry_kind_for_field(field: str) -> tuple[str, str]:
    normalized = field.lower()
    if normalized.startswith("ngc"):
        return "ngc", "model"
    return "hf", "dataset" if "dataset" in normalized else "model"


def first_repo_argument(args: str) -> str | None:
    keyword_values: dict[str, str] = {}
    for match in KEYWORD_STRING_RE.finditer(args):
        keyword_values[match.group("key").lower()] = match.group("value")
    for key in ("repo_id", "path_or_repo_id", "model_id", "dataset_id", "pretrained_model_name_or_path"):
        if key in keyword_values:
            return keyword_values[key]
    first = STRING_RE.search(args)
    return first.group("value") if first else None


def add_extraction(
    records: list[dict[str, Any]],
    fixture_id: str,
    text: str,
    registry: str,
    kind: str,
    identifier: str,
    source_pattern: str,
    start: int,
    end: int,
) -> None:
    cleaned = clean_identifier(identifier, registry)
    if not valid_identifier(registry, kind, cleaned):
        return
    key = (fixture_id, registry, kind, cleaned)
    for record in records:
        if (record["fixture_id"], record["registry"], record["kind"], record["identifier"]) == key:
            if source_pattern not in record["source_patterns"]:
                record["source_patterns"].append(source_pattern)
            return
    records.append(
        {
            "fixture_id": fixture_id,
            "registry": registry,
            "kind": kind,
            "identifier": cleaned,
            "source_patterns": [source_pattern],
            "span": [start, end],
            "text_sha256": sha256_text(text),
        }
    )


def add_field_extraction(
    records: list[dict[str, Any]],
    fixture_id: str,
    text: str,
    field: str,
    value: Any,
    source_pattern: str,
    start: int = 0,
    end: int = 0,
) -> None:
    if not isinstance(value, str):
        return
    registry, kind = registry_kind_for_field(field)
    add_extraction(records, fixture_id, text, registry, kind, value, source_pattern, start, end)


def walk_json_fields(value: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and key.lower() in FIELD_NAMES and isinstance(child, str):
                found.append((key, child))
            found.extend(walk_json_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_json_fields(child))
    return found


def extract_json_fields(text: str, fixture_id: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    records: list[dict[str, Any]] = []
    for field, value in walk_json_fields(payload):
        add_field_extraction(records, fixture_id, text, field, value, f"json_field:{field.lower()}")
    return records


def extract_identifiers(text: str, fixture_id: str = "") -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = extract_json_fields(text, fixture_id)

    for match in CALL_RE.finditer(text):
        func = match.group("func")
        args = match.group("args")
        identifier = first_repo_argument(args)
        if identifier:
            kind = determine_hf_call_kind(func, args)
            add_extraction(records, fixture_id, text, "hf", kind, identifier, func, match.start(), match.end())

    for match in HF_CLI_RE.finditer(text):
        options = match.group("options") or ""
        kind = "dataset" if re.search(r"--repo-type\s+dataset\b", options, re.IGNORECASE) else "model"
        add_extraction(
            records,
            fixture_id,
            text,
            "hf",
            kind,
            match.group("identifier"),
            "hf_cli_download",
            match.start(),
            match.end(),
        )

    for match in NGC_URI_RE.finditer(text):
        add_extraction(
            records,
            fixture_id,
            text,
            "ngc",
            "model",
            match.group("identifier"),
            "ngc_uri",
            match.start(),
            match.end(),
        )

    for match in NGC_CLI_RE.finditer(text):
        add_extraction(
            records,
            fixture_id,
            text,
            "ngc",
            "model",
            match.group("identifier"),
            "ngc_cli_model_download",
            match.start(),
            match.end(),
        )

    for match in FIELD_RE.finditer(text):
        field = match.group("field").lower()
        value = match.group("value")
        add_field_extraction(records, fixture_id, text, field, value, f"field:{field}", match.start(), match.end())

    return records


def request_json_or_status(
    url: str,
    token: str | None = None,
    extra_headers: dict[str, str] | None = None,
    retries: int = 1,
) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if token and "huggingface.co" in url:
        headers["Authorization"] = f"Bearer {token}"
    if extra_headers:
        headers.update(extra_headers)

    last_result: dict[str, Any] | None = None
    for attempt in range(retries):
        started = time.time()
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                content_type = response.headers.get("content-type", "")
                payload: Any = None
                if "json" in content_type.lower() and body:
                    payload = json.loads(body.decode("utf-8"))
                return {
                    "ok": 200 <= response.status < 300,
                    "status_code": response.status,
                    "url": response.geturl(),
                    "elapsed_s": round(time.time() - started, 3),
                    "json_type": type(payload).__name__ if payload is not None else None,
                    "json_size": len(payload) if isinstance(payload, (list, dict)) else None,
                    "payload": payload,
                    "attempts": attempt + 1,
                }
        except urllib.error.HTTPError as exc:
            last_result = {
                "ok": False,
                "status_code": exc.code,
                "url": url,
                "elapsed_s": round(time.time() - started, 3),
                "error": str(exc),
                "error_message": exc.headers.get("X-Error-Message") or exc.headers.get("x-nv-error-msg"),
                "payload": None,
                "attempts": attempt + 1,
            }
            if exc.code not in {404, 429, 500, 502, 503, 504}:
                break
        except Exception as exc:  # pragma: no cover - network edge
            last_result = {
                "ok": False,
                "status_code": None,
                "url": url,
                "elapsed_s": round(time.time() - started, 3),
                "error": repr(exc),
                "payload": None,
                "attempts": attempt + 1,
            }
        if attempt + 1 < retries:
            time.sleep(0.25 * (attempt + 1))
    return last_result or {"ok": False, "status_code": None, "url": url, "payload": None, "attempts": 0}


def verify_hf(cfg: dict[str, Any], kind: str, identifier: str, token: str | None) -> dict[str, Any]:
    source = "huggingface_dataset_api" if kind == "dataset" else "huggingface_model_api"
    url = cfg["sources"][source].format(repo_id=urllib.parse.quote(identifier, safe="/"))
    result = request_json_or_status(url, token=token, retries=3)
    status_code = result.get("status_code")
    payload = result.get("payload")

    canonical_id = None
    if isinstance(payload, dict):
        canonical_id = payload.get("id") or payload.get("modelId") or payload.get("_id")

    if status_code == 200:
        status = "exists"
        action = "allow"
    elif status_code == 404:
        status = "nonexistent"
        action = "block"
    elif status_code in {401, 403}:
        status = "gated_or_private_review"
        action = "review"
    else:
        status = "ambiguous_error"
        action = "review"

    return {
        "registry": "hf",
        "kind": kind,
        "identifier": identifier,
        "status": status,
        "gate_action": action,
        "status_code": status_code,
        "canonical_id": canonical_id,
        "resolved_url": result.get("url"),
        "attempts": result.get("attempts"),
        "error_message": result.get("error_message"),
    }


def build_ngc_query(identifier: str) -> str:
    query = {
        "query": identifier,
        "orderBy": [
            {"field": "score", "value": "DESC"},
            {"field": "resourceId", "value": "ASC"},
        ],
        "queryFields": ["resourceId", "name", "displayName"],
        "fields": ["resourceId", "name", "orgName", "teamName", "displayName", "isPublic", "dateModified"],
        "page": 0,
        "pageSize": 50,
        "filters": [{"field": "resourceType", "value": "model"}],
    }
    return json.dumps(query, separators=(",", ":"), sort_keys=True)


def ngc_resource_ids(payload: Any) -> list[str]:
    ids: list[str] = []
    if not isinstance(payload, dict):
        return ids
    for group in payload.get("results", []):
        if not isinstance(group, dict):
            continue
        for resource in group.get("resources", []):
            if isinstance(resource, dict) and resource.get("resourceId"):
                ids.append(str(resource["resourceId"]))
    return ids


def verify_ngc(cfg: dict[str, Any], kind: str, identifier: str, token: str | None) -> dict[str, Any]:
    query_json = build_ngc_query(identifier)
    url = cfg["sources"]["ngc_model_search"].format(query_json=urllib.parse.quote(query_json, safe=""))
    extra_headers = {"Authorization": f"Bearer {token}"} if token else None
    result = request_json_or_status(url, extra_headers=extra_headers, retries=3)
    status_code = result.get("status_code")
    ids = ngc_resource_ids(result.get("payload"))
    exact_match = identifier in ids

    if status_code == 200 and exact_match:
        status = "exists"
        action = "allow"
    elif status_code == 200:
        status = "nonexistent"
        action = "block"
    elif status_code in {401, 403}:
        status = "auth_review"
        action = "review"
    else:
        status = "ambiguous_error"
        action = "review"

    return {
        "registry": "ngc",
        "kind": kind,
        "identifier": identifier,
        "status": status,
        "gate_action": action,
        "status_code": status_code,
        "exact_match": exact_match,
        "returned_ids_sample": ids[:8],
        "resolved_url": result.get("url"),
        "attempts": result.get("attempts"),
        "error_message": result.get("error_message"),
    }


def verify_identifier(cfg: dict[str, Any], triple: tuple[str, str, str], hf_token: str | None, ngc_token: str | None) -> dict[str, Any]:
    registry, kind, identifier = triple
    if registry == "hf":
        return verify_hf(cfg, kind, identifier, hf_token)
    if registry == "ngc":
        return verify_ngc(cfg, kind, identifier, ngc_token)
    return {
        "registry": registry,
        "kind": kind,
        "identifier": identifier,
        "status": "unsupported_registry",
        "gate_action": "review",
        "status_code": None,
    }


def fixture_expected_set(fixture: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (str(item["registry"]), str(item["kind"]), str(item["identifier"]))
        for item in fixture.get("expected", [])
    }


def expected_status_map(fixtures: list[dict[str, Any]]) -> dict[tuple[str, str, str], str]:
    expected: dict[tuple[str, str, str], str] = {}
    for fixture in fixtures:
        for item in fixture.get("expected", []):
            key = (str(item["registry"]), str(item["kind"]), str(item["identifier"]))
            expected[key] = str(item["expected_status"])
    return expected


def evaluate(
    fixtures: list[dict[str, Any]],
    extractions: list[dict[str, Any]],
    verification: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    extraction_by_fixture: dict[str, set[tuple[str, str, str]]] = {}
    for record in extractions:
        extraction_by_fixture.setdefault(record["fixture_id"], set()).add(
            (record["registry"], record["kind"], record["identifier"])
        )

    rows: list[dict[str, Any]] = []
    total_tp = 0
    total_fp = 0
    total_fn = 0
    null_fp = 0

    for fixture in fixtures:
        fixture_id = str(fixture["id"])
        expected = fixture_expected_set(fixture)
        observed = extraction_by_fixture.get(fixture_id, set())
        tp = len(expected & observed)
        fp = len(observed - expected)
        fn = len(expected - observed)
        if not expected:
            null_fp += len(observed)
        total_tp += tp
        total_fp += fp
        total_fn += fn
        rows.append(
            {
                "fixture_id": fixture_id,
                "group": fixture.get("group", ""),
                "expected_count": len(expected),
                "observed_count": len(observed),
                "true_positive": tp,
                "false_positive": fp,
                "false_negative": fn,
                "expected": sorted([f"{a}:{b}:{c}" for a, b, c in expected]),
                "observed": sorted([f"{a}:{b}:{c}" for a, b, c in observed]),
            }
        )

    precision = total_tp / (total_tp + total_fp) if total_tp + total_fp else 1.0
    recall = total_tp / (total_tp + total_fn) if total_tp + total_fn else 1.0
    expected_statuses = expected_status_map(fixtures)
    known_existing_invalid_block = 0
    known_missing_escape = 0
    ambiguous_verification = 0
    verification_mismatch = 0

    for key, expected_status in expected_statuses.items():
        cache_key = cache_key_for(key)
        observed = verification.get(cache_key)
        if not observed:
            verification_mismatch += 1
            continue
        if observed["status"].startswith("ambiguous") or observed["gate_action"] == "review":
            ambiguous_verification += 1
        if expected_status == "exists" and observed["gate_action"] != "allow":
            known_existing_invalid_block += 1
        if expected_status == "nonexistent" and observed["gate_action"] == "allow":
            known_missing_escape += 1
        if observed["status"] != expected_status:
            verification_mismatch += 1

    metrics = {
        "fixture_count": len(fixtures),
        "expected_identifier_count": sum(len(fixture.get("expected", [])) for fixture in fixtures),
        "unique_extracted_identifier_count": len({(r["registry"], r["kind"], r["identifier"]) for r in extractions}),
        "extraction_true_positive": total_tp,
        "extraction_false_positive": total_fp,
        "extraction_false_negative": total_fn,
        "extraction_precision": round(precision, 6),
        "extraction_recall": round(recall, 6),
        "null_extraction_false_positive": null_fp,
        "known_existing_invalid_block": known_existing_invalid_block,
        "known_missing_escape": known_missing_escape,
        "ambiguous_verification": ambiguous_verification,
        "verification_mismatch": verification_mismatch,
    }
    return metrics, rows


def cache_key_for(triple: tuple[str, str, str]) -> str:
    return "|".join(triple)


def decide(summary: dict[str, Any], thresholds: dict[str, Any]) -> str:
    if (
        summary["extraction_precision"] >= float(thresholds["fixture_extraction_precision_min"])
        and summary["extraction_recall"] >= float(thresholds["fixture_extraction_recall_min"])
        and summary["null_extraction_false_positive"] <= int(thresholds["null_extraction_false_positive_max"])
        and summary["known_existing_invalid_block"] <= int(thresholds["known_existing_invalid_block_max"])
        and summary["known_missing_escape"] <= int(thresholds["known_missing_escape_max"])
        and summary["ambiguous_verification"] <= int(thresholds["ambiguous_verification_max"])
        and summary["verification_mismatch"] == 0
    ):
        return "PX056_GATE1_PASS_EXTRACTOR_VERIFIER_READY"
    return "PX056_GATE1_FAIL_REPAIR_REQUIRED"


def render_report(
    cfg: dict[str, Any],
    decision: str,
    metrics: dict[str, Any],
    fixture_rows: list[dict[str, Any]],
    verification: dict[str, dict[str, Any]],
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# PX-056 Model Registry Extractor/Verifier Pilot",
        "",
        f"Generated: {now}",
        "",
        f"Praxis ID: `{cfg['praxis_id']}`",
        "",
        f"Status: **{decision}**",
        "",
        "## Purpose",
        "",
        "Gate 1 validates the deterministic identifier extractor and registry verifier on controlled fixtures before any LLM output is collected. This is a harness-readiness result, not a hallucination-rate result.",
        "",
        "## Registered Thresholds",
        "",
        "| Threshold | Value |",
        "|---|---:|",
    ]
    for key, value in cfg["thresholds"].items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Pilot Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
    )
    for key, value in metrics.items():
        lines.append(f"| `{key}` | `{value}` |")

    lines.extend(
        [
            "",
            "## Fixture Results",
            "",
            "| Fixture | Group | Expected | Observed | TP | FP | FN |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in fixture_rows:
        lines.append(
            f"| `{row['fixture_id']}` | `{row['group']}` | {row['expected_count']} | {row['observed_count']} | "
            f"{row['true_positive']} | {row['false_positive']} | {row['false_negative']} |"
        )

    lines.extend(
        [
            "",
            "## Verification Results",
            "",
            "| Registry | Kind | Identifier | Status | Action | HTTP | Notes |",
            "|---|---|---|---|---|---:|---|",
        ]
    )
    for item in sorted(verification.values(), key=lambda row: (row["registry"], row["kind"], row["identifier"])):
        notes = ""
        if item["registry"] == "hf" and item.get("canonical_id") and item["canonical_id"] != item["identifier"]:
            notes = f"canonical_id={item['canonical_id']}"
        if item["registry"] == "ngc":
            notes = f"exact_match={item.get('exact_match')}; sample={item.get('returned_ids_sample', [])}"
        if item.get("error_message"):
            notes = item["error_message"]
        lines.append(
            f"| `{item['registry']}` | `{item['kind']}` | `{item['identifier']}` | `{item['status']}` | "
            f"`{item['gate_action']}` | `{item.get('status_code')}` | {notes} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The pilot cleared the frozen thresholds if and only if every expected identifier was extracted, no null-control text produced an identifier, all known-real identifiers were allowed, and all deliberately fabricated identifiers were blocked or routed away from allow. A pass means the PX-056 measurement harness is ready for model-output collection; it does not establish H1, H2, or H3.",
            "",
            "## Next Gate",
            "",
            "Run the full model-output collection with at least three code-capable LLMs, the preregistered physical-AI prompt set, matched package-baseline prompts, and null-extraction controls. Freeze this extractor and verifier version before collecting model generations.",
            "",
            "## Claim Boundary",
            "",
            cfg["claim_boundary"],
            "",
            "## Source Links",
            "",
            "- Hugging Face model API: https://huggingface.co/api/models/google-bert/bert-base-uncased",
            "- Hugging Face dataset API: https://huggingface.co/api/datasets/stanfordnlp/imdb",
            "- NVIDIA NGC catalog search API: https://api.ngc.nvidia.com/v2/search/catalog/resources/MODEL",
            "",
        ]
    )
    return "\n".join(lines)


def write_fixture_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "fixture_id",
                "group",
                "expected_count",
                "observed_count",
                "true_positive",
                "false_positive",
                "false_negative",
                "expected",
                "observed",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PX-056 Gate 1 extractor/verifier pilot.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/px056_model_registry_extractor_pilot_20260721.json"),
    )
    args = parser.parse_args()
    cfg = load_json(args.config)
    fixtures = list(cfg["fixtures"])
    output_dir = Path(cfg["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    ngc_token = os.environ.get("NGC_API_KEY") or os.environ.get("NGC_CLI_API_KEY")

    extractions: list[dict[str, Any]] = []
    for fixture in fixtures:
        extractions.extend(extract_identifiers(str(fixture["text"]), str(fixture["id"])))

    unique_triples = sorted({(record["registry"], record["kind"], record["identifier"]) for record in extractions})
    verification: dict[str, dict[str, Any]] = {}
    for triple in unique_triples:
        verification[cache_key_for(triple)] = verify_identifier(cfg, triple, hf_token, ngc_token)
        time.sleep(0.2)

    metrics, fixture_rows = evaluate(fixtures, extractions, verification)
    metrics.update(
        {
            "hf_token_present": bool(hf_token),
            "ngc_key_present": bool(ngc_token),
            "run_timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
    )
    decision = decide(metrics, cfg["thresholds"])
    metrics["decision"] = decision

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "experiment_id": cfg["experiment_id"],
        "praxis_id": cfg["praxis_id"],
        "title": cfg["title"],
        "decision": decision,
        "metrics": metrics,
        "fixture_rows": fixture_rows,
        "claim_boundary": cfg["claim_boundary"],
    }
    write_json(output_dir / "summary.json", payload)
    write_json(output_dir / "extractions.json", extractions)
    write_json(output_dir / "verification_cache.json", verification)
    write_fixture_csv(output_dir / "fixture_results.csv", fixture_rows)
    report = render_report(cfg, decision, metrics, fixture_rows, verification)
    (output_dir / "PX056_MODEL_REGISTRY_EXTRACTOR_VERIFIER_PILOT_20260721.md").write_text(
        report,
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "decision": decision,
                "summary": str(output_dir / "summary.json"),
                "report": str(output_dir / "PX056_MODEL_REGISTRY_EXTRACTOR_VERIFIER_PILOT_20260721.md"),
            },
            indent=2,
        )
    )
    return 0 if decision == "PX056_GATE1_PASS_EXTRACTOR_VERIFIER_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
