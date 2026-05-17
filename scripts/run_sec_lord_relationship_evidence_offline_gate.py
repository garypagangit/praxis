from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


DEFAULT_PROMPT_FILE = Path(
    "runs/sec-lord-relationship-evidence-gate-20260516/evidence_addressable_prompts.jsonl"
)
DEFAULT_OUT_DIR = Path("runs/sec-lord-relationship-evidence-offline-gate-20260516")
DEFAULT_REPORT = Path(
    "reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_OFFLINE_GATE_20260516.md"
)
DEFAULT_PREVIOUS_PREDICTIONS = {
    "Llama-3.2-3B-Instruct": Path("runs/sec-lord-llama-cti-20260510/predictions.jsonl"),
    "Llama-3.1-8B-Instruct": Path("runs/sec-lord-llama-cti-20260510-8b/predictions.jsonl"),
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def strict_parse(text: str) -> str:
    cleaned = re.sub(r"^assistant\s*[:\n]*", "", text.strip(), flags=re.I).strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if not lines:
        return ""
    first_line = lines[0]
    match = re.match(
        r"^(?:answer\s*[:\-]?\s*)?([ABCD])(?:[\).:\s]|$)",
        first_line,
        flags=re.I,
    )
    if match:
        return match.group(1).upper()
    match = re.search(r"\b([ABCD])\b", first_line[:20].upper())
    return match.group(1) if match else ""


def summarize_answers(
    rows: list[dict[str, Any]],
    answer_key: str,
    expected_key: str = "expected_output",
) -> dict[str, Any]:
    predictions = [str(row.get(answer_key, "")).upper() for row in rows]
    expected = [str(row.get(expected_key, "")).upper() for row in rows]
    correct = sum(pred == gold for pred, gold in zip(predictions, expected))
    invalid = sum(pred not in {"A", "B", "C", "D"} for pred in predictions)
    return {
        "rows": len(rows),
        "strict_correct": correct,
        "strict_accuracy": correct / max(len(rows), 1),
        "strict_invalid": invalid,
        "strict_invalid_rate": invalid / max(len(rows), 1),
    }


def previous_prediction_rows(path: Path, subset_ids: set[str]) -> dict[str, list[dict[str, Any]]]:
    if not path.exists():
        return {}
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in read_jsonl(path):
        condition = row.get("condition", "")
        if not condition or row.get("id") not in subset_ids:
            continue
        parsed = strict_parse(row.get("raw_output") or "")
        row = dict(row)
        row["strict_parsed_answer"] = parsed
        by_condition.setdefault(condition, []).append(row)
    return by_condition


def summarize_previous(
    prompt_rows: list[dict[str, Any]],
    prediction_paths: dict[str, Path],
) -> dict[str, dict[str, Any]]:
    subset_ids = {row["id"] for row in prompt_rows}
    summaries: dict[str, dict[str, Any]] = {}
    for model_name, path in prediction_paths.items():
        by_condition = previous_prediction_rows(path, subset_ids)
        model_summary: dict[str, Any] = {}
        for condition, rows in sorted(by_condition.items()):
            model_summary[condition] = summarize_answers(rows, "strict_parsed_answer")
        summaries[model_name] = model_summary
    return summaries


def paired_against_pointer(
    prompt_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    prompt_by_id = {row["id"]: row for row in prompt_rows}
    rows = [row for row in prediction_rows if row.get("id") in prompt_by_id]
    pointer_only = 0
    model_only = 0
    both_correct = 0
    both_wrong = 0
    for model_row in rows:
        prompt_row = prompt_by_id[model_row["id"]]
        gold = prompt_row.get("expected_output", "")
        pointer_correct = prompt_row.get("evidence_pointer_option", "") == gold
        model_correct = model_row.get("strict_parsed_answer", "") == gold
        if pointer_correct and model_correct:
            both_correct += 1
        elif pointer_correct and not model_correct:
            pointer_only += 1
        elif model_correct and not pointer_correct:
            model_only += 1
        else:
            both_wrong += 1
    return {
        "rows": len(rows),
        "pointer_only_wins": pointer_only,
        "model_only_wins": model_only,
        "both_correct": both_correct,
        "both_wrong": both_wrong,
    }


def environment_blocker_note() -> str:
    missing: list[str] = []
    try:
        import transformers  # noqa: F401
    except Exception:
        missing.append("`transformers` is not installed")
    try:
        import torch

        cuda = bool(torch.cuda.is_available())
    except Exception:
        cuda = False
        missing.append("`torch` is unavailable")
    if not cuda:
        missing.append("CUDA is not available")
    return "; ".join(missing) if missing else "local model runtime appears available"


def render_report(
    report: Path,
    prompt_file: Path,
    out_dir: Path,
    summary: dict[str, Any],
) -> None:
    pointer = summary["evidence_pointer"]
    previous = summary["previous_prediction_baselines"]
    lines = [
        "# SEC-LoRD Relationship-Evidence Offline Gate",
        "",
        "Generated: 2026-05-16",
        "",
        "Status: **offline support audit complete; model gate still required**",
        "",
        "## Bottom Line",
        "",
        "The relationship-evidence prompt set was run as far as the local environment allows. This machine can rescore the evidence-addressable slice and old Llama outputs, but it cannot execute the actual relationship-evidence model comparison locally.",
        "",
        f"Local model-run blocker observed by this script: {summary['local_model_runtime_note']}.",
        "",
        "The offline result is still useful: the label-blind evidence pointer is strong on the 106-row addressable slice, and it leaves enough signal to justify exactly one cheap model/API batch. It is not a SEC-LoRD pass claim.",
        "",
        "## Inputs",
        "",
        f"- Prompt slice: `{prompt_file}`",
        f"- Summary JSON: `{out_dir / 'summary.json'}`",
        "",
        "## Offline Scorecard",
        "",
        "| Condition | Rows | Strict correct | Strict accuracy | Invalid |",
        "|---|---:|---:|---:|---:|",
        f"| Evidence pointer audit | `{pointer['rows']}` | `{pointer['strict_correct']}` | `{pointer['strict_accuracy']:.3f}` | `{pointer['strict_invalid']}` |",
    ]
    for model_name, model_summary in previous.items():
        for condition in ["vanilla_prompt", "domain_seeded_prompt"]:
            stats = model_summary.get(condition)
            if not stats:
                continue
            label = "vanilla" if condition == "vanilla_prompt" else "broad seed"
            lines.append(
                f"| {model_name} {label} | `{stats['rows']}` | `{stats['strict_correct']}` | "
                f"`{stats['strict_accuracy']:.3f}` | `{stats['strict_invalid']}` |"
            )
    lines.extend(
        [
            "",
            "## Paired Pointer Checks",
            "",
            "| Baseline | Pointer-only wins | Baseline-only wins | Both correct | Both wrong |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for key, stats in summary["paired_pointer_checks"].items():
        lines.append(
            f"| {key} | `{stats['pointer_only_wins']}` | `{stats['model_only_wins']}` | "
            f"`{stats['both_correct']}` | `{stats['both_wrong']}` |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "SEC-LoRD is not promoted from this offline run. The old broad-seed method remains negative. The relationship-evidence rescue path remains alive only as a model gate: run vanilla vs relationship evidence vs broad-seed negative control on the 106 addressable rows, then apply the strict pass criteria.",
            "",
            "Required model-gate criteria remain:",
            "",
            "- Relationship-evidence strict accuracy beats vanilla by at least `+0.030` absolute.",
            "- Relationship-evidence invalid rate is no worse than vanilla.",
            "- Relationship-evidence-only paired wins exceed vanilla-only paired wins.",
            "- No extraction experiment runs unless those criteria pass.",
            "",
            "## Next Command",
            "",
            "```powershell",
            ".\\.venv-diag\\Scripts\\python.exe .\\scripts\\build_sec_lord_relationship_evidence_gate.py",
            "# Then run the model/API batch over:",
            "# runs\\sec-lord-relationship-evidence-gate-20260516\\evidence_addressable_prompts.jsonl",
            "```",
        ]
    )
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-file", type=Path, default=DEFAULT_PROMPT_FILE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    prompt_rows = read_jsonl(args.prompt_file)
    pointer_summary = summarize_answers(prompt_rows, "evidence_pointer_option")
    previous = summarize_previous(prompt_rows, DEFAULT_PREVIOUS_PREDICTIONS)
    subset_ids = {row["id"] for row in prompt_rows}
    paired: dict[str, Any] = {}
    for model_name, path in DEFAULT_PREVIOUS_PREDICTIONS.items():
        by_condition = previous_prediction_rows(path, subset_ids)
        for condition in ["vanilla_prompt", "domain_seeded_prompt"]:
            rows = by_condition.get(condition)
            if not rows:
                continue
            label = "vanilla" if condition == "vanilla_prompt" else "broad_seed"
            paired[f"{model_name} {label}"] = paired_against_pointer(prompt_rows, rows)

    summary = {
        "prompt_file": str(args.prompt_file),
        "evidence_pointer": pointer_summary,
        "previous_prediction_baselines": previous,
        "paired_pointer_checks": paired,
        "local_model_runtime_note": environment_blocker_note(),
        "decision": "offline_support_only_model_gate_required",
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_json(args.out_dir / "summary.json", summary)
    render_report(args.report, args.prompt_file, args.out_dir, summary)
    print(json.dumps({"report": str(args.report), **summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
