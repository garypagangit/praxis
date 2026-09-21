"""Audit stronger controls and compare full-query predictions without refitting."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedKFold

from ..tabular_batch import analyze_e1 as audit
from ..tabular_batch.run_e1 import write_json
from . import run_strong_baselines as strong


def support(data, seed, condition):
    rows = audit.fit_support(data, seed, 32)
    if condition == "equal_32_per_class":
        return rows
    audit.require(condition == "abundant_benign_1024", "Unknown condition")
    normal = data["classes"].tolist().index("NormalTraffic")
    original = set(rows.tolist())
    pool = [int(i) for i in np.flatnonzero((data["split"] == 0) & (data["y"] == normal)) if int(i) not in original]
    audit.require(len(pool) >= 992, "Insufficient benign fitting support")
    def key(i):
        return hashlib.sha256(f"STRONG_BASELINES_BENIGN_20260921|{seed}|{data['group_sha256'][i]}".encode("ascii")).digest()
    return np.r_[rows, np.asarray(sorted(pool, key=key)[:992], dtype=np.int64)]


def cv_check(cv, grid):
    audit.require(len(cv["candidates"]) == len(grid), "CV candidate count mismatch")
    means = []
    for candidate, parameters in zip(cv["candidates"], grid):
        values = np.asarray(candidate["fold_macro_f1"], dtype=float)
        audit.require(values.shape == (3,) and np.isfinite(values).all() and np.all((values >= 0) & (values <= 1)), "Invalid CV values")
        audit.require(candidate["parameters"] == parameters, "CV parameters mismatch")
        audit.require(np.isclose(values.mean(), candidate["mean_macro_f1"], rtol=0, atol=1e-12), "CV mean mismatch")
        means.append(float(values.mean()))
    selected = int(np.argmax(means))
    audit.require(cv["selected_candidate_index"] == selected and cv["selected_parameters"] == grid[selected], "CV chose wrong candidate")
    audit.require(np.isclose(cv["selected_mean_macro_f1"], means[selected], rtol=0, atol=1e-12), "Selected CV value mismatch")
    audit.require(cv["selection_data"] == "Selected fit support only", "Unexpected tuning data")
    return means[selected]


def fpr(metrics):
    index = metrics["classes"].index("NormalTraffic")
    row = np.asarray(metrics["confusion_matrix"])[index]
    return float((row.sum() - row[index]) / row.sum())


def validate_global_completion(root, binding, execution, protocol):
    """A running batch may lack this marker; an existing marker must be intact."""
    path = root / "COMPLETE.json"
    if not path.exists():
        return None
    marker = json.loads(path.read_text(encoding="utf-8"))
    audit.require(marker.get("execution_binding") == binding, "Global completion binding mismatch")
    audit.require(set(marker.get("artifact_sha256", {})) == {"PREFIT_RECEIPT.json", "RESULTS.json"}, "Global artifact roster mismatch")
    for filename, digest in marker["artifact_sha256"].items():
        audit.require(audit.file_hash(root / filename) == digest, "Global completed bytes changed")
    expected = {f"{condition}/{name}/{seed}" for condition in execution["conditions"]
                for name in execution["models"] for seed in protocol["seeds"]}
    audit.require(set(marker.get("cell_complete_sha256", {})) == expected, "Global completed cell roster mismatch")
    for name, digest in marker["cell_complete_sha256"].items():
        audit.require(audit.file_hash(root / "cells" / name / "COMPLETE.json") == digest, "Global cell receipt changed")
    all_registered = set(execution["conditions"]) == set(protocol["conditions"]) and set(execution["models"]) == set(protocol["models"])
    audit.require(marker.get("all_registered_cells_complete") == all_registered, "Global batch-completion claim mismatch")
    return audit.file_hash(path)


def validate_imputer(saved_statistics, selected_features):
    """Independently check stored medians, including the empty-column fallback."""
    expected = np.zeros(selected_features.shape[1], dtype=float)
    populated = ~np.isnan(selected_features).all(axis=0)
    expected[populated] = np.nanmedian(selected_features[:, populated], axis=0)
    audit.require(np.array_equal(saved_statistics, expected), "Imputer statistics do not match selected fitting rows")


def audit_strong(data, protocol, protocol_path, e1_protocol_path, roots):
    strong.validate_protocol(protocol, e1_protocol_path)
    source = Path(__file__).parent
    code = {"followup/run_strong_baselines.py": source / "run_strong_baselines.py",
            "followup/requirements_strong_baselines.txt": source / "requirements_strong_baselines.txt",
            "tabular_batch/run_e1.py": source.parent / "tabular_batch/run_e1.py",
            "tabular_batch/model_backend.py": source.parent / "tabular_batch/model_backend.py"}
    expected = {"data_sha256": protocol["data_npz_sha256"], "manifest_sha256": protocol["manifest_sha256"],
                "protocol_sha256": audit.file_hash(protocol_path), "e1_protocol_sha256": audit.file_hash(e1_protocol_path),
                "code_sha256": {name: audit.file_hash(path) for name, path in code.items()}}
    test = np.flatnonzero(data["split"] == 2)
    cells, seen, receipts = [], set(), []
    for root in map(Path, roots):
        prefit_path = root / "PREFIT_RECEIPT.json"
        prefit = json.loads(prefit_path.read_text(encoding="utf-8"))
        ex = prefit["execution"]
        binding = audit.value_hash(ex)
        audit.require(binding == prefit["execution_binding"], "Invalid prefit binding")
        audit.require(all(ex.get(k) == v for k, v in expected.items()), "Source/protocol binding mismatch")
        audit.require(ex["seeds"] == protocol["seeds"] and ex["classes"] == data["classes"].tolist(), "Seed/class mismatch")
        audit.require(bool(ex["models"]) and set(ex["models"]) <= set(protocol["models"]) and len(set(ex["models"])) == len(ex["models"]), "Invalid model roster")
        audit.require(bool(ex["conditions"]) and set(ex["conditions"]) <= set(protocol["conditions"]) and len(set(ex["conditions"])) == len(ex["conditions"]), "Invalid condition roster")
        audit.require(ex.get("actual_device") == "cpu" and ex.get("cpu_threads") == protocol["cpu_threads"], "Execution hardware settings mismatch")
        audit.require(ex["test_query"] == {"indices": test.tolist(), "fingerprints": data["group_sha256"][test].tolist()}, "Prefit test query mismatch")
        completed_sha = validate_global_completion(root, binding, ex, protocol)
        receipts.append({"prefit_sha256": audit.file_hash(prefit_path), "execution_binding": binding, "global_complete_sha256": completed_sha})
        for condition in ex["conditions"]:
            for seed in protocol["seeds"]:
                rows = support(data, seed, condition)
                folds = list(StratifiedKFold(3, shuffle=True, random_state=seed).split(np.zeros((len(rows), 1)), data["y"][rows]))
                registered_support = {"indices": rows.tolist(), "fingerprints": data["group_sha256"][rows].tolist(),
                    "class_counts": {name: int(np.sum(data["y"][rows] == k)) for k, name in enumerate(data["classes"])},
                    "inner_folds_support_positions": [{"train": a.tolist(), "validation": b.tolist()} for a, b in folds]}
                audit.require(ex["supports"][condition][str(seed)] == registered_support, "Support or fold mismatch")
                comparison = audit.value_hash({**expected, "condition": condition, "seed": seed, "support": registered_support})
                for name in ex["models"]:
                    folder = root / "cells" / condition / name / str(seed)
                    if not (folder / "COMPLETE.json").exists():
                        continue
                    key = (condition, name, seed)
                    audit.require(key not in seen, "Duplicate completed cell")
                    seen.add(key)
                    complete = json.loads((folder / "COMPLETE.json").read_text(encoding="utf-8"))
                    audit.require(complete["execution_binding"] == binding and complete["comparison_binding"] == comparison, "Completion binding mismatch")
                    audit.require(set(complete["file_sha256"]) == {"CELL.json", "PREDICTIONS.npz"}, "Completion artifact roster mismatch")
                    for filename, digest in complete["file_sha256"].items():
                        audit.require(audit.file_hash(folder / filename) == digest, "Completed bytes changed")
                    cell = json.loads((folder / "CELL.json").read_text(encoding="utf-8"))
                    audit.require((cell["condition"], cell["model"], cell["seed"]) == key, "Cell identity mismatch")
                    audit.require(cell.get("experiment") == protocol["experiment"] and cell.get("actual_device") == "cpu" and cell.get("versions") == ex["versions"], "Cell experiment/environment mismatch")
                    audit.require(cell["execution_binding"] == binding and cell["comparison_binding"] == comparison and cell["common_binding"] == expected, "Cell provenance mismatch")
                    audit.require(cell["prefit_receipt_sha256"] == audit.file_hash(prefit_path), "Prefit changed")
                    started = json.loads((folder / "STARTED.json").read_text(encoding="utf-8"))
                    audit.require(cell["started_receipt_sha256"] == audit.file_hash(folder / "STARTED.json"), "Start receipt changed")
                    audit.require(started["execution_binding"] == binding and started["comparison_binding"] == comparison and started["prefit_receipt_sha256"] == cell["prefit_receipt_sha256"], "Start binding mismatch")
                    audit.require(cell["prediction_sha256"] == complete["file_sha256"]["PREDICTIONS.npz"], "Prediction binding mismatch")
                    audit.require(cell["selected_fit_fingerprints_sha256"] == audit.value_hash(registered_support["fingerprints"]), "Fit fingerprint digest mismatch")
                    audit.require(cell["selected_fit_rows"] == len(rows) and cell["class_label_costs"] == registered_support["class_counts"] and cell["additional_tuning_labels"] == 0, "Label cost mismatch")
                    with np.load(folder / "PREDICTIONS.npz", allow_pickle=False) as z:
                        audit.require(np.array_equal(z["test_indices"], test) and np.array_equal(z["test_fingerprints"], data["group_sha256"][test]), "Query identity mismatch")
                        audit.require(np.array_equal(z["selected_fit_indices"], rows) and np.array_equal(z["selected_fit_fingerprints"], data["group_sha256"][rows]), "Fit identity mismatch")
                        audit.require(np.array_equal(z["classes"], data["classes"]) and np.array_equal(z["test_y"], data["y"][test]), "Test class/label mismatch")
                        validate_imputer(z["imputer_statistics"], data["X"][rows])
                        metrics = audit.recompute_metrics(z["test_y"], z["test_probabilities"], data["classes"].tolist())
                    audit.check_reported_metrics(cell["metrics"]["test"], metrics)
                    score = cv_check(cell["inner_cv"], protocol["model_grids"][name])
                    cells.append({"condition": condition, "model": name, "seed": seed, "cv_macro_f1": score,
                                  "metrics": metrics, "normal_fpr": fpr(metrics), "class_label_costs": cell["class_label_costs"],
                                  "prediction_sha256": cell["prediction_sha256"], "complete_sha256": audit.file_hash(folder / "COMPLETE.json")})
    return cells, receipts


def compare(e1, cells, protocol):
    foundation_cells = [c for c in e1["cells"] if c["model"] == "tabicl_v2"]
    foundation = {c["seed"]: c for c in foundation_cells}
    audit.require(len(foundation) == len(foundation_cells), "Duplicate foundation seed")
    audit.require(len({(c["condition"], c["seed"], c["model"]) for c in cells}) == len(cells), "Duplicate tree cell")
    gate = protocol["same_budget_primary_gate"]
    audit.require(gate["required_paired_seeds"] == len(protocol["seeds"]), "Gate and protocol seed count differ")
    outputs = {}
    for condition in protocol["conditions"]:
        pairs = []
        for seed in protocol["seeds"]:
            models = {c["model"]: c for c in cells if c["condition"] == condition and c["seed"] == seed}
            if seed not in foundation or not {"xgboost", "lightgbm"} <= set(models):
                continue
            selected = max([models["xgboost"], models["lightgbm"]], key=lambda c: c["cv_macro_f1"])
            a, b = foundation[seed]["test_metrics"], selected["metrics"]
            audit.require(a["classes"] == b["classes"], "Compared class orders differ")
            pairs.append({"seed": seed, "selected_tree": selected["model"], "tabicl_macro_f1": a["macro_f1"],
                          "tree_macro_f1": b["macro_f1"], "delta_macro_f1": a["macro_f1"] - b["macro_f1"],
                          "tabicl_normal_fpr": fpr(a), "tree_normal_fpr": fpr(b),
                          "recall_deltas": {name: a["per_stage"][name]["recall"] - b["per_stage"][name]["recall"] for name in a["classes"]}})
        average = float(np.mean([p["delta_macro_f1"] for p in pairs])) if pairs else None
        recall = {name: float(np.mean([p["recall_deltas"][name] for p in pairs])) if pairs else None for name in gate["high_risk_classes"]}
        gates = {"mean_macro_f1_gain_at_least_0.02": average is not None and average >= gate["mean_macro_f1_delta_min"],
                 **{name + "_mean_recall_loss_at_most_0.05": value is not None and value >= gate["mean_recall_delta_min"] for name, value in recall.items()}}
        complete = len(pairs) == gate["required_paired_seeds"]
        status = "INCOMPLETE" if not complete else ("PASS" if all(gates.values()) else "FAIL")
        if condition == "abundant_benign_1024":
            status = "DESCRIPTIVE_UNEQUAL_LABEL_BUDGET" if complete else "INCOMPLETE"
        outputs[condition] = {"status": status, "matched_seeds": len(pairs), "mean_macro_f1_delta": average,
                              "mean_high_risk_recall_deltas": recall, "gates": gates if condition == "equal_32_per_class" else None,
                              "pairs": pairs, "foundation_fit_labels": 192, "tree_fit_labels": 192 if condition == "equal_32_per_class" else 1184}
    return outputs


def run(data_path, protocol_path, e1_protocol_path, strong_roots, e1_roots):
    data_path = data_path / "DATA.npz" if data_path.is_dir() else data_path
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    audit.require(audit.file_hash(data_path) == protocol["data_npz_sha256"] and audit.file_hash(data_path.with_name("MANIFEST.json")) == protocol["manifest_sha256"], "Dataset mismatch")
    with np.load(data_path, allow_pickle=False) as z:
        data = {name: z[name] for name in z.files}
    e1 = audit.analyze(data_path, e1_protocol_path, e1_roots)
    cells, receipts = audit_strong(data, protocol, protocol_path, e1_protocol_path, strong_roots)
    expected_count = len(protocol["seeds"]) * len(protocol["conditions"]) * len(protocol["models"])
    summaries = {}
    for condition in protocol["conditions"]:
        summaries[condition] = {}
        for model in protocol["models"]:
            selected = [c for c in cells if c["condition"] == condition and c["model"] == model]
            summaries[condition][model] = {"seeds": len(selected), "macro_f1": audit.summarize([c["metrics"]["macro_f1"] for c in selected]), "normal_fpr": audit.summarize([c["normal_fpr"] for c in selected])}
    return {"audit_status": "PASS", "complete_strong_cells": len(cells), "expected_strong_cells": expected_count,
            "strong_batch_complete": len(cells) == expected_count, "protocol_sha256": audit.file_hash(protocol_path),
            "auditor_sha256": audit.file_hash(__file__), "source_receipts": receipts, "model_summaries": summaries,
            "comparisons": compare(e1, cells, protocol), "cells": cells,
            "full_e1_completed_cells": e1["completed_cell_count"], "full_e1_primary": e1["primary"],
            "interpretation": "Development followup, full identical test rows; repeated seeds are not independent incidents. Abundant-benign trees use 992 extra fitting labels. No independent confirmation or novelty established."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--e1-protocol", type=Path, required=True)
    parser.add_argument("--strong-run", type=Path, action="append", required=True)
    parser.add_argument("--e1-run", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve previous audits; use a fresh output file")
    result = run(args.data, args.protocol, args.e1_protocol, args.strong_run, args.e1_run)
    write_json(args.output, result)
    print(json.dumps({"audit_status": result["audit_status"], "completed_strong_cells": result["complete_strong_cells"], "comparisons": {k: {"status": v["status"], "paired_seeds": v["matched_seeds"]} for k, v in result["comparisons"].items()}}))
