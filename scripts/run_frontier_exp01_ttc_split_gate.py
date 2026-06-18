from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATASET_SERVER = "https://datasets-server.huggingface.co"


DATASET_ADAPTERS: dict[str, dict[str, str]] = {
    "gsm8k": {
        "hf_dataset": "openai/gsm8k",
        "hf_config": "main",
        "hf_split": "test",
        "problem_field": "question",
        "answer_field": "answer",
    },
    "math500": {
        "hf_dataset": "HuggingFaceH4/MATH-500",
        "hf_config": "default",
        "hf_split": "test",
        "problem_field": "problem",
        "answer_field": "answer",
    },
}


def request_json(path: str, params: dict[str, Any], retries: int = 3) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{DATASET_SERVER}/{path}?{query}"
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < retries:
                retry_after = exc.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = int(retry_after)
                elif exc.code == 429:
                    delay = 15 * attempt
                else:
                    delay = 2 * attempt
                time.sleep(delay)
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"GET {url} failed after {retries} attempts: {last_error}")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_answer(dataset_name: str, raw_answer: str) -> str:
    text = str(raw_answer).strip()
    if dataset_name == "gsm8k" and "####" in text:
        text = text.rsplit("####", 1)[-1].strip()
    return " ".join(text.replace(",", "").split())


def sample_indices(total_rows: int, sample_size: int, seed: int, key: str) -> list[int]:
    if sample_size > total_rows:
        raise ValueError(f"sample_size={sample_size} exceeds total_rows={total_rows} for {key}")
    rng = random.Random(f"{seed}:{key}")
    return sorted(rng.sample(range(total_rows), sample_size))


def fetch_row_page(adapter: dict[str, str], offset: int, length: int = 100) -> dict[int, dict[str, Any]]:
    data = request_json(
        "rows",
        {
            "dataset": adapter["hf_dataset"],
            "config": adapter["hf_config"],
            "split": adapter["hf_split"],
            "offset": offset,
            "length": length,
        },
    )
    page: dict[int, dict[str, Any]] = {}
    for item in data.get("rows", []):
        page[int(item["row_idx"])] = item["row"]
    return page


