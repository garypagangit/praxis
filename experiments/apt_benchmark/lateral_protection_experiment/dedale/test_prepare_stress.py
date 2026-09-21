"""Synthetic integrity tests; no scientific model or dataset outcomes."""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.apt_benchmark.lateral_protection_experiment.dedale import prepare_stress as mod


def fixture(tmp_path, corrupt_source=False, fractional_label=False):
    names = [f"feature_{i}" for i in range(73)]
    source = np.full((1, 73), 99.0)
    source_groups = mod.fingerprints(mod.canonical(source))
    if corrupt_source:
        source_groups = ["0" * 64]
    source_path = tmp_path / "SOURCE.npz"
    np.savez(source_path, X=source, feature_names=np.asarray(names), group_sha256=np.asarray(source_groups))
    rows = []
    # Duplicate normal, one lateral, conflicting normal/lateral feature group,
    # one exact source overlap, and one excluded other-stage attack.
    for value, label, stage, tactic, technique in [
        (1, 0, "benign", "", ""), (1, 0, "benign", "", ""),
        (2, 1, "lateral_movement", "TA0008", "T1210"),
        (3, 0, "benign", "", ""), (3, 1, "lateral_movement", "TA0008", "T1210"),
        (99, 0, "benign", "", ""), (4, 1, "command_and_control", "TA0011", "T1104"),
    ]:
        rows.append({**{n: value for n in names}, "label": label,
                     "attack_step": stage, "tactic": tactic, "technique": technique})
    if fractional_label:
        rows[0]["label"] = 0.5
    target = tmp_path / "TARGET.csv"
    pd.DataFrame(rows).to_csv(target, index=False)
    protocol = {
        "status": "FROZEN_BEFORE_EXTRACTION", "seed": 20260921,
        "preparation_code_sha256": mod.sha(mod.__file__),
        "source_scvic_npz_sha256": mod.sha(source_path),
        "target_day17_csv_sha256": mod.sha(target),
        "feature_names": names, "feature_mapping_scvic_to_dedale": {n: n for n in names},
        "maximum_normal_unique_groups": 100_000,
    }
    protocol_path = tmp_path / "PROTOCOL.json"
    protocol_path.write_text(json.dumps(protocol))
    return protocol_path, source_path, target, tmp_path / "prepared"


class PreparationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)

    def test_conflicts_duplicates_source_overlap_and_no_pickle(self):
        args = fixture(self.path)
        mod.prepare(*args)
        output = args[-1]
        manifest = json.loads((output / "MANIFEST.json").read_text())
        self.assertEqual(manifest["class_counts"], {"0_normal": 1, "1_author_lateral": 1})
        self.assertEqual(manifest["source_overlap_rows"], 1)
        self.assertEqual(manifest["conflicting_author_label_rows"], 2)
        self.assertEqual(manifest["retained_duplicate_excess_rows"], 1)
        with np.load(output / "DATA.npz", allow_pickle=False) as data:
            self.assertTrue(all(data[k].dtype.kind != "O" for k in data.files))
            self.assertEqual(sorted(data["multiplicity"].tolist()), [1, 2])
            self.assertEqual(mod.fingerprints(data["X"]), data["group_sha256"].tolist())
        complete = json.loads((output / "COMPLETE.json").read_text())
        self.assertEqual(complete["file_sha256"]["DATA.npz"], mod.sha(output / "DATA.npz"))

    def test_source_supplied_hashes_must_reproduce(self):
        with self.assertRaisesRegex(ValueError, "Recomputed canonical source"):
            mod.prepare(*fixture(self.path, corrupt_source=True))

    def test_fractional_labels_rejected(self):
        with self.assertRaisesRegex(ValueError, "fractional"):
            mod.prepare(*fixture(self.path, fractional_label=True))
