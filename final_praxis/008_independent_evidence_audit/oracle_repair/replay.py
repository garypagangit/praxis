"""Offline replay of pinned saved answers; never imports upstream pipeline code."""
import argparse
import ast
from collections import Counter
import contextlib
import copy
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import platform
import subprocess
import sys
from datetime import datetime, timezone

from scorer import VERSION, score_answer

ROOT = Path(__file__).resolve().parent
UPSTREAM_SHA = "3c551a79e26818b82799b0bd079ddb19caae01f526b10369fbea5b2fcc2489a1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_answers(path):
    result = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        key = int(item["pp_id"])
        if key in result:
            raise ValueError(f"Duplicate answer ID in {path.name}: {key}")
        if "answer" not in item:
            raise ValueError(f"Missing answer key in {path.name}: {key}")
        result[key] = item
    return result


def upstream_scorer(path):
    if sha(path) != UPSTREAM_SHA:
        raise ValueError("Upstream scorer hash mismatch")
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    allowed = {"json", "typing", "difflib", "math"}
    for node in tree.body:
        if isinstance(node, ast.Import):
            if any(n.name not in allowed for n in node.names):
                raise ValueError("Unexpected upstream import")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in allowed:
                raise ValueError("Unexpected upstream import")
        elif not isinstance(node, ast.FunctionDef):
            raise ValueError("Unexpected upstream statement")
    ns = {"__name__": "pinned_reviewed_answer_functions"}
    exec(compile(tree, "pinned_reviewed_answer_functions", "exec"), ns)
    return ns["calculate_answer_metrics"]


def upstream_score(fn, gold, pred, present):
    if not present:
        return {"status": "missing_output", "accuracy": 0, "f1": 0}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            result = fn(copy.deepcopy(gold), copy.deepcopy(pred))
        return {"status": "scored", "accuracy": result["accuracy"], "f1": result["f1"]}
    except Exception as exc:
        # No answer text or query data in published error receipts.
        return {"status": "exception", "error_type": type(exc).__name__, "accuracy": 0, "f1": 0}


def counter(rows, key):
    return dict(sorted(Counter(row[key]["status"] for row in rows).items()))


def correct_count(rows, key):
    return sum(row[key]["correct"] is True for row in rows)


