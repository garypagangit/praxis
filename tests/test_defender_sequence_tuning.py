import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_sequence_tuning as study


class SequenceTuningTests(unittest.TestCase):
    def test_adjacent_bins_preserve_direction_and_window_boundary(self):
        row = {f"bin_{channel}_{i}": 0 for channel in study.expanded.BIN_CHANNELS for i in range(6)}
        row["bin_security_0"] = 2
        row["bin_security_3"] = 1
        row["bin_flow_1"] = 1
        row["bin_flow_4"] = 3
        row["bin_extra_5"] = 1
        features = study.sequence_features(row)
        self.assertEqual(features["next_bin_security_to_flow"], 2)
        self.assertEqual(features["next_bin_flow_to_security"], 0)
        self.assertEqual(features["next_bin_flow_to_extra"], 1)
        self.assertEqual(features["next_bin_extra_to_security"], 0)

    def test_inner_selection_never_sees_outer_held_session(self):
        sessions = [f"s{i}" for i in range(9)]
        groups = np.array(sessions)
        labels = np.array([int(i < 4) for i in range(9)])
        X = np.zeros((9, 1))
        calls = []

        def fake_fit(_X, groups, _labels, train, test, candidate):
            calls.append((set(groups[train]), set(groups[test]), candidate[0]))
            return np.full(test.sum(), 0.3)

        with patch.object(study, "fit_predict", side_effect=fake_fit):
            fixed, tuned, selected = study.nested_predictions(X, groups, labels, sessions)
        self.assertEqual(len(fixed), 9)
        self.assertEqual(len(tuned), 9)
        self.assertTrue(all(v["candidate"] == "enhanced_depth3" for v in selected.values()))
        per_outer = 4 * 8 + 2
        self.assertEqual(len(calls), 9 * per_outer)
        for i, outer in enumerate(sessions):
            fold_calls = calls[i * per_outer:(i + 1) * per_outer]
            for train, test, _ in fold_calls[:-2]:
                self.assertEqual(len(train), 7)
                self.assertEqual(len(test), 1)
                self.assertNotIn(outer, train | test)
                self.assertFalse(train & test)
            for train, test, _ in fold_calls[-2:]:
                self.assertEqual(train, set(sessions) - {outer})
                self.assertEqual(test, {outer})

    def test_scoring_rejects_session_overlap(self):
        groups = np.array(["same", "same"])
        with self.assertRaisesRegex(ValueError, "overlap"):
            study.fit_predict(np.zeros((2, 1)), groups, np.array([0, 0]),
                              np.array([True, False]), np.array([False, True]),
                              study.CANDIDATES[0])

    def test_summary_separates_attack_false_positives_from_ai_recall(self):
        groups = np.array([f"s{i}" for i in range(9)])
        labels = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0])
        probabilities = np.array([0.8, 0.2, 0.9, 0.1, 0.6, 0.1, 0.9, 0.1, 0.1])
        result = study.summarize(labels, groups, list(groups), probabilities)
        self.assertEqual(result["ai_recall"], 0.5)
        self.assertEqual(result["human_attack_window_fpr"], 0.4)
        self.assertEqual(result["session_accuracy"], 5 / 9)


if __name__ == "__main__":
    unittest.main()
