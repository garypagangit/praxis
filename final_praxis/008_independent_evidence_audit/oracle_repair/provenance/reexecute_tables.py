"""Post-freeze, offline query replay of archived CSVs; no model calls or fallback.

The reviewed QExecute/helper AST is extracted without upstream top-level I/O.
Each except handler is instrumented to record that it ran. Successful-path query
operations are unchanged; any caught exception invalidates that prediction for
task-success scoring, even when the upstream method returns a default value.
"""
from __future__ import annotations

import argparse
import ast
import collections
import contextlib
import copy
import csv
import datetime
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import sys
import warnings

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
REPAIR_ROOT = HERE.parent
sys.path.insert(0, str(REPAIR_ROOT))
from scorer import VERSION, score_answer

MODELS = ("gemma2", "gemma2base", "llama3.1", "mistral")
COMMIT = "082dcbf5304329ef1ff08f5830e4116256b00a59"
RUNNER_LABEL = "reviewed_queries_with_recorded_exception_handlers_and_numpy_scalar_serialization"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))


def freeze_check(commit, paths):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("A full frozen Git commit hash is required")
    repository = Path(subprocess.check_output(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True).strip())
    subprocess.run(["git", "-C", str(repository), "merge-base", "--is-ancestor", commit, "HEAD"], check=True)
    receipts = []
    for path in paths:
        path = path.resolve()
        relative = path.relative_to(repository).as_posix()
        frozen = subprocess.check_output(["git", "-C", str(repository), "show", f"{commit}:{relative}"])
        current = path.read_bytes()
        if frozen != current:
            raise ValueError(f"File differs from frozen commit: {relative}")
        receipts.append({"path": relative, "sha256": digest(current)})
    return repository, receipts


def parse_answers(payload):
    records = {}
    for line in payload.decode("utf-8-sig").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        identifier = int(row["pp_id"])
        if identifier in records or "answer" not in row:
            raise ValueError("Invalid or repeated answer ID")
        records[identifier] = row["answer"]
    return records


def has_nonfinite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return any(has_nonfinite(x) for x in value)
    if isinstance(value, dict):
        return any(has_nonfinite(x) for x in value.values())
    return False


def json_answer(value):
    conversions = []

    def numpy_scalar(item):
        if isinstance(item, np.generic):
            conversions.append(type(item).__name__)
            return item.item()
        raise TypeError(f"Unsupported query return type: {type(item).__name__}")

    # Match JSON storage's object-key conversion while preserving strings. This
    # explicit numpy-scalar extension is disclosed; there is no str() fallback.
    serialized = json.dumps(value, ensure_ascii=False, default=numpy_scalar, allow_nan=True)
    return json.loads(serialized), conversions


def public_value_properties(value):
    return {"return_type": type(value).__name__, "returned_null": value is None,
            "returned_empty_container": isinstance(value, (list, dict, str)) and len(value) == 0,
            "returned_nonfinite": has_nonfinite(value)}


class RecordHandlers(ast.NodeTransformer):
    def __init__(self):
        self.lines = []

    def visit_ExceptHandler(self, node):
        self.generic_visit(node)
        self.lines.append(node.lineno)
        call = ast.Expr(value=ast.Call(func=ast.Name(id="_record_query_handler", ctx=ast.Load()),
                                     args=[ast.Constant(node.lineno)], keywords=[]))
        node.body.insert(0, ast.copy_location(call, node))
        return node


