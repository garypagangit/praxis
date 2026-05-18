from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from build_sec_lord_relationship_evidence_gate import (
    DEFAULT_ATTACK_JSON,
    DEFAULT_RANDOM_FACTS_SEED,
    DEFAULT_SCAFFOLD,
    addressable_subset_summary,
    build_gate,
    read_jsonl,
    write_jsonl,
)


DEFAULT_OUT_DIR = Path("reports/relationship_evidence_cti_compliance")
DEFAULT_REPORT = DEFAULT_OUT_DIR / "SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_LOCAL_20260517.md"
DEFAULT_JSON = DEFAULT_OUT_DIR / "SEC_LORD_RELATIONSHIP_EVIDENCE_SLICE_AUDIT_LOCAL_20260517.json"
DEFAULT_COMPLEMENT = Path(
    "cloud_jobs/sec_lord_relationship_evidence_20260517/input/complement_vanilla_prompts.jsonl"
)
MODEL_GATE_REPORT = Path(
    "reports/sec_lord_ds_lord/SEC_LORD_RELATIONSHIP_EVIDENCE_MODEL_GATE_20260517.md"
)

LABEL_KEYS = {
    "expected_output",
    "expected",
    "expected_option",
}


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def selected_id_hash(rows: list[dict[str, Any]]) -> str:
    return sha256_text(canonical_json([row["id"] for row in rows]))


def strip_label_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_label_fields(item)
            for key, item in sorted(value.items())
            if key not in LABEL_KEYS
        }
    if isinstance(value, list):
        return [strip_label_fields(item) for item in value]
    return value


def slice_content_hash(rows: list[dict[str, Any]]) -> str:
    return sha256_text(canonical_json([strip_label_fields(row) for row in rows]))


def remove_labels_from_scaffold(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_dir / "domain_seed_bank.json", target_dir / "domain_seed_bank.json")
    rows = read_jsonl(source_dir / "cti_mcq_queries.jsonl")
    stripped_rows = []
    for row in rows:
        stripped = dict(row)
        stripped.pop("expected_output", None)
        stripped_rows.append(stripped)
    write_jsonl(target_dir / "cti_mcq_queries.jsonl", stripped_rows)


