import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_visibility_transfer as study


class OutsideTransferTests(unittest.TestCase):
    def test_training_uses_only_other_sessions_attack_windows(self):
        sessions = [("a", "human"), ("b", "human"), ("c", "ai"), ("d", "ai")]
        attack = [{"session": s, "label": label, **{c: 0 for c in study.audit.FLOW_COLUMNS}}
                  for s, label in sessions]
        outside = [{"session": s, "label": label, **{c: 1 for c in study.audit.FLOW_COLUMNS}}
                   for s, label in sessions]
        observed = []

        def fake_fit(features, groups, labels, train, test, candidate):
            held = set(groups[test])
            self.assertEqual(len(held), 1)
            self.assertFalse(any(train[len(attack):]))
            self.assertFalse(held & set(groups[train]))
            self.assertEqual(int(test.sum()), 2)
            observed.extend(held)
            return np.full(int(test.sum()), 0.3)

        with patch.object(study.sequence, "fit_predict", side_effect=fake_fit):
            _, _, probabilities = study.transfer(attack, outside)
        self.assertEqual(set(observed), {s for s, _ in sessions})
        self.assertEqual(probabilities.tolist(), [0.3] * 8)


if __name__ == "__main__":
    unittest.main()
