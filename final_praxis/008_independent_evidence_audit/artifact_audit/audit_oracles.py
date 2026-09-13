"""Offline contract audit of reviewed, immutable AutoDCWorkflow evaluator functions.
No models, API clients, upstream module import, network access, or upstream top-level I/O.
Run after fetch_sources.py. Exit 0 means the audit completed, NOT that its base passed.
"""
from pathlib import Path
import ast, collections, contextlib, copy, csv, hashlib, importlib.metadata, io, json, math, platform, sys
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "source"
EXPECTED_SHA = {
    "evaluation/answer_analysis.py": "3c551a79e26818b82799b0bd079ddb19caae01f526b10369fbea5b2fcc2489a1",
    "evaluation/data_compare.py": "06dbd1dc87a65317ac0a34fe1b6f86913d5eaa2ea9a964e1d256b7ab4559d97b",
    "evaluation/q_execution.py": "b5b7c42a1e60a0457cc275a17cc839777d9aa461d8ae7c30bb68922277f13622",
    "dataset-all - all_purposes.csv": "17f3c65a86630c603f034083581da03ab773ccf7deebf8636ece6f9d8a18ff06",
    "CoT.rerun/answer_1-154_gt.json": "9e4cbb32d08408ca103df40273e6db6ed27a3edc2982f57cd1412d318b994f49",
}
ALLOWED_IMPORTS = {"json", "typing", "difflib", "math", "pandas", "numpy", "dateutil.parser"}


def source_text(name):
    raw = (SOURCE / name).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED_SHA[name]:
        raise RuntimeError(f"Pinned source mismatch: {name}: {actual}")
    return raw.decode("utf-8-sig")


def reviewed_functions(name):
    tree = ast.parse(source_text(name), filename=name)
    for node in tree.body:
        if isinstance(node, ast.Import):
            if any(n.name not in ALLOWED_IMPORTS for n in node.names):
                raise RuntimeError("Unexpected import")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in ALLOWED_IMPORTS:
                raise RuntimeError("Unexpected from import")
        elif not isinstance(node, ast.FunctionDef):
            raise RuntimeError("Unexpected module-level statement")
    namespace = {"__name__": "audited_pinned_functions"}
    exec(compile(tree, name, "exec"), namespace)
    return namespace


def selected_queries():
    """Extract only three short, reviewed methods; never execute q_execution module."""
    tree = ast.parse(source_text("evaluation/q_execution.py"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "QExecute")
    wanted = {"pp1_exe", "pp2_exe", "pp3_exe"}
    funcs = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    if {n.name for n in funcs} != wanted:
        raise RuntimeError("Missing frozen query functions")
    module = ast.Module(body=funcs, type_ignores=[])
    namespace = {"pd": pd, "__name__": "audited_selected_queries"}
    exec(compile(ast.fix_missing_locations(module), "reviewed_QExecute_subset", "exec"), namespace)
    return namespace


def wrong_answer(answer):
    if type(answer) is int:
        return answer + max(1, abs(answer) // 2)
    if type(answer) is float:
        return answer + max(1.0, abs(answer) * 0.5)
    if isinstance(answer, str):
        return "__AUDIT_WRONG_ANSWER__"
    if isinstance(answer, list):
        return [] if answer else ["__AUDIT_WRONG_ITEM__"]
    if isinstance(answer, dict):
        return {k: "__AUDIT_WRONG_VALUE__" for k in answer} if answer else {"__AUDIT_WRONG_KEY__": 1}
    raise TypeError(type(answer).__name__)


def capture_call(fn, *args):
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            value = fn(*args)
        return {"value": value, "exception": None, "stdout": captured.getvalue()}
    except Exception as exc:
        return {"value": None, "exception": type(exc).__name__, "message": str(exc), "stdout": captured.getvalue()}


def json_safe(value):
    # Receipt encoding only. All scorer inputs retain the source's original values.
    if isinstance(value, float) and not math.isfinite(value):
        return {"__nonfinite_float__": repr(value)}
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    return value


def nonfinite_paths(value, path="answer"):
    if isinstance(value, float) and not math.isfinite(value):
        return [path]
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in nonfinite_paths(v, path + "." + str(k))]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in nonfinite_paths(v, path + "[" + str(i) + "]")]
    return []