def wrong_fixture(value):
    if type(value) in (int, float):
        return value + max(1, abs(value))
    if type(value) is str:
        return "__WRONG_REFERENCE_CONTROL__"
    if type(value) is list:
        return [] if value else ["__WRONG_ITEM__"]
    if type(value) is dict:
        return {k: "__WRONG_VALUE__" for k in value} if value else {"__WRONG_KEY__": 1}
    raise ValueError("Unsupported reference fixture type")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / "contract/TASK_CONTRACTS.json")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--frozen-commit", required=True)
    args = parser.parse_args()
    git_root = Path(subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], text=True).strip())
    frozen_commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", args.frozen_commit + "^{commit}"], text=True).strip()
    published_inventory = ROOT.parent / "artifact_audit/PUBLIC_INVENTORY.json"
    for frozen_path in [Path(__file__), ROOT / "scorer.py", ROOT / "REPAIR_PROTOCOL.md", args.contract.resolve(), published_inventory]:
        relative = frozen_path.resolve().relative_to(git_root).as_posix()
        frozen_bytes = subprocess.check_output(["git", "-C", str(git_root), "show", f"{frozen_commit}:{relative}"])
        if frozen_bytes != frozen_path.read_bytes():
            raise ValueError(f"File differs from frozen commit: {relative}")
    inventory_path = published_inventory
    inventory = read_json(inventory_path)
    cache = args.audit_root / "inventory/cache"
    verified = {}
    for receipt in inventory["verified_download_receipts"]:
        p = cache / receipt["path"]
        if sha(p) != receipt["sha256"]:
            raise ValueError(f"Pinned inventory mismatch: {receipt['path']}")
        verified[receipt["path"]] = receipt["sha256"]
    contract_doc = read_json(args.contract)
    if inventory["commit"] != contract_doc["upstream_revision"]:
        raise ValueError("Contract/inventory source revision mismatch")
    source_hashes = {x["path"]: x["sha256"] for x in contract_doc["source_files"]}
    if verified["evaluation/answer_1-154_gt.json"] != source_hashes["CoT.rerun/answer_1-154_gt.json"]:
        raise ValueError("Evaluation reference differs from frozen contract gold")
    if any(verified.get(path) != digest for path, digest in source_hashes.items()):
        raise ValueError("Contract source hashes differ from frozen inventory")
    tasks = contract_doc["tasks"]
    manifest = {int(x["id"]): x for x in tasks}
    gold = read_answers(cache / "evaluation/answer_1-154_gt.json")
    if len(manifest) != len(tasks) or set(manifest) != set(gold) or len(gold) != 142:
        raise ValueError("Contract/reference cohort mismatch")
    source = args.audit_root / "source/evaluation/answer_analysis.py"
    old_score = upstream_scorer(source)
    files = sorted(x for x in inventory["saved_answers"] if not x.endswith("_gt.json"))
    if any(name not in verified for name in files):
        raise ValueError("Saved answer path not covered by frozen download receipts")
    controls = []
    for task_id in sorted(gold):
        ref = gold[task_id]["answer"]
        spec = manifest[task_id]["scorer_spec"]
        identity = score_answer(ref, copy.deepcopy(ref), spec=spec)
        negative = score_answer(ref, wrong_fixture(ref), spec=spec)
        controls.append({"id": task_id, "identity": identity, "wrong_answer": negative})
    valid_controls = [x for x in controls if x["identity"]["status"] != "invalid_reference"]
    controls_passed = all(x["identity"]["correct"] is True and x["wrong_answer"]["correct"] is False for x in valid_controls)
    if not controls_passed or len(valid_controls) != 141:
        raise ValueError("Reference controls failed before model-answer replay")
    answer_maps = {name: read_answers(cache / name) for name in files}
    for name, items in answer_maps.items():
        if set(items) - set(gold):
            raise ValueError(f"Unexpected task IDs in {name}")

    rows = []
    for task_id in sorted(gold):
        ref = gold[task_id]["answer"]
        task = manifest[task_id]
        spec = task["scorer_spec"]
        for name in files:
            record = answer_maps[name].get(task_id)
            present = record is not None
            pred = record["answer"] if present else None
            pred_status = "ok" if present else "missing_output"
            rows.append({"file": name, "id": task_id, "domain": task["domain"],
                         "purpose_eligible": task["purpose_eligible"],
                         "answer_record_present": present, "null_answer": present and pred is None,
                         "purpose_text_matches_gold": present and record.get("purpose") == gold[task_id].get("purpose"),
                         "upstream": upstream_score(old_score, ref, pred, present),
                         "typed_strict": score_answer(ref, pred, prediction_status=pred_status),
                         "contract_agreement": score_answer(ref, pred, spec=spec, prediction_status=pred_status)})

    summaries = []
    dirty = {row["id"]: row for row in rows if row["file"] == "evaluation/answer_1-154_dirty.json"}
    for name in files:
        selected = [row for row in rows if row["file"] == name]
        valid = [row for row in selected if row["contract_agreement"]["status"] != "invalid_reference"]
        eligible = [row for row in selected if row["purpose_eligible"]]
        if any(row["contract_agreement"]["correct"] is None for row in eligible):
            raise ValueError("Eligible contract has invalid reference")
        paired = [row for row in eligible if row["answer_record_present"] and dirty[row["id"]]["answer_record_present"]]
        transitions = Counter((dirty[row["id"]]["contract_agreement"]["correct"], row["contract_agreement"]["correct"]) for row in paired)
        successes = correct_count(selected, "contract_agreement")
        invalid = len(selected) - len(valid)
        summaries.append({
            "file": name, "assigned": len(selected),
            "present_answer_records": sum(row["answer_record_present"] for row in selected),
            "missing_answer_ids": [row["id"] for row in selected if not row["answer_record_present"]],
            "null_answer_ids": [row["id"] for row in selected if row["null_answer"]],
            "purpose_text_mismatch_ids": [row["id"] for row in selected if row["answer_record_present"] and not row["purpose_text_matches_gold"]],
            "upstream_exact_correct": sum(row["upstream"]["accuracy"] == 1 for row in selected),
            "upstream_f1_sum": sum(row["upstream"]["f1"] for row in selected),
            "upstream_exceptions": sum(row["upstream"]["status"] == "exception" for row in selected),
            "typed_strict_correct": correct_count(selected, "typed_strict"),
            "contract_correct": successes, "valid_reference_denominator": len(valid),
            "invalid_reference_ids": [row["id"] for row in selected if row["contract_agreement"]["status"] == "invalid_reference"],
            "all_assigned_reference_uncertainty_bounds": [successes / len(selected), (successes + invalid) / len(selected)],
            "contract_status_counts": counter(selected, "contract_agreement"),
            "purpose_eligible_denominator": len(eligible),
            "purpose_eligible_correct": correct_count(eligible, "contract_agreement"),
            "purpose_eligible_present": sum(row["answer_record_present"] for row in eligible),
            "paired_present_eligible": len(paired),
            "dirty_to_saved_answer_transitions": {
                "wrong_to_correct": transitions[(False, True)], "correct_to_wrong": transitions[(True, False)],
                "correct_to_correct": transitions[(True, True)], "wrong_to_wrong": transitions[(False, False)]},
            "purpose_eligible_by_domain": {domain: {"n": len(part), "correct": correct_count(part, "contract_agreement")}
                for domain in sorted({row["domain"] for row in eligible})
                for part in [[row for row in eligible if row["domain"] == domain]]},
        })
    valid_controls = [x for x in controls if x["identity"]["status"] != "invalid_reference"]
    controls_passed = all(x["identity"]["correct"] is True and x["wrong_answer"]["correct"] is False for x in valid_controls)
    output = {
        "decision": "HOLD_PENDING_PURPOSE_AND_OUTPUT_PROVENANCE_QUALIFICATION",
        "scope": "Retrospective saved-answer scoring only; not fresh inference, historical output provenance, a paper-wide reproduction, or evidence of a novel method.",
        "scorer_version": VERSION, "source_commit": inventory["commit"],
        "contract_sha256": sha(args.contract), "scorer_sha256": sha(ROOT / "scorer.py"),
        "reference_controls": {"total": len(controls), "valid": len(valid_controls), "invalid_reference_ids": [x["id"] for x in controls if x["identity"]["status"] == "invalid_reference"],
                               "identities_passed": sum(x["identity"]["correct"] is True for x in valid_controls),
                               "wrong_answers_rejected": sum(x["wrong_answer"]["correct"] is False for x in valid_controls), "passed": controls_passed},
        "purpose_eligible_ids": [i for i in sorted(manifest) if manifest[i]["purpose_eligible"]],
        "purpose_ineligible_ids": [i for i in sorted(manifest) if not manifest[i]["purpose_eligible"]],
        "summaries": summaries,
        "interpretation_limits": ["Reference agreement is not automatically purpose success.",
                                  "Saved answer filenames lack a complete source-CSV execution chain; do not rank model capability from these tables.",
                                  "Missing model CSVs and raw fallback require the separate provenance audit.",
                                  "Task subsets were selected by contract inspection before aggregate replay, not model scores.",
                                  "Purpose IDs are clustered within source domains; no IID inference is asserted."],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {"REPLAY_SUMMARY.json": output, "REPLAY_CELLS.json": rows, "REFERENCE_CONTROLS.json": controls}
    for name, data in outputs.items():
        (args.output_dir / name).write_bytes((json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
    receipt = {"completed_utc": datetime.now(timezone.utc).isoformat(),
               "frozen_commit": frozen_commit,
               "git_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
               "python": sys.version, "platform": platform.platform(), "replay_script_sha256": sha(Path(__file__)),
               "input_inventory_sha256": sha(inventory_path), "verified_input_sha256": verified,
               "output_sha256": {name: sha(args.output_dir / name) for name in outputs},
               "paid_model_calls": 0, "aws_actions": 0}
    (args.output_dir / "REPLAY_RECEIPT.json").write_bytes((json.dumps(receipt, indent=2, allow_nan=False) + "\n").encode())
    print(json.dumps({"reference_controls": output["reference_controls"], "purpose_eligible": len(output["purpose_eligible_ids"]),
                      "files": len(summaries), "cells": len(rows), "output_dir": str(args.output_dir)}, indent=2))
    if not controls_passed:
        raise SystemExit("Reference controls failed; replay is diagnostic only")


if __name__ == "__main__":
    main()
