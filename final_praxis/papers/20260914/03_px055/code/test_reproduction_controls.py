"""Synthetic checks of comparison, integrity rejection and geometric primitives."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import reproduce


class Controls(unittest.TestCase):
    def test_nested_value_change_is_not_accepted(self):
        self.assertEqual(len(reproduce.compare({"x": [1, 2]}, {"x": [1, 3]})["failures"]), 1)

    def test_bool_change_is_not_accepted(self):
        self.assertTrue(reproduce.compare({"positive": False}, {"positive": True})["failures"])

    def test_nonfinite_is_not_accepted(self):
        self.assertTrue(reproduce.compare(float("nan"), 0.0)["failures"])

    def test_artifact_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = root / "sample"
            p.write_bytes(b"before")
            (root / "FILE_MANIFEST.json").write_text(json.dumps({"files": [{"path": "sample", "bytes": 6, "sha256": hashlib.sha256(b"before").hexdigest()}]}))
            self.assertEqual(reproduce.check_manifest(root), 1)
            p.write_bytes(b"change")
            with self.assertRaises(ValueError):
                reproduce.check_manifest(root)

    def test_full_cross_gram_unequal_ranks(self):
        core = reproduce.load_core()
        # A one-dimensional subspace inside a two-dimensional one has angle 0.
        a = np.asarray([[0., 1., 0.]])
        b = np.asarray([[1., 0., 0.], [0., 1., 0.]])
        self.assertAlmostEqual(core.principal_angles_degrees(a, b)[0], 0.0)

    def test_orthogonal_angle(self):
        core = reproduce.load_core()
        self.assertAlmostEqual(core.principal_angles_degrees(np.asarray([[1., 0.]]), np.asarray([[0., 1.]]))[0], 90.0)

    def test_balanced_accuracy_unequal_class_sizes(self):
        core = reproduce.load_core()
        self.assertAlmostEqual(core.balanced_accuracy([1, 0, 0, 0], [1, 1, 1, 0]), 2 / 3)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    receipt = {"scope": "Synthetic checks only; not candidate inference or another experimental replication", "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "pass": result.wasSuccessful(), "source_sha256": reproduce.sha(__file__), "reproducer_sha256": reproduce.sha(reproduce.__file__)}
    (reproduce.ROOT / "results/SYNTHETIC_CONTROLS.json").write_text(json.dumps(receipt, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