def main():
    for filename in EXPECTED_SHA:
        source_text(filename)
    answer_mod = reviewed_functions("evaluation/answer_analysis.py")
    data_mod = reviewed_functions("evaluation/data_compare.py")
    score = answer_mod["calculate_answer_metrics"]
    compare = data_mod["average_match_ratio"]
    gt = [json.loads(line) for line in source_text("CoT.rerun/answer_1-154_gt.json").splitlines() if line.strip()]
    purpose_rows = list(csv.DictReader(io.StringIO(source_text("dataset-all - all_purposes.csv"))))
    purpose_map = {int(row["ID"]): row for row in purpose_rows}
    answer_cases = []
    for row in gt:
        value = row["answer"]
        identity = capture_call(score, copy.deepcopy(value), copy.deepcopy(value))
        wrong = wrong_answer(value)
        negative = capture_call(score, copy.deepcopy(value), copy.deepcopy(wrong))
        answer_cases.append({
            "id": row["pp_id"], "type": type(value).__name__,
            "gold": value, "wrong": wrong,
            "identity": identity, "negative": negative,
            "identity_accuracy_is_one": identity["exception"] is None and identity["value"]["accuracy"] == 1,
            "negative_accuracy_is_zero": negative["exception"] is None and negative["value"]["accuracy"] == 0,
        })
    by_type = {}
    for name in sorted({x["type"] for x in answer_cases}):
        subset = [x for x in answer_cases if x["type"] == name]
        by_type[name] = {
            "n": len(subset),
            "identity_accuracy_one": sum(x["identity_accuracy_is_one"] for x in subset),
            "identity_f1_one": sum(x["identity"]["exception"] is None and x["identity"]["value"]["f1"] == 1 for x in subset),
            "negative_accuracy_zero": sum(x["negative_accuracy_is_zero"] for x in subset),
            "wrong_answer_f1_one": sum(x["negative"]["exception"] is None and x["negative"]["value"]["f1"] == 1 for x in subset),
            "identity_failure_ids": [x["id"] for x in subset if not x["identity_accuracy_is_one"]],
        }

    table_cases = []
    def table_case(name, gold, pred, interpretation, target="value"):
        actual = capture_call(compare, pd.DataFrame(gold), pd.DataFrame(pred), target)
        table_cases.append({"name": name, "gold": gold, "prediction": pred, "target_columns": target, "observed": actual, "interpretation": interpretation})
    clean = {"row_id": [101, 102], "value": ["ALPHA", "BETA"]}
    table_case("identity", clean, clean, "Positive control; expect 1.")
    table_case("all_values_wrong", clean, {"row_id": [101, 102], "value": ["WRONG", "WRONG"]}, "Negative control; expect 0.")
    table_case("same_records_reordered", clean, {"row_id": [102, 101], "value": ["BETA", "ALPHA"]}, "Same records by explicit row_id, but comparator uses positional/default index alignment.")
    table_case("extra_wrong_record", clean, {"row_id": [101, 102, 103], "value": ["ALPHA", "BETA", "WRONG"]}, "Extra rows are not penalized by this target-column comparator.")
    table_case("missing_record", clean, {"row_id": [101], "value": ["ALPHA"]}, "Missing output rows require explicit failure accounting rather than unhandled exceptions.")
    table_case("changed_gold_null", {"row_id": [101, 102], "value": ["ALPHA", None]}, {"row_id": [101, 102], "value": ["ALPHA", "ARBITRARY_FILL"]}, "Null gold cells are excluded. Whether filling is allowed must be set by the task; this metric cannot measure preservation there.")
    table_case("all_gold_null", {"row_id": [101, 102], "value": [None, None]}, {"row_id": [101, 102], "value": [None, None]}, "All-null targets need a defined result; denominator is zero upstream.")
    table_case("missing_target_column", clean, {"row_id": [101, 102], "other": ["ALPHA", "BETA"]}, "Schema failures need explicit scoring.")
    queries = selected_queries()
    q1 = queries["pp1_exe"](pd.DataFrame({"page_count": [1, 22]}))
    q2 = queries["pp2_exe"](pd.DataFrame({"page_count": [1, 2]}))
    q3 = queries["pp3_exe"](pd.DataFrame({"event": ["A", "B", "A"]}))
    query_cases = [
        {"id": 1, "purpose": purpose_map[1]["Purposes"], "query_output": q1, "output_type": type(q1).__name__, "identity_score": score(q1, q1), "observation": "Actual upstream query returns an int that upstream answer scoring cannot credit."},
        {"id": 2, "purpose": purpose_map[2]["Purposes"], "input_page_counts": [1, 2], "query_output": q2, "unrounded_mean": 1.5, "observation": "Query truncates the arithmetic mean to int; purpose does not specify this rounding."},
        {"id": 3, "purpose": purpose_map[3]["Purposes"], "input_events": ["A", "B", "A"], "query_output": q3, "distinct_count": 2, "observation": "Published purpose asks for a count, but query and released gold return distinct values."},
    ]
    summary = {
        "decision": "HOLD_UNTRUSTWORTHY_BASELINE_ORACLE",
        "audit_execution_completed": True,
        "scope": "142 released gold-answer identity/negative fixture pairs; eight data-comparator fixtures; three reviewed actual query functions. Not a full pipeline or saved-model-performance reproduction.",
        "repository_commit": "082dcbf5304329ef1ff08f5830e4116256b00a59",
        "input_hashes": EXPECTED_SHA,
        "environment": {"python": sys.version, "platform": platform.platform(), "packages": {p: importlib.metadata.version(p) for p in ["pandas", "numpy", "python-dateutil"]}},
        "purpose_rows": len(purpose_rows), "unique_purpose_ids": len(purpose_map),
        "gold_rows": len(gt), "unique_gold_ids": len({x["pp_id"] for x in gt}),
        "id_sets_equal": set(purpose_map) == {x["pp_id"] for x in gt},
        "nonfinite_gold": [{"id": x["pp_id"], "paths": nonfinite_paths(x["answer"])} for x in gt if nonfinite_paths(x["answer"])],
        "receipt_encoding": "Python json.loads accepts upstream NaN; original values supplied to scorer unchanged. Nonfinite values tagged only in output JSON. Their identity behavior is not a valid semantic scoring guarantee.",
        "answer_fixtures_by_type": by_type,
        "identity_correct": sum(x["identity_accuracy_is_one"] for x in answer_cases),
        "identity_total": len(answer_cases),
        "negative_correct": sum(x["negative_accuracy_is_zero"] for x in answer_cases),
        "table_fixtures": table_cases, "query_fixtures": query_cases,
        "minimal_repairs": [
            "Freeze one authoritative purpose-to-query-to-gold contract; resolve pp2 rounding and pp3 count-versus-list mismatch before interpreting aggregate task success.",
            "Normalize numeric types explicitly (exclude bool; define finite-value and tolerance rules); handle integer and mixed int/float comparisons; add identity/wrong fixtures for every released answer type.",
            "Do not use dictionary-key F1 as answer-value correctness; specify canonical exact/typed value scoring and list ordering/duplicate policy per task.",
            "Define stable row identity or task-specific order invariance, extra/deleted-row accounting, missing-column behavior and null semantics; do not silently exclude failures.",
            "Keep unmodified upstream results as a reproduction track, and any repaired oracle as a separately versioned measurement amendment. Re-score released outputs offline before any new inference.",
        ],
    }
    (ROOT / "ANSWER_FIXTURES.json").write_text(json.dumps(json_safe(answer_cases), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (ROOT / "AUDIT.json").write_text(json.dumps(json_safe(summary), indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["decision", "purpose_rows", "gold_rows", "id_sets_equal", "answer_fixtures_by_type", "identity_correct", "identity_total", "negative_correct"]}, indent=2))
    print("TABLE_FIXTURES", json.dumps([{ "name": x["name"], "value": x["observed"]["value"], "exception": x["observed"]["exception"]} for x in table_cases]))
    print("QUERY_FIXTURES", json.dumps(query_cases))

if __name__ == "__main__":
    main()
