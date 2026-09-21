import unittest
from copy import deepcopy

import numpy as np

from experiments.apt_benchmark.tabular_followup import audit_comparisons as check


CLASSES = ["DataExfiltration", "InitialCompromise", "LateralMovement", "NormalTraffic", "Pivoting", "Reconnaissance"]


def metrics(score, recall=.8):
    return {"classes": CLASSES, "macro_f1": score, "confusion_matrix": np.eye(6, dtype=int).tolist(),
            "per_stage": {name: {"recall": recall} for name in CLASSES}}


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
        protocol = {"seeds": seeds, "conditions": ["equal_32_per_class", "abundant_benign_1024"]}
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
        protocol = {"seeds": [1], "conditions": ["equal_32_per_class"]}
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


if __name__ == "__main__":
    unittest.main()