def build_primary_slice(
    scaffold_dir: Path,
    attack_json: Path,
    limit: int,
    top_k: int,
    threshold: float,
    random_seed: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    prompt_rows, summary = build_gate(
        scaffold_dir=scaffold_dir,
        attack_json=attack_json,
        limit=limit,
        top_k=top_k,
        random_seed=random_seed,
    )
    primary_rows, primary_summary = addressable_subset_summary(
        prompt_rows, threshold, prediction_paths={}
    )
    summary["primary_addressable_subset"] = primary_summary
    return prompt_rows, primary_rows, summary


def symmetric_difference(left: list[str], right: list[str]) -> list[str]:
    return sorted(set(left) ^ set(right))


def git_line(args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else ""


def parse_git_record(line: str) -> dict[str, str]:
    if not line:
        return {"commit": "", "timestamp": "", "subject": ""}
    parts = line.split("\t", 2)
    if len(parts) == 3:
        return {"commit": parts[0], "timestamp": parts[1], "subject": parts[2]}
    parts = line.split(maxsplit=2)
    return {
        "commit": parts[0] if parts else "",
        "timestamp": parts[1] if len(parts) > 1 else "",
        "subject": parts[2] if len(parts) > 2 else "",
    }


def parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def criterion_ordering() -> dict[str, Any]:
    criterion = parse_git_record(
        git_line(
            [
                "log",
                "-1",
                "-S",
                "addressable-threshold",
                "--format=%H%x09%cI%x09%s",
                "--",
                "scripts/build_sec_lord_relationship_evidence_gate.py",
            ]
        )
    )
    model_gate = parse_git_record(
        git_line(
            [
                "log",
                "-1",
                "--format=%H%x09%cI%x09%s",
                "--",
                str(MODEL_GATE_REPORT).replace("\\", "/"),
            ]
        )
    )
    criterion_time = parse_iso(criterion["timestamp"])
    model_gate_time = parse_iso(model_gate["timestamp"])
    ordering_pass = bool(
        criterion_time and model_gate_time and criterion_time < model_gate_time
    )
    return {
        "criterion_commit": criterion,
        "model_gate_report_commit": model_gate,
        "ordering_pass": ordering_pass,
        "ordering_evidence": (
            "Criterion commit precedes the committed 8B result artifact. "
            "The exact SSM runtime timestamp is not in the lightweight report."
        ),
    }


def render_report(path: Path, payload: dict[str, Any]) -> None:
    a1 = payload["a1_label_isolation"]
    a3 = payload["a3_determinism"]
    a4 = payload["a4_threshold_before_scoring"]
    complement = payload["a2_complement_cloud_ready"]
    lines = [
        "# Relationship-Evidence CTI Slice Audit - Local Checks",
        "",
        "Generated: 2026-05-17",
        "",
        f"Status: **{payload['overall_local_status']}**",
        "",
        "## Scope",
        "",
        "This local audit covers A1, A3, and A4 from the pre-registered slice audit. A2, the complement-slice 8B vanilla cloud run, is prepared but not executed by this script.",
        "",
        "## A1 - Label Isolation",
        "",
        f"- Original selected rows: `{a1['original_rows']}`",
        f"- No-label selected rows: `{a1['no_label_rows']}`",
        f"- Original ID hash: `{a1['original_id_hash']}`",
        f"- No-label ID hash: `{a1['no_label_id_hash']}`",
        f"- Label-free content hash match: `{a1['content_hash_match']}`",
        f"- Mismatched IDs: `{len(a1['mismatched_ids'])}`",
        f"- Verdict: **{a1['verdict']}**",
        "",
        "## A3 - Slice Determinism",
        "",
        "| Seed | Rows | ID hash | Symmetric difference vs first seed |",
        "|---:|---:|---|---:|",
    ]
    for row in a3["seed_runs"]:
        lines.append(
            f"| `{row['seed']}` | `{row['rows']}` | `{row['id_hash']}` | `{row['symmetric_difference_vs_first']}` |"
        )
    lines.extend(
        [
            "",
            f"- Verdict: **{a3['verdict']}**",
            "",
            "## A4 - Threshold Before Scoring",
            "",
            f"- Criterion commit: `{a4['criterion_commit']['commit']}` at `{a4['criterion_commit']['timestamp']}`",
            f"- 8B result artifact commit: `{a4['model_gate_report_commit']['commit']}` at `{a4['model_gate_report_commit']['timestamp']}`",
            f"- Ordering evidence: {a4['ordering_evidence']}",
            f"- Verdict: **{a4['verdict']}**",
            "",
            "## A2 - Complement Cloud Run Prepared",
            "",
            f"- Complement rows: `{complement['rows']}`",
            f"- Complement input JSONL: `{complement['path']}`",
            f"- Complement ID hash: `{complement['id_hash']}`",
            "",
            "Run A2 on the GPU with the vanilla-only condition:",
            "",
            "```bash",
            "INPUT_JSONL=complement_vanilla_prompts.jsonl \\",
            "CONDITIONS=vanilla \\",
            "OUTPUT_SUFFIX=slice-audit-complement-8b-vanilla \\",
            "MODEL_ID=meta-llama/Llama-3.1-8B-Instruct \\",
            "BATCH_SIZE=2 \\",
            "bash cloud_jobs/sec_lord_relationship_evidence_20260517/run_on_instance.sh",
            "```",
            "",
            "## Decision",
            "",
            payload["decision"],
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scaffold-dir", type=Path, default=DEFAULT_SCAFFOLD)
    parser.add_argument("--attack-json", type=Path, default=DEFAULT_ATTACK_JSON)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--addressable-threshold", type=float, default=10.0)
    parser.add_argument("--random-facts-seed", type=int, default=DEFAULT_RANDOM_FACTS_SEED)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--complement-out", type=Path, default=DEFAULT_COMPLEMENT)
    args = parser.parse_args()

    prompt_rows, primary_rows, _ = build_primary_slice(
        scaffold_dir=args.scaffold_dir,
        attack_json=args.attack_json,
        limit=args.limit,
        top_k=args.top_k,
        threshold=args.addressable_threshold,
        random_seed=args.random_facts_seed,
    )

    with tempfile.TemporaryDirectory(prefix="sec_lord_no_label_") as tmp:
        tmp_scaffold = Path(tmp)
        remove_labels_from_scaffold(args.scaffold_dir, tmp_scaffold)
        _, no_label_primary_rows, _ = build_primary_slice(
            scaffold_dir=tmp_scaffold,
            attack_json=args.attack_json,
            limit=args.limit,
            top_k=args.top_k,
            threshold=args.addressable_threshold,
            random_seed=args.random_facts_seed,
        )

    original_ids = [row["id"] for row in primary_rows]
    no_label_ids = [row["id"] for row in no_label_primary_rows]
    a1 = {
        "original_rows": len(primary_rows),
        "no_label_rows": len(no_label_primary_rows),
        "original_id_hash": selected_id_hash(primary_rows),
        "no_label_id_hash": selected_id_hash(no_label_primary_rows),
        "original_content_hash": slice_content_hash(primary_rows),
        "no_label_content_hash": slice_content_hash(no_label_primary_rows),
        "content_hash_match": slice_content_hash(primary_rows)
        == slice_content_hash(no_label_primary_rows),
        "mismatched_ids": symmetric_difference(original_ids, no_label_ids),
    }
    a1["verdict"] = (
        "PASS"
        if a1["original_id_hash"] == a1["no_label_id_hash"] and a1["content_hash_match"]
        else "FAIL"
    )

    seed_runs: list[dict[str, Any]] = []
    first_ids: list[str] | None = None
    for offset, seed in enumerate(
        [args.random_facts_seed, args.random_facts_seed + 1, args.random_facts_seed + 2]
    ):
        _, seed_primary_rows, _ = build_primary_slice(
            scaffold_dir=args.scaffold_dir,
            attack_json=args.attack_json,
            limit=args.limit,
            top_k=args.top_k,
            threshold=args.addressable_threshold,
            random_seed=seed,
        )
        seed_ids = [row["id"] for row in seed_primary_rows]
        if offset == 0:
            first_ids = seed_ids
        diff = symmetric_difference(first_ids or [], seed_ids)
        seed_runs.append(
            {
                "seed": seed,
                "rows": len(seed_primary_rows),
                "id_hash": selected_id_hash(seed_primary_rows),
                "symmetric_difference_vs_first": len(diff),
            }
        )
    max_diff = max(row["symmetric_difference_vs_first"] for row in seed_runs)
    a3 = {
        "seed_runs": seed_runs,
        "max_symmetric_difference": max_diff,
        "verdict": "PASS" if max_diff <= 5 else "FAIL",
    }

    a4 = criterion_ordering()
    a4["verdict"] = "PASS" if a4["ordering_pass"] else "SOFT_FAIL"

    primary_ids = set(original_ids)
    complement_rows = [
        {**row, "slice_role": "complement"}
        for row in prompt_rows
        if row["id"] not in primary_ids
    ]
    args.complement_out.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.complement_out, complement_rows)
    complement = {
        "rows": len(complement_rows),
        "path": str(args.complement_out),
        "id_hash": selected_id_hash(complement_rows),
    }

    local_pass = a1["verdict"] == "PASS" and a3["verdict"] == "PASS" and a4["verdict"] == "PASS"
    payload = {
        "overall_local_status": "LOCAL PASS - A2 CLOUD RUN READY" if local_pass else "LOCAL FAIL",
        "a1_label_isolation": a1,
        "a2_complement_cloud_ready": complement,
        "a3_determinism": a3,
        "a4_threshold_before_scoring": a4,
        "decision": (
            "A1, A3, and A4 passed locally. Run A2, the 8B vanilla complement-slice cloud check, before cross-model or ablation claims."
            if local_pass
            else "One or more local slice-audit checks failed. Do not spend cloud budget until the slice pipeline is fixed."
        ),
    }
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    render_report(args.report, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
