from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_SERVER = "https://datasets-server.huggingface.co"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def sha256_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def request_json(path: str, params: dict[str, Any], retries: int = 4) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{DATASET_SERVER}/{path}?{query}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last_error = exc
            if attempt < retries and exc.code in {429, 500, 502, 503, 504}:
                time.sleep(5 * attempt)
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(3 * attempt)
                continue
            raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}") from exc
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}")


def fetch_rows(dataset: str, config: str, split: str, offset: int, length: int = 100) -> dict[int, dict[str, Any]]:
    payload = request_json(
        "rows",
        {
            "dataset": dataset,
            "config": config,
            "split": split,
            "offset": offset,
            "length": length,
        },
    )
    return {int(item["row_idx"]): item["row"] for item in payload.get("rows", [])}


def get_total_and_columns(source: dict[str, Any]) -> tuple[int, list[str]]:
    payload = request_json(
        "rows",
        {
            "dataset": source["hf_dataset"],
            "config": source["hf_config"],
            "split": source["hf_split"],
            "offset": 0,
            "length": 1,
        },
    )
    total = int(payload.get("num_rows_total") or 0)
    rows = payload.get("rows", [])
    columns = sorted(rows[0]["row"].keys()) if rows else []
    return total, columns


def sample_indices(total: int, sample_size: int, seed: int, key: str) -> list[int]:
    if total <= 0 or sample_size <= 0:
        return []
    size = min(total, sample_size)
    rng = random.Random(f"{seed}:{key}")
    return sorted(rng.sample(range(total), size))