def load_queries(payload, tasks):
    text = payload.decode("utf-8-sig")
    tree = ast.parse(text)
    selected = [node for node in tree.body if
                (isinstance(node, ast.ClassDef) and node.name == "QExecute") or
                (isinstance(node, ast.FunctionDef) and node.name == "safe_parse_datetime") or
                (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "ISO_8601_REGEX" for target in node.targets))]
    if len(selected) != 3:
        raise ValueError("Unexpected reviewed query/helper structure")
    klass = next(node for node in selected if isinstance(node, ast.ClassDef))
    if klass.bases or klass.decorator_list or any(not isinstance(node, ast.FunctionDef) for node in klass.body):
        raise ValueError("Unexpected executable class-level content")
    functions = {node.name: node for node in klass.body}
    for task in tasks.values():
        function = functions[task["query"]["function"]]
        if digest(ast.get_source_segment(text, function).encode("utf-8")) != task["query"]["function_sha256"]:
            raise ValueError(f"Contract query hash mismatch: {task['id']}")
    module = ast.Module(body=copy.deepcopy(selected), type_ignores=[])
    instrument = RecordHandlers()
    module = instrument.visit(module)
    ast.fix_missing_locations(module)
    handler_events = []

    def record_handler(line):
        exception = sys.exc_info()[1]
        handler_events.append({"handler_line": line, "exception_type": type(exception).__name__})

    namespace = {"pd": pd, "np": np, "re": re, "_record_query_handler": record_handler}
    exec(compile(module, "reviewed-instrumented-query-functions", "exec"), namespace)
    return namespace["QExecute"], handler_events, sorted(instrument.lines), digest(ast.dump(module, include_attributes=True).encode())


def execute_query(payload, function, handler_events):
    handler_events.clear()
    diagnostic = {"query_executed": False, "caught_exceptions": [], "warnings": {},
                  "stdout_characters": 0, "preprocessing": "pandas.read_csv defaults; no column removal, dtype override, repair, or raw fallback"}
    if payload is None:
        return None, {**diagnostic, "execution_status": "missing_csv"}
    try:
        rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig"))))
        malformed = [i for i, row in enumerate(rows[1:], 2) if len(row) != len(rows[0])] if rows else [1]
        diagnostic["csv_rows"] = max(0, len(rows) - 1)
        diagnostic["csv_columns"] = len(rows[0]) if rows else 0
        diagnostic["malformed_row_numbers"] = malformed
        if malformed:
            return None, {**diagnostic, "execution_status": "malformed_csv"}
    except (UnicodeError, csv.Error) as error:
        return None, {**diagnostic, "execution_status": "csv_decode_error", "error_type": type(error).__name__}
    stdout = io.StringIO()
    answer = None
    with warnings.catch_warnings(record=True) as caught_warnings, contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(io.StringIO()):
        warnings.simplefilter("always")
        try:
            table = pd.read_csv(io.BytesIO(payload))
        except Exception as error:
            diagnostic.update(execution_status="csv_parse_error", error_type=type(error).__name__)
        else:
            try:
                diagnostic["query_executed"] = True
                raw_answer = function(table.copy(deep=True))
            except Exception as error:
                diagnostic.update(execution_status="query_exception", error_type=type(error).__name__)
            else:
                try:
                    answer, scalar_conversions = json_answer(raw_answer)
                    diagnostic.update(public_value_properties(answer))
                    diagnostic["numpy_scalar_conversions"] = dict(collections.Counter(scalar_conversions))
                    diagnostic["execution_status"] = "caught_query_exception" if handler_events else "nonfinite_result" if has_nonfinite(answer) else "null_result" if answer is None else "ok"
                except (TypeError, ValueError) as error:
                    diagnostic.update(execution_status="serialization_error", error_type=type(error).__name__)
    diagnostic["caught_exceptions"] = list(handler_events)
    diagnostic["warnings"] = dict(collections.Counter(type(w.message).__name__ for w in caught_warnings))
    diagnostic["stdout_characters"] = len(stdout.getvalue())
    return answer, diagnostic