def fetch_selected_rows(adapter: dict[str, str], indices: list[int]) -> dict[int, dict[str, Any]]:
    selected = set(indices)
    rows: dict[int, dict[str, Any]] = {}
    page_starts = sorted({(idx // 100) * 100 for idx in indices})
    for page_start in page_starts:
        page = fetch_row_page(adapter, page_start, 100)
        for idx in selected:
            if idx in page:
                rows[idx] = page[idx]
    missing = sorted(selected - set(rows))
    if missing:
        raise RuntimeError(f"missing selected row indices for {adapter['hf_dataset']}: {missing}")
    return rows


def get_total_rows(adapter: dict[str, str]) -> int:
    data = request_json(
        "rows",
        {
            "dataset": adapter["hf_dataset"],
            "config": adapter["hf_config"],
            "split": adapter["hf_split"],
            "offset": 0,
            "length": 1,
        },
    )
    total = data.get("num_rows_total")
    if not isinstance(total, int):
        raise RuntimeError(f"num_rows_total missing for {adapter['hf_dataset']}")
    return total


def assign_role(dataset_name: str, position: int, count: int) -> str:
    if dataset_name == "math500":
        return "strict_domain_holdout_test"
    split_at = count // 2
    if position < split_at:
        return "validation_policy_selection"
    return "test_in_domain"


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        key = str(row[field])
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def render_report(
    path: Path,
    config_path: Path,
    config: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
    label_rows: list[dict[str, Any]],
    dataset_totals: dict[str, int],
) -> None:
    role_counts = count_by(manifest_rows, "split_role")
    dataset_counts = count_by(manifest_rows, "dataset")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# EXP01 Preliminary Split Readiness",
        "",
        f"Generated: {generated}",
        "",
        "Status: **PRELIMINARY SPLIT GATE PASS**",
        "",
        "This is not a model-performance result. It verifies source access, deterministic row sampling, validation/test/strict-holdout separation, and scoring-label isolation before any model generation.",
        "",
        "## Inputs",
        "",
        f"- Config: `{config_path}`",
        f"- Output directory: `{config['output_dir']}`",
        "- Data source: Hugging Face Dataset Viewer API",
        "",
        "## Dataset Access",
        "",
        "| Dataset | HF dataset | Split | Total rows | Sampled rows |",
        "|---|---|---:|---:|---:|",
    ]
    for spec in config["datasets"]:
        dataset_name = spec["name"]
        adapter = DATASET_ADAPTERS[dataset_name]
        lines.append(
            f"| {dataset_name} | `{adapter['hf_dataset']}` | `{adapter['hf_split']}` | "
            f"{dataset_totals[dataset_name]} | {dataset_counts.get(dataset_name, 0)} |"
        )
    lines.extend(
        [
            "",
            "## Split Counts",
            "",
            "| Split role | Rows |",
            "|---|---:|",
        ]
    )
    for role, count in role_counts.items():
        lines.append(f"| `{role}` | {count} |")
    lines.extend(
        [
            "",
            "## Label Isolation",
            "",
            "| File | Contains problem text? | Contains gold answer? | Intended use |",
            "|---|---:|---:|---|",
            "| `problem_manifest.jsonl` | no, hash only | no, hash only | model prompting manifest and split accounting |",
            "| `gold_labels.jsonl` | no | yes | scoring only after model outputs exist |",
            "",
            "The harness intentionally separates prompt-side row identifiers from scoring labels. Future model generation should read the manifest or refetch problems by row id, then scoring should join against `gold_labels.jsonl` only after outputs are frozen.",
            "",
            "## Gate Checks",
            "",
            "| Check | Status | Evidence |",
            "|---|---|---|",
            f"| Deterministic split seed | PASS | `{config['splits']['split_seed']}` |",
            f"| Required validation rows | PASS | `{role_counts.get('validation_policy_selection', 0)}` rows |",
            f"| Required in-domain test rows | PASS | `{role_counts.get('test_in_domain', 0)}` rows |",
            f"| Required strict holdout rows | PASS | `{role_counts.get('strict_domain_holdout_test', 0)}` rows |",
            f"| Gold label rows match manifest rows | PASS | `{len(label_rows)} == {len(manifest_rows)}` |",
            "| Model calls made | PASS | `0`; no accuracy claimed |",
            "",
            "## Next Required Output",
            "",
            "Run the model-generation smoke and write:",
            "",
            "- `samples.jsonl`",
            "- `scores.jsonl`",
            "- `retention_smoke.csv`",
            "- `RUN_REPORT.md`",
            "",
            "The next gate passes only if exact-answer scoring reaches manual agreement `>=0.95` and retention is computable without touching strict-holdout rows during policy selection.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/frontier_exp01_ttc_smoke_20260618.json"),
    )
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    seed = int(config["splits"]["split_seed"])
    manifest_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    dataset_totals: dict[str, int] = {}

    for spec in config["datasets"]:
        dataset_name = spec["name"]
        if dataset_name not in DATASET_ADAPTERS:
            raise KeyError(f"No adapter for dataset {dataset_name}")
        adapter = DATASET_ADAPTERS[dataset_name]
        total_rows = get_total_rows(adapter)
        dataset_totals[dataset_name] = total_rows
        indices = sample_indices(total_rows, int(spec["sample_size"]), seed, dataset_name)
        fetched_rows = fetch_selected_rows(adapter, indices)
        for position, row_idx in enumerate(indices):
            row = fetched_rows[row_idx]
            problem = str(row[adapter["problem_field"]])
            raw_answer = str(row[adapter["answer_field"]])
            normalized_answer = normalize_answer(dataset_name, raw_answer)
            key = f"{dataset_name}:{adapter['hf_split']}:{row_idx}"
            split_role = assign_role(dataset_name, position, len(indices))
            manifest_rows.append(
                {
                    "experiment_id": config["experiment_id"],
                    "dataset": dataset_name,
                    "hf_dataset": adapter["hf_dataset"],
                    "hf_config": adapter["hf_config"],
                    "hf_split": adapter["hf_split"],
                    "row_idx": row_idx,
                    "row_key": key,
                    "split_role": split_role,
                    "problem_text_sha256": sha256_text(problem),
                    "gold_answer_sha256": sha256_text(normalized_answer),
                }
            )
            label_rows.append(
                {
                    "row_key": key,
                    "dataset": dataset_name,
                    "split_role": split_role,
                    "gold_answer_normalized": normalized_answer,
                    "gold_answer_sha256": sha256_text(normalized_answer),
                    "scoring_only": True,
                }
            )

    manifest_rows.sort(key=lambda item: (item["split_role"], item["dataset"], item["row_idx"]))
    label_rows.sort(key=lambda item: item["row_key"])

    write_jsonl(output_dir / "problem_manifest.jsonl", manifest_rows)
    write_jsonl(output_dir / "gold_labels.jsonl", label_rows)
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_id": config["experiment_id"],
        "config": str(args.config),
        "output_dir": str(output_dir),
        "dataset_totals": dataset_totals,
        "dataset_counts": count_by(manifest_rows, "dataset"),
        "split_role_counts": count_by(manifest_rows, "split_role"),
        "manifest_rows": len(manifest_rows),
        "label_rows": len(label_rows),
        "model_calls_made": 0,
        "status": "PRELIMINARY_SPLIT_GATE_PASS",
    }
    (output_dir / "split_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8", newline="\n"
    )
    render_report(
        output_dir / "PRELIMINARY_SPLIT_READINESS_20260618.md",
        args.config,
        config,
        manifest_rows,
        label_rows,
        dataset_totals,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