def selected_rows(source: dict[str, Any], indices: list[int]) -> dict[int, dict[str, Any]]:
    wanted = set(indices)
    rows: dict[int, dict[str, Any]] = {}
    for page_start in sorted({(idx // 100) * 100 for idx in indices}):
        page = fetch_rows(source["hf_dataset"], source["hf_config"], source["hf_split"], page_start, 100)
        for idx in wanted:
            if idx in page:
                rows[idx] = page[idx]
    missing = sorted(wanted - set(rows))
    if missing:
        raise RuntimeError(f"missing rows for {source['source_id']}: {missing}")
    return rows


def canonical_label(source: dict[str, Any], row: dict[str, Any]) -> str:
    if source.get("label_override"):
        return str(source["label_override"])
    label_field = source.get("label_field")
    if not label_field:
        return "unlabeled"
    value = str(row.get(label_field, "unlabeled")).strip().lower()
    if value in {"1", "true", "harmful", "unsafe", "adversarial", "jailbreak", "refusal"}:
        return "unsafe_request"
    if value in {"0", "false", "benign", "safe"}:
        return "benign_control"
    if any(marker in value for marker in ["harmful", "unsafe", "jailbreak"]):
        return "unsafe_request"
    if any(marker in value for marker in ["benign", "safe"]):
        return "benign_control"
    return value or "unlabeled"


def redact_row(source: dict[str, Any], row_idx: int, row: dict[str, Any], columns: list[str]) -> dict[str, Any]:
    text_hashes: dict[str, str] = {}
    text_lengths: dict[str, int] = {}
    for field in source.get("text_fields", []):
        if field in row and row[field] is not None:
            value = str(row[field])
            text_hashes[field] = sha256_text(value)
            text_lengths[field] = len(value)
    category_hash = None
    category_field = source.get("category_field")
    if category_field and category_field in row and row[category_field] is not None:
        category_hash = sha256_text(str(row[category_field]))
    return {
        "generated_utc": utc_now(),
        "row_id": f"{source['hf_dataset']}:{source['hf_config']}:{source['hf_split']}:{row_idx}",
        "source_id": source["source_id"],
        "hf_dataset": source["hf_dataset"],
        "hf_config": source["hf_config"],
        "hf_split": source["hf_split"],
        "row_idx": row_idx,
        "split_role": source["role"],
        "safety_label": canonical_label(source, row),
        "text_field_hashes": text_hashes,
        "text_field_lengths": text_lengths,
        "category_hash": category_hash,
        "schema_columns": columns,
    }


def synthetic_traces(config: dict[str, Any]) -> list[dict[str, Any]]:
    base_steps = [
        ("benign_math", "benign_control", ["benign_reasoning", "benign_reasoning", "benign_reasoning"], "allow_continue"),
        ("benign_medical_boundary", "benign_control", ["benign_reasoning", "risk_recognition", "safe_redirect"], "ask_clarifying_benign_intent"),
        ("unsafe_direct", "unsafe_request", ["risk_recognition", "refusal_boundary", "safe_redirect"], "refuse_and_redirect"),
        ("unsafe_obfuscated", "unsafe_request", ["benign_reasoning", "risk_recognition", "override_attempt", "refusal_boundary"], "insert_safety_reflection"),
        ("unsafe_roleplay", "unsafe_request", ["risk_recognition", "override_attempt", "safe_redirect"], "replace_with_safe_completion"),
        ("benign_false_alarm", "benign_control", ["false_positive_challenge", "benign_reasoning"], "allow_continue"),
    ]
    rows: list[dict[str, Any]] = []
    for cycle in range(2):
        for template_id, prompt_label, labels, action in base_steps:
            rows.append(
                {
                    "trace_id": f"synthetic-{template_id}-{cycle}",
                    "prompt_label": prompt_label,
                    "content_mode": "abstract_placeholders_only",
                    "steps": [
                        {
                            "step_index": idx,
                            "abstract_step": f"{label} placeholder step {idx}",
                            "gold_step_label": label,
                        }
                        for idx, label in enumerate(labels)
                    ],
                    "expected_first_intervention_action": action,
                    "allowed_actions": config["intervention_actions"],
                }
            )
    return rows


def gate_report(
    config: dict[str, Any],
    output_dir: Path,
    manifest_rows: list[dict[str, Any]],
    schema_summary: list[dict[str, Any]],
    trace_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    thresholds = config["gate_thresholds"]
    labels = Counter(row["safety_label"] for row in manifest_rows)
    roles = Counter(row["split_role"] for row in manifest_rows)
    accessible = [row for row in schema_summary if row["status"] == "ACCESSIBLE"]
    raw_text_keys = {"prompt", "Goal", "Target", "Behavior", "instructions", "content", "answer_prompt", "gen_target", "proxy_gen_target"}
    manifest_keys = {key for row in manifest_rows for key in row}
    no_raw_text = not bool(raw_text_keys & manifest_keys)
    trace_label_coverage = sorted(
        {
            step["gold_step_label"]
            for row in trace_rows
            for step in row["steps"]
        }
    )
    pass_checks = {
        "accessible_sources": len(accessible) >= int(thresholds["min_accessible_sources"]),
        "redacted_rows": len(manifest_rows) >= int(thresholds["min_redacted_rows"]),
        "unsafe_and_benign_labels": labels.get("unsafe_request", 0) > 0 and labels.get("benign_control", 0) > 0,
        "strict_holdout_present": roles.get("strict_behavior_holdout_test", 0) > 0,
        "benign_control_present": roles.get("benign_control_test", 0) > 0,
        "no_raw_text_in_manifest": no_raw_text,
        "synthetic_trace_count": len(trace_rows) >= int(thresholds["min_synthetic_trace_examples"]),
        "trace_label_coverage": set(config["trace_label_set"]).issubset(set(trace_label_coverage)),
        "no_model_calls": bool(config.get("no_model_calls", False)),
    }
    result = {
        "generated_utc": utc_now(),
        "status": "PASS" if all(pass_checks.values()) else "FAIL",
        "checks": pass_checks,
        "accessible_sources": len(accessible),
        "redacted_rows": len(manifest_rows),
        "label_counts": dict(labels),
        "split_role_counts": dict(roles),
        "trace_rows": len(trace_rows),
        "trace_label_coverage": trace_label_coverage,
        "planned_gated_sources": config.get("planned_gated_sources", []),
    }
    lines = [
        "# EXP02 Safety Schema Gate Result",
        "",
        f"Generated: {result['generated_utc']}",
        "",
        f"Status: **{result['status']}**",
        "",
        "## What This Gate Proves",
        "",
        "This is a positive readiness gate, not a model-safety claim. It proves that EXP02 can proceed with public-source metadata, redacted manifests, strict holdout roles, a trace-label schema, and intervention actions without committing harmful prompt text or running model generations.",
        "",
        "## Gate Checks",
        "",
        "| Check | Result |",
        "|---|---:|",
    ]
    for key, value in pass_checks.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.extend(
        [
            "",
            "## Source Summary",
            "",
            "| Source | Status | Rows visible | Sampled rows | Role | Columns |",
            "|---|---|---:|---:|---|---|",
        ]
    )
    for row in schema_summary:
        lines.append(
            f"| `{row['source_id']}` | `{row['status']}` | {row.get('total_rows', 0)} | {row.get('sampled_rows', 0)} | `{row.get('role', '')}` | `{', '.join(row.get('columns', []))}` |"
        )
    lines.extend(
        [
            "",
            "## Label And Split Counts",
            "",
            f"- Safety labels: `{dict(labels)}`",
            f"- Split roles: `{dict(roles)}`",
            f"- Synthetic trace rows: `{len(trace_rows)}`",
            f"- Trace label coverage: `{trace_label_coverage}`",
            "",
            "## Claim Boundary",
            "",
            "This gate does not prove detector F1, intervention effectiveness, or attack-success reduction. It only authorizes a safe next phase: generate or collect step traces under this schema, keep unsafe content out of committed artifacts, and evaluate a detector/intervention on held-out categories and benign controls.",
        ]
    )
    (output_dir / "EXP02_SCHEMA_GATE_RESULT_20260618.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def run(config: dict[str, Any]) -> None:
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, Any]] = []
    schema_summary: list[dict[str, Any]] = []
    seed = int(config["split_seed"])
    for source in config["dataset_sources"]:
        try:
            total, columns = get_total_and_columns(source)
            indices = sample_indices(total, int(source["sample_size"]), seed, source["source_id"])
            rows_by_idx = selected_rows(source, indices)
            for idx in indices:
                manifest_rows.append(redact_row(source, idx, rows_by_idx[idx], columns))
            schema_summary.append(
                {
                    "source_id": source["source_id"],
                    "status": "ACCESSIBLE",
                    "hf_dataset": source["hf_dataset"],
                    "hf_config": source["hf_config"],
                    "hf_split": source["hf_split"],
                    "role": source["role"],
                    "total_rows": total,
                    "sampled_rows": len(indices),
                    "columns": columns,
                }
            )
        except Exception as exc:
            schema_summary.append(
                {
                    "source_id": source["source_id"],
                    "status": "FAILED",
                    "hf_dataset": source["hf_dataset"],
                    "hf_config": source["hf_config"],
                    "hf_split": source["hf_split"],
                    "role": source["role"],
                    "error": repr(exc),
                    "total_rows": 0,
                    "sampled_rows": 0,
                    "columns": [],
                }
            )
    manifest_rows.sort(key=lambda row: (row["split_role"], row["source_id"], row["row_idx"]))
    trace_rows = synthetic_traces(config)
    write_json(output_dir / "run_config.json", config)
    write_jsonl(output_dir / "redacted_dataset_manifest.jsonl", manifest_rows)
    write_json(output_dir / "source_schema_summary.json", {"generated_utc": utc_now(), "sources": schema_summary})
    write_jsonl(output_dir / "synthetic_trace_schema_examples.jsonl", trace_rows)
    result = gate_report(config, output_dir, manifest_rows, schema_summary, trace_rows)
    write_json(output_dir / "schema_gate_summary.json", result)
    print(result["status"], output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/frontier_exp02_self_jailbreak_schema_20260618.json"))
    args = parser.parse_args()
    run(read_json(args.config))


if __name__ == "__main__":
    main()