def score_prediction(reference, prediction, diagnostic, spec):
    status = diagnostic["execution_status"]
    prediction_status = "missing_output" if status == "missing_csv" else "ok" if status == "ok" else "execution_error"
    return score_answer(reference, prediction, spec=spec, prediction_status=prediction_status)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-root", required=True, type=Path)
    parser.add_argument("--model-cache", required=True, type=Path)
    parser.add_argument("--private-controls", required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=REPAIR_ROOT / "contract/TASK_CONTRACTS.json")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--private-output-dir", required=True, type=Path)
    parser.add_argument("--frozen-commit", required=True)
    parser.add_argument("--controls-only", action="store_true")
    args = parser.parse_args()
    manifest_path = HERE / "VERIFIED_SOURCE_MANIFEST.json"
    csv_manifest_path = HERE / "CSV_MANIFEST.json"
    frozen_files = [Path(__file__), REPAIR_ROOT / "scorer.py", args.contract, manifest_path, csv_manifest_path]
    repository, freeze_receipts = freeze_check(args.frozen_commit, frozen_files)
    private_output = args.private_output_dir.resolve()
    if private_output.is_relative_to(repository) or private_output.is_relative_to(args.output_dir.resolve()):
        raise ValueError("Private answers must remain outside the Git repository and public output directory")
    contract = read_json(args.contract)
    tasks = {int(task["id"]): task for task in contract["tasks"]}
    if len(tasks) != len(contract["tasks"]) or len(tasks) != 142:
        raise ValueError("Expected unique frozen 142-purpose contract")
    manifest = read_json(manifest_path)
    if manifest["commit"] != COMMIT or contract["upstream_revision"] != COMMIT:
        raise ValueError("Upstream revision mismatch")
    expected = {item["path"]: item for item in manifest["files"]}
    verified_inputs = {}

    def load(path, absent_allowed=False):
        if path not in expected:
            if absent_allowed:
                return None
            raise ValueError(f"Source omitted from frozen manifest: {path}")
        candidates = [args.audit_root / "inventory/cache" / path, args.model_cache / path]
        source = next((p for p in candidates if p.exists()), None)
        if source is None:
            if absent_allowed:
                return None
            raise FileNotFoundError(path)
        data = source.read_bytes()
        info = expected[path]
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest(data) != info["sha256"] or blob != info["git_blob_sha1"] or len(data) != info["bytes"]:
            raise ValueError(f"Pinned file mismatch: {path}")
        verified_inputs[path] = info["sha256"]
        return data

    gold_path = "evaluation/answer_1-154_gt.json"
    gold = parse_answers(load(gold_path))
    if set(gold) != set(tasks):
        raise ValueError("Reference and contract IDs differ")
    query_payload = load("evaluation/q_execution.py")
    for source in contract["source_files"]:
        if digest(load(source["path"])) != source["sha256"]:
            raise ValueError(f"Contract source hash mismatch: {source['path']}")
    controls_payload = args.private_controls.read_bytes()
    if digest(controls_payload) != contract["raw_clean_private_control_sha256"]:
        raise ValueError("Prior raw/clean controls differ from source-only freeze")
    prior_controls = {int(item["id"]): item for item in json.loads(controls_payload)}
    if set(prior_controls) != set(tasks):
        raise ValueError("Prior raw/clean control IDs differ")
    queries, events, handler_lines, instrumented_ast_sha = load_queries(query_payload, tasks)
    rows, private_rows, controls = [], [], []
    task_results = {}

    def run(kind, task, path, archived_answer=None, archived_present=False):
        identifier = task["id"]
        payload = load(path, absent_allowed=kind not in ("raw", "clean"))
        if kind in ("raw", "clean") and digest(payload) != task["tables"][kind]["sha256"]:
            raise ValueError(f"Contract table hash mismatch: {identifier} {kind}")
        prediction, diagnostic = execute_query(payload, getattr(queries, task["query"]["function"]), events)
        result = score_prediction(gold[identifier], prediction, diagnostic, task["scorer_spec"])
        row = {"group": kind, "id": identifier, "domain": task["domain"], "purpose_eligible": task["purpose_eligible"],
               "source_csv": path, "source_sha256": digest(payload) if payload is not None else None,
               "diagnostic": diagnostic, "contract_agreement": result,
               "archived_answer_present": archived_present,
               "historical_source_identity_asserted": False}
        if archived_present and diagnostic["query_executed"] and diagnostic["execution_status"] not in ("query_exception", "serialization_error"):
            # This compares a current derived value to a saved value. It does not
            # prove where or under which configuration the saved value arose.
            row["saved_answer_agreement"] = {"evaluated": True,
                "strict": score_answer(archived_answer, prediction),
                "contract": score_answer(archived_answer, prediction, spec=task["scorer_spec"])}
        else:
            row["saved_answer_agreement"] = {"evaluated": False, "reason": "no_saved_answer_or_no_returned_value"}
        private_rows.append({"group": kind, "id": identifier, "source_csv": path, "answer": prediction,
                             "execution_status": diagnostic["execution_status"]})
        rows.append(row)
        task_results[(kind, identifier)] = (prediction, row)
        return prediction, row

    # Gate model-output replay on fresh raw/clean controls, preserving all 142 IDs.
    for identifier in sorted(tasks):
        task = tasks[identifier]
        for kind in ("raw", "clean"):
            prediction, row = run(kind, task, task["tables"][kind]["path"])
            prior = prior_controls[identifier][kind]
            agreement = score_answer(prior["answer"], prediction, spec=task["scorer_spec"])
            controls.append({"id": identifier, "kind": kind,
                             "prior_return_value_agreement": agreement,
                             "current_execution_status": row["diagnostic"]["execution_status"],
                             "prior_uncaught_error_present": prior["error"] is not None,
                             "interpretation": "Return-value replication is distinct from task success; caught defaults remain task failures."})
    clean_rows = [row for row in rows if row["group"] == "clean"]
    clean_valid = [row for row in clean_rows if row["contract_agreement"]["status"] != "invalid_reference"]
    control_valid = [row for row in controls if row["prior_return_value_agreement"]["status"] != "invalid_reference"]
    clean_gate = all(row["contract_agreement"]["correct"] is True for row in clean_valid)
    repeat_gate = all(row["prior_return_value_agreement"]["correct"] is True and not row["prior_uncaught_error_present"] for row in control_valid)
    controls_passed = clean_gate and repeat_gate
    if controls_passed and not args.controls_only:
        archived_files = {model: parse_answers(load(f"evaluation/answer_1-154_{model}.json")) for model in MODELS}
        for model in MODELS:
            for identifier in sorted(tasks):
                task = tasks[identifier]
                path = f"CoT.response/{model}/datasets_llm/{model}_{task['domain']}_test_p{identifier}.csv"
                archived = archived_files[model]
                run(model, task, path, archived.get(identifier), identifier in archived)

    summaries = []
    for group in ("raw", "clean", *MODELS):
        selected = [row for row in rows if row["group"] == group]
        if not selected:
            continue
        eligible = [row for row in selected if row["purpose_eligible"]]
        valid = [row for row in selected if row["contract_agreement"]["status"] != "invalid_reference"]
        successes = sum(row["contract_agreement"]["correct"] is True for row in selected)
        transition = collections.Counter((task_results[("raw", row["id"])][1]["contract_agreement"]["correct"], row["contract_agreement"]["correct"]) for row in eligible)
        summaries.append({"group": group, "assigned": len(selected), "query_executed": sum(row["diagnostic"]["query_executed"] for row in selected),
                          "execution_status_counts": dict(collections.Counter(row["diagnostic"]["execution_status"] for row in selected)),
                          "contract_status_counts": dict(collections.Counter(row["contract_agreement"]["status"] for row in selected)),
                          "valid_reference_denominator": len(valid), "contract_correct": successes,
                          "invalid_reference_ids": [row["id"] for row in selected if row["contract_agreement"]["status"] == "invalid_reference"],
                          "purpose_eligible_denominator": len(eligible), "purpose_eligible_correct": sum(row["contract_agreement"]["correct"] is True for row in eligible),
                          "raw_to_current_eligible": {"wrong_to_correct": transition[(False, True)], "correct_to_wrong": transition[(True, False)], "correct_to_correct": transition[(True, True)], "wrong_to_wrong": transition[(False, False)]},
                          "saved_answer_comparisons": sum(row["saved_answer_agreement"]["evaluated"] for row in selected),
                          "saved_answer_strict_matches": sum(row["saved_answer_agreement"].get("strict", {}).get("correct") is True for row in selected),
                          "saved_answer_contract_matches": sum(row["saved_answer_agreement"].get("contract", {}).get("correct") is True for row in selected)})
    report = {"runner_label": RUNNER_LABEL, "source_commit": COMMIT, "frozen_git_commit": args.frozen_commit,
              "decision": "REPLAY_COMPLETE_NO_NEW_METHOD_QUALIFIED" if controls_passed and not args.controls_only else "CONTROLS_PASSED_MODEL_TABLES_NOT_RUN" if controls_passed else "HOLD_FRESH_RAW_CLEAN_CONTROLS_FAILED",
              "scope": "Archived CSV reexecution with pinned source queries and a repaired measurement contract; not fresh model inference or a historical generation reproduction.",
              "raw_fallback_allowed": False, "upstream_top_level_executed": False, "scorer_version": VERSION,
              "instrumentation": {"description": "Prepend exception-type recording to every reviewed except handler; preserve successful-path code. Any handler event prevents task-success credit.", "handler_lines": handler_lines, "instrumented_ast_sha256": instrumented_ast_sha},
              "serialization": "JSON round trip with explicit numpy scalar .item conversion only; mapping keys follow JSON conversion, code strings remain strings, no unsupported-type str fallback.",
              "control_gate": {"passed": controls_passed, "clean_reference_gate": clean_gate, "prior_return_value_replication_gate": repeat_gate,
                               "clean_valid_reference_denominator": len(clean_valid), "prior_control_valid_denominator": len(control_valid)},
              "summaries": summaries, "purpose_eligible_ids": [i for i in sorted(tasks) if tasks[i]["purpose_eligible"]],
              "limits": ["Purpose eligibility is provisional source review, not independent certification.", "Saved-answer agreement does not prove historical source identity.", "Malformed/missing/null/nonfinite/exception outputs remain in assigned task accounting.", "Any caught exception is conservatively treated as an execution failure even if upstream fallback returns a value.", "Purpose IDs share source domains; no IID uncertainty or model capability ranking is inferred."]}
    public = {"TABLE_REPLAY_SUMMARY.json": report, "TABLE_REPLAY_CELLS.json": rows, "TABLE_REPLAY_CONTROLS.json": controls}
    for name, value in public.items():
        write_json(args.output_dir / name, value)
    private_output.mkdir(parents=True, exist_ok=True)
    private_path = private_output / "RECOMPUTED_ANSWERS.jsonl"
    private_path.write_bytes(("\n".join(json.dumps(row, ensure_ascii=False, allow_nan=True) for row in private_rows) + "\n").encode("utf-8"))
    receipt = {"completed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "frozen_git_commit": args.frozen_commit,
               "frozen_files": freeze_receipts, "query_source_sha256": digest(query_payload),
               "verified_input_sha256": verified_inputs, "private_controls_sha256": digest(controls_payload),
               "private_answer_sha256": digest(private_path.read_bytes()), "private_answer_format": "Python JSONL allowing NaN/Infinity, preserving upstream values; never publish raw payloads",
               "output_sha256": {name: digest((args.output_dir / name).read_bytes()) for name in public},
               "python": sys.version, "platform": platform.platform(),
               "dependencies": {name: importlib.metadata.version(name) for name in ("pandas", "numpy", "python-dateutil")},
               "model_calls": 0, "cloud_actions": 0, "network_requests": 0}
    write_json(args.output_dir / "TABLE_REPLAY_RECEIPT.json", receipt)
    print(json.dumps({"decision": report["decision"], "controls": report["control_gate"], "assigned_table_cells": len(rows), "output_dir": str(args.output_dir)}, indent=2))
    return 0 if controls_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
