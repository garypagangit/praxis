"""Versioned, offline typed comparisons. No model clients or upstream imports."""
import json
import math

VERSION = "typed-oracle-v1"


def _invalid(value, allow_null=True):
    if value is None:
        return not allow_null
    if type(value) is float:
        return not math.isfinite(value)
    if type(value) in (str, int, bool):
        return False
    if type(value) is list:
        return any(_invalid(x, allow_null) for x in value)
    if type(value) is dict:
        return any(type(k) is not str or _invalid(v, allow_null) for k, v in value.items())
    return True


def _pointer(path, key):
    return path + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _matched(left, right, equal):
    """Perfect bipartite matching; greedy matching fails with numeric tolerance."""
    if len(left) != len(right):
        return False
    edges = [[j for j, y in enumerate(right) if equal(x, y)] for x in left]
    assigned = {}

    def augment(i, seen):
        for j in edges[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in assigned or augment(assigned[j], seen):
                assigned[j] = i
                return True
        return False

    return all(augment(i, set()) for i in range(len(left)))


def _deduplicate(values):
    # Duplicate membership is exact typed equality, independent of float tolerance.
    result = []
    for value in values:
        if not any(_equal(value, x, {}, "") for x in result):
            result.append(value)
    return result


def _equal(reference, prediction, spec, path):
    if type(reference) is bool or type(prediction) is bool:
        return type(reference) is bool and type(prediction) is bool and reference == prediction
    if type(reference) in (int, float) and type(prediction) in (int, float):
        if spec.get("numeric_mode", "exact") == "exact":
            return reference == prediction
        return math.isclose(reference, prediction, abs_tol=spec.get("abs_tol", 0),
                            rel_tol=spec.get("rel_tol", 0))
    if type(reference) is not type(prediction):
        return False
    if reference is None or type(reference) is str:
        return reference == prediction
    if type(reference) is dict:
        if reference.keys() != prediction.keys():
            return False
        columnar = spec.get("columnar_mode") if path == "" else None
        if columnar:
            if not all(type(x) is list for x in (*reference.values(), *prediction.values())):
                return False
            ref_lengths = {len(x) for x in reference.values()}
            pred_lengths = {len(x) for x in prediction.values()}
            if len(ref_lengths) > 1 or len(pred_lengths) > 1:
                return False
            keys = sorted(reference)
            ref_rows = [dict(zip(keys, xs)) for xs in zip(*(reference[k] for k in keys))]
            pred_rows = [dict(zip(keys, xs)) for xs in zip(*(prediction[k] for k in keys))]
            row_spec = {k: v for k, v in spec.items() if k != "columnar_mode"}
            row_spec["path_modes"] = {**row_spec.get("path_modes", {}), "": columnar}
            return _equal(ref_rows, pred_rows, row_spec, "")
        return all(_equal(v, prediction[k], spec, _pointer(path, k)) for k, v in reference.items())
    if type(reference) is list:
        mode = spec.get("path_modes", {}).get(path, spec.get("list_mode", "ordered"))
        if mode == "ordered":
            return len(reference) == len(prediction) and all(
                _equal(x, y, spec, _pointer(path, i)) for i, (x, y) in enumerate(zip(reference, prediction)))
        left, right = reference, prediction
        if mode == "set":
            left, right = _deduplicate(left), _deduplicate(right)
        return _matched(left, right, lambda x, y: _equal(x, y, spec, _pointer(path, "*")))
    return False


def _validate_spec(spec):
    if spec.get("numeric_mode", "exact") not in ("exact", "tolerant"):
        raise ValueError("Unknown numeric_mode")
    for key in ("abs_tol", "rel_tol"):
        val = spec.get(key, 0)
        if type(val) not in (int, float) or not math.isfinite(val) or val < 0:
            raise ValueError("Tolerances must be finite nonnegative numbers")
    modes = [spec.get("list_mode", "ordered"), *spec.get("path_modes", {}).values()]
    if any(x not in ("ordered", "multiset", "set") for x in modes):
        raise ValueError("Unknown list mode")
    if spec.get("columnar_mode") not in (None, "ordered", "multiset"):
        raise ValueError("Unknown columnar mode")


def score_answer(reference, prediction=None, *, spec=None, prediction_status="ok"):
    spec = spec or {}
    _validate_spec(spec)
    if prediction_status not in ("ok", "missing_output", "execution_error"):
        raise ValueError("Unknown prediction_status")
    if _invalid(reference, spec.get("allow_null", True)):
        return {"status": "invalid_reference", "correct": None, "reason": "nonfinite_or_unsupported_reference"}
    if spec.get("columnar_mode") and (type(reference) is not dict or
            not all(type(x) is list for x in reference.values()) or
            len({len(x) for x in reference.values()}) > 1):
        return {"status": "invalid_reference", "correct": None, "reason": "invalid_parallel_columns"}
    if prediction_status != "ok":
        return {"status": prediction_status, "correct": False, "reason": prediction_status}
    if _invalid(prediction, spec.get("allow_null", True)):
        return {"status": "incorrect", "correct": False, "reason": "nonfinite_or_unsupported_prediction"}
    correct = _equal(reference, prediction, spec, "")
    return {"status": "correct" if correct else "incorrect", "correct": correct,
            "reason": "typed_agreement" if correct else "typed_mismatch"}


def _identity(row, columns):
    vals = [row[k] for k in columns]
    if any(v is None or type(v) not in (str, int, float, bool) or _invalid(v) for v in vals):
        raise ValueError("record IDs must be nonnull finite scalars")
    # IDs are type-preserving, even if answer quantities allow int/float equality.
    return json.dumps([[type(v).__name__, v] for v in vals], ensure_ascii=False, allow_nan=False)


def score_table(reference_rows, prediction_rows=None, *, id_columns, required_columns=None,
                prediction_status="ok"):
    """Strict preservation control for declared unique IDs; not a cleaning oracle."""
    def failed(status, reason):
        return {"status": status, "correct": None if status == "invalid_reference" else False,
                "reason": reason, "matched_cells": 0, "total_cells": None}
    if prediction_status not in ("ok", "missing_output", "execution_error"):
        raise ValueError("Unknown prediction_status")
    if not id_columns or len(set(id_columns)) != len(id_columns):
        return failed("invalid_reference", "missing_or_repeated_identity_columns")
    if type(reference_rows) is not list or any(type(x) is not dict for x in reference_rows):
        return failed("invalid_reference", "reference_rows_must_be_objects")
    columns = set(required_columns if required_columns is not None else
                  [k for row in reference_rows for k in row]) | set(id_columns)
    if any(set(row) != columns for row in reference_rows):
        return failed("invalid_reference", "reference_schema_mismatch")
    indexes = []
    for rows, status in ((reference_rows, "invalid_reference"), (prediction_rows, "incorrect")):
        if status == "incorrect":
            if prediction_status != "ok":
                return failed(prediction_status, prediction_status)
            if type(rows) is not list or any(type(x) is not dict for x in rows):
                return failed("incorrect", "prediction_rows_must_be_objects")
            if any(set(row) != columns for row in rows):
                return failed("incorrect", "prediction_schema_mismatch")
        index = {}
        for row in rows:
            if _invalid(row):
                return failed(status, "nonfinite_or_unsupported_cell")
            try:
                key = _identity(row, id_columns)
            except (ValueError, KeyError) as exc:
                return failed(status, str(exc))
            if key in index:
                return failed(status, "duplicate_identity")
            index[key] = row
        indexes.append(index)
    ref, pred = indexes
    common = ref.keys() & pred.keys()
    missing, added = sorted(ref.keys() - pred.keys()), sorted(pred.keys() - ref.keys())
    matched = sum(_equal(ref[k][c], pred[k][c], {}, "") for k in common for c in columns)
    total = len(ref.keys() | pred.keys()) * len(columns)
    correct = not missing and not added and matched == total
    return {"status": "correct" if correct else "incorrect", "correct": correct,
            "reason": "record_agreement" if correct else "record_mismatch",
            "matched_cells": matched, "total_cells": total, "missing_ids": missing,
            "added_ids": added, "cell_match_fraction": matched / total if total else 1.0}
