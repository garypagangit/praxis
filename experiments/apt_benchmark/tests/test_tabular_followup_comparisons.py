import unittest
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

import numpy as np
from sklearn.tree import DecisionTreeClassifier

from experiments.apt_benchmark.tabular_followup import audit_comparisons as check


CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]


def metrics(score, recall=.8):
    return {"classes": CLASSES, "macro_f1": score, "confusion_matrix": np.eye(6, dtype=int).tolist(),
            "per_stage": {name: {"recall": recall} for name in CLASSES}}


def comparison_protocol(seeds, conditions):
    gate = deepcopy(check.strong.PRIMARY_GATE)
    gate["required_paired_seeds"] = len(seeds)
    return {"seeds": seeds, "conditions": conditions, "same_budget_primary_gate": gate}


class ComparisonsTests(unittest.TestCase):
    def test_cv_rejects_test_selected_or_tampered_winner(self):
        grid = [{"a": 1}, {"a": 2}]
        cv = {"candidates": [{"parameters": p, "fold_macro_f1": [v]*3, "mean_macro_f1": v} for p, v in zip(grid, [.8, .4])],
              "selected_candidate_index": 0, "selected_parameters": grid[0], "selected_mean_macro_f1": .8,
              "selection_data": "Selected fit support only"}
        self.assertAlmostEqual(check.cv_check(cv, grid), .8)
        for key, value in [("selected_candidate_index", 1), ("selection_data", "test")]:
            changed = deepcopy(cv)
            changed[key] = value
            with self.assertRaises(ValueError):
                check.cv_check(changed, grid)
        changed = deepcopy(cv)
        changed["candidates"][0]["fold_macro_f1"][0] = float("nan")
        with self.assertRaises(ValueError):
            check.cv_check(changed, grid)

    def test_comparator_is_selected_using_cv_not_test(self):
        seeds = list(range(10))
        protocol = comparison_protocol(seeds, ["equal_32_per_class", "abundant_benign_1024"])
        e1 = {"cells": [{"model": "tabicl_v2", "seed": s, "test_metrics": metrics(.6)} for s in seeds]}
        cells = [{"condition": c, "seed": s, "model": m, "cv_macro_f1": cv, "metrics": metrics(test)}
                 for c in protocol["conditions"] for s in seeds for m, cv, test in [("xgboost", .9, .5), ("lightgbm", .7, .8)]]
        result = check.compare(e1, cells, protocol)
        self.assertEqual(result["equal_32_per_class"]["status"], "PASS")
        self.assertTrue(all(p["selected_tree"] == "xgboost" for p in result["equal_32_per_class"]["pairs"]))
        self.assertEqual(result["abundant_benign_1024"]["status"], "DESCRIPTIVE_UNEQUAL_LABEL_BUDGET")
        self.assertIsNone(result["abundant_benign_1024"]["gates"])
        e1["cells"].pop()
        self.assertEqual(check.compare(e1, cells, protocol)["equal_32_per_class"]["status"], "INCOMPLETE")

    def test_high_f1_cannot_hide_rare_stage_loss(self):
        protocol = comparison_protocol([1], ["equal_32_per_class"])
        a = metrics(.9)
        a["per_stage"]["InitialCompromise"]["recall"] = .1
        e1 = {"cells": [{"model": "tabicl_v2", "seed": 1, "test_metrics": a}]}
        cells = [{"condition": "equal_32_per_class", "seed": 1, "model": m, "cv_macro_f1": .5, "metrics": metrics(.5)} for m in ["xgboost", "lightgbm"]]
        self.assertEqual(check.compare(e1, cells, protocol)["equal_32_per_class"]["status"], "FAIL")

    def test_abundant_support_preserves_attacks_and_never_uses_calibration(self):
        y = np.concatenate([np.repeat(k, 1150 if k == 3 else 42) for k in range(6)])
        split = np.zeros(len(y), dtype=int)
        for k in range(6):
            split[np.flatnonzero(y == k)[-5:]] = 2
        data = {"y": y, "split": split, "classes": np.asarray(CLASSES), "group_sha256": np.asarray([f"{i:064x}" for i in range(len(y))])}
        a = check.support(data, 20260921, "equal_32_per_class")
        b = check.support(data, 20260921, "abundant_benign_1024")
        self.assertEqual(len(b), 1184)
        self.assertTrue(np.array_equal(b[:192], a))
        self.assertTrue(np.all(y[b[192:]] == 3))
        self.assertTrue(np.all(split[b] == 0))
        self.assertEqual(len(set(b.tolist())), len(b))
        self.assertTrue(np.array_equal(check.strong.select_support(data, 20260921, "abundant_benign_1024"), b))

    def test_duplicate_pairs_and_shortened_gate_are_rejected(self):
        protocol = comparison_protocol([1], ["equal_32_per_class"])
        e1 = {"cells": [{"model": "tabicl_v2", "seed": 1, "test_metrics": metrics(.9)}]}
        cells = [{"condition": "equal_32_per_class", "seed": 1, "model": name, "cv_macro_f1": .5, "metrics": metrics(.5)} for name in ["xgboost", "lightgbm"]]
        with self.assertRaisesRegex(ValueError, "Duplicate tree"):
            check.compare(e1, [*cells, cells[0]], protocol)
        with self.assertRaisesRegex(ValueError, "Duplicate foundation"):
            check.compare({"cells": e1["cells"] * 2}, cells, protocol)
        protocol["same_budget_primary_gate"]["required_paired_seeds"] = 10
        with self.assertRaisesRegex(ValueError, "seed count differ"):
            check.compare(e1, cells, protocol)

    def test_imputation_audit_uses_selected_rows_and_empty_column_zero(self):
        selected = np.asarray([[1., np.nan], [5., np.nan], [np.nan, np.nan]])
        check.validate_imputer(np.asarray([3., 0.]), selected)
        for invalid in ([1e8, 0.], [3., np.nan], [3.], [3., 1.]):
            with self.assertRaisesRegex(ValueError, "Imputer statistics"):
                check.validate_imputer(np.asarray(invalid), selected)

    def test_real_synthetic_receipts_audit_and_environment_tampering(self):
        # Reuse the synthetic fixture only; no SCVIC data or scientific fits.
        from experiments.apt_benchmark.tests.test_tabular_followup_strong_baselines import StrongBaselineTests
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, path, original, protocol_path, protocol = StrongBaselineTests().make_inputs(root)
            output = root / "output"
            with patch.object(check.strong, "make_tree", return_value=DecisionTreeClassifier(max_depth=3, random_state=1)):
                check.strong.run(path, protocol_path, output, e1_protocol_path=original,
                                 models=["random_forest"], conditions=["equal_32_per_class"])
            cells, receipts = check.audit_strong(data, protocol, protocol_path, original, [output])
            self.assertEqual(len(cells), 1)
            self.assertIsNotNone(receipts[0]["global_complete_sha256"])
            cell_dir = output / "cells/equal_32_per_class/random_forest/20260921"
            cell = json.loads((cell_dir / "CELL.json").read_text())
            cell["versions"]["numpy"] = "wrong-version"
            check.write_json(cell_dir / "CELL.json", cell)
            marker = json.loads((cell_dir / "COMPLETE.json").read_text())
            marker["file_sha256"]["CELL.json"] = check.audit.file_hash(cell_dir / "CELL.json")
            check.write_json(cell_dir / "COMPLETE.json", marker)
            global_marker = json.loads((output / "COMPLETE.json").read_text())
            global_marker["cell_complete_sha256"]["equal_32_per_class/random_forest/20260921"] = check.audit.file_hash(cell_dir / "COMPLETE.json")
            check.write_json(output / "COMPLETE.json", global_marker)
            with self.assertRaisesRegex(ValueError, "experiment/environment mismatch"):
                check.audit_strong(data, protocol, protocol_path, original, [output])

    def test_global_completion_rejects_changed_aggregate_and_false_batch_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            execution = {"models": ["random_forest"], "conditions": ["equal_32_per_class"]}
            protocol = {"seeds": [1], "models": check.strong.MODELS, "conditions": check.strong.CONDITIONS}
            self.assertIsNone(check.validate_global_completion(root, "bound", execution, protocol))
            for name in ["PREFIT_RECEIPT.json", "RESULTS.json", "cells/equal_32_per_class/random_forest/1/COMPLETE.json"]:
                check.write_json(root / name, {})
            marker = {"execution_binding": "bound", "all_registered_cells_complete": False,
                      "artifact_sha256": {name: check.audit.file_hash(root / name) for name in ["PREFIT_RECEIPT.json", "RESULTS.json"]},
                      "cell_complete_sha256": {"equal_32_per_class/random_forest/1": check.audit.file_hash(root / "cells/equal_32_per_class/random_forest/1/COMPLETE.json")}}
            check.write_json(root / "COMPLETE.json", marker)
            self.assertIsNotNone(check.validate_global_completion(root, "bound", execution, protocol))
            marker["all_registered_cells_complete"] = True
            check.write_json(root / "COMPLETE.json", marker)
            with self.assertRaisesRegex(ValueError, "batch-completion claim"):
                check.validate_global_completion(root, "bound", execution, protocol)
            marker["all_registered_cells_complete"] = False
            check.write_json(root / "COMPLETE.json", marker)
            (root / "RESULTS.json").write_text('{"tampered": true}')
            with self.assertRaisesRegex(ValueError, "Global completed bytes"):
                check.validate_global_completion(root, "bound", execution, protocol)


if __name__ == "__main__":
    unittest.main()
