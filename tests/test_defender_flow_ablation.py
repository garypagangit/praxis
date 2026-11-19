import sys
import unittest
from pathlib import Path

import numpy as np


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import defender_flow_ablation as audit


class FlowAblationTests(unittest.TestCase):
    def test_paired_bootstrap_is_zero_for_identical_predictions(self):
        groups = np.array([f"s{i}" for i in range(9)])
        labels = np.array([1, 1, 1, 1, 0, 0, 0, 0, 0])
        predictions = np.array([1, 0, 1, 0, 1, 0, 1, 0, 0])
        interval = audit.paired_interval(labels, groups, list(groups), predictions, predictions)
        self.assertEqual(interval, [0.0, 0.0])


if __name__ == "__main__":
    unittest.main()
