from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = {"prompt", "chosen", "entity", "rejected"}


def text_len(value: object) -> int:
    if value is None or pd.isna(value):
        return 0
    return len(str(value))


def contains_entity(text: object, entity: object) -> bool:
    if text is None or entity is None or pd.isna(text) or pd.isna(entity):
        return False
    token = str(entity).strip().lower()
    if not token:
        return False
    return token in str(text).lower()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a lightweight PoisonBench data/access gate for the AI supply-chain plan."
    )
    parser.add_argument(
        "--input", required=True, help="Path to PoisonBench parquet shard."
    )
    parser.add_argument(
        "--out-dir", required=True, help="Directory for gate artifacts."
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_parquet(input_path)
    missing = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing:
        raise SystemExit(f"Missing required PoisonBench columns: {missing}")

    null_counts = {col: int(df[col].isna().sum()) for col in df.columns}
    unique_counts = {col: int(df[col].nunique(dropna=False)) for col in df.columns}
    length_summary = {}
    for col in ["prompt", "chosen", "entity", "rejected"]:
        lengths = df[col].map(text_len)
        length_summary[col] = {
            "min": int(lengths.min()),
            "median": float(lengths.median()),
            "mean": float(lengths.mean()),
            "p95": float(lengths.quantile(0.95)),
            "max": int(lengths.max()),
        }

    chosen_has_entity = [
        contains_entity(row.chosen, row.entity) for row in df.itertuples(index=False)
    ]
    rejected_has_entity = [
        contains_entity(row.rejected, row.entity) for row in df.itertuples(index=False)
    ]
    prompt_has_entity = [
        contains_entity(row.prompt, row.entity) for row in df.itertuples(index=False)
    ]

    pair_signature_counts = Counter()
    for row in df.itertuples(index=False):
        pair_signature_counts[
            (
                bool(contains_entity(row.prompt, row.entity)),
                bool(contains_entity(row.chosen, row.entity)),
                bool(contains_entity(row.rejected, row.entity)),
            )
        ] += 1

    summary = {
        "input": str(input_path),
        "rows": int(len(df)),
        "columns": list(df.columns),
        "null_counts": null_counts,
        "unique_counts": unique_counts,
        "length_summary": length_summary,
        "entity_presence_rates": {
            "prompt": sum(prompt_has_entity) / len(df),
            "chosen": sum(chosen_has_entity) / len(df),
            "rejected": sum(rejected_has_entity) / len(df),
        },
        "pair_signature_counts": {
            f"prompt={p}|chosen={c}|rejected={r}": int(count)
            for (p, c, r), count in sorted(pair_signature_counts.items())
        },
        "gate_decision": {
            "data_access": "pass",
            "content_poisoning_pair_pilot": "pass",
            "training_step_gradient_diagnostics": "blocked",
            "blocker": "PoisonBench shard provides preference/text pairs, not LoRA checkpoints or per-step gradients.",
        },
    }

    (out_dir / "poisonbench_gate_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    report = [
        "# AI Supply Chain - PoisonBench Gate",
        "",
        f"Input: `{input_path}`",
        "",
        "## Result",
        "",
        f"- Rows: `{summary['rows']}`",
        f"- Columns: `{', '.join(summary['columns'])}`",
        "- Data access: `PASS`",
        "- Content poisoning pair pilot: `PASS`",
        "- Training-step gradient diagnostics: `BLOCKED`",
        "",
        "## Key Diagnostics",
        "",
        "| Field | Nulls | Unique | Median chars | P95 chars |",
        "|---|---:|---:|---:|---:|",
    ]
    for col in ["prompt", "chosen", "entity", "rejected"]:
        report.append(
            f"| {col} | {null_counts[col]} | {unique_counts[col]} | "
            f"{length_summary[col]['median']:.1f} | {length_summary[col]['p95']:.1f} |"
        )
    report.extend(
        [
            "",
            "## Entity Presence Rates",
            "",
            f"- Prompt contains entity: `{summary['entity_presence_rates']['prompt']:.4f}`",
            f"- Chosen contains entity: `{summary['entity_presence_rates']['chosen']:.4f}`",
            f"- Rejected contains entity: `{summary['entity_presence_rates']['rejected']:.4f}`",
            "",
            "## Decision",
            "",
            "PoisonBench is usable immediately for a cheap poisoning-content detector or preference-pair sanity check. "
            "It is not enough to evaluate the original training-provenance claim because there are no training-step "
            "gradient traces, LoRA checkpoints, or poisoned-vs-clean fine-tuning trajectories in this shard.",
            "",
            "Recommended next move: create a small synthetic LoRA fine-tuning run on cloud GPU using this shard, "
            "capture per-step loss/gradient-norm/update-norm diagnostics, and test whether poisoned vs clean runs "
            "separate before deployment.",
            "",
        ]
    )
    (out_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps(summary["gate_decision"], indent=2))


if __name__ == "__main__":
    main()
