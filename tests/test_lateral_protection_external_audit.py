"""Saved external-prediction audit checks with synthetic lookup outputs only."""
import contextlib
import io
import json
from pathlib import Path
import unittest

import numpy as np

from experiments.apt_benchmark.lateral_protection_experiment import audit, audit_external
from tests import test_lateral_protection_audit as fixture


class ExternalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.apt_benchmark.lateral_protection_experiment import run_external
        fixture.SavedArtifactAuditTests.setUpClass()
        cls.source = fixture.SavedArtifactAuditTests
        root = Path(cls.source.tmp.name)
        cls.target = root / "target"
        cls.target.mkdir()
        cls.data_path, cls.protocol_path, cls.out = cls.target / "DATA.npz", root / "external_protocol.json", root / "external"
        y = np.r_[np.zeros(20, dtype=np.int8), np.ones(3, dtype=np.int8)]
        X = np.column_stack([np.where(y == 0, 3, 2), np.arange(len(y)) + 1000., np.full(len(y), np.nan)])
        features = cls.source.data["feature_names"]
        np.savez_compressed(cls.data_path, X=X, y_binary=y, feature_names=features,
            group_sha256=np.array(audit_external.canonical_fingerprints(X)),
            source_row_indices=np.arange(len(y)), multiplicity=np.ones(len(y), dtype=np.int64))
        manifest = {"data_npz_sha256": audit.file_hash(cls.data_path),
            "source_scvic_npz_sha256": audit.file_hash(cls.source.data_path), "feature_names": features.tolist(),
            "rows": len(y), "class_counts": {"0_normal": 20, "1_author_lateral": 3},
            "independent_campaigns": 1, "documented_lateral_executions": 1,
            "scientific_fits": 0, "target_calibration": False}
        cls.data_path.with_name("MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        protocol = run_external.specification(cls.data_path, cls.source.out)
        cls.protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            run_external.run(cls.data_path, cls.source.out, protocol, cls.out)

    @classmethod
    def tearDownClass(cls):
        fixture.SavedArtifactAuditTests.tearDownClass()

    def check(self):
        return audit_external.audit_external(self.data_path, self.source.data_path, self.source.protocol_path,
            self.source.out, self.protocol_path, self.out)

    def test_complete_external_outputs_recompute(self):
        result = self.check()
        self.assertEqual(result["audit_status"], "PASS")
        self.assertEqual(result["run_status"], "COMPLETE_LIMITED_EXTERNAL_STRESS")
        self.assertEqual((result["benign_n"], result["lateral_n"]), (20, 3))
        self.assertEqual(set(result["metrics"]), set(audit_external.POLICIES))

    def test_rehashed_prediction_labels_are_not_trusted(self):
        path, result_path = self.out / "PREDICTIONS.npz", self.out / "RESULT.json"
        originals = {p: p.read_bytes() for p in [path, result_path]}
        try:
            with np.load(path, allow_pickle=False) as a:
                values = {k: a[k] for k in a.files}
            values["y_binary"][0] = 1
            np.savez_compressed(path, **values)
            result = audit.read_json(result_path)
            result["predictions_sha256"] = audit.file_hash(path)
            result_path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "prediction labels differ"):
                self.check()
        finally:
            for p, original in originals.items():
                p.write_bytes(original)

    def test_changed_source_threshold_is_rejected(self):
        path = self.out / "RESULT.json"
        original = path.read_bytes()
        try:
            result = audit.read_json(path)
            result["source_policies"]["candidate"]["threshold"] += .001
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric mismatch"):
                self.check()
        finally:
            path.write_bytes(original)

    def test_falsified_f1_is_rejected(self):
        path = self.out / "RESULT.json"
        original = path.read_bytes()
        try:
            result = audit.read_json(path)
            result["metrics"]["reference"]["attack_f1"] = .1234
            path.write_text(json.dumps(result), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "numeric mismatch"):
                self.check()
        finally:
            path.write_bytes(original)

    def test_rehashed_target_feature_tamper_fails_fingerprint_check(self):
        paths = [self.data_path, self.data_path.with_name("MANIFEST.json"), self.protocol_path]
        originals = {p: p.read_bytes() for p in paths}
        try:
            with np.load(self.data_path, allow_pickle=False) as a:
                data = {k: a[k] for k in a.files}
            data["X"][0, 1] += .5
            np.savez_compressed(self.data_path, **data)
            manifest = audit.read_json(paths[1])
            manifest["data_npz_sha256"] = audit.file_hash(self.data_path)
            paths[1].write_text(json.dumps(manifest), encoding="utf-8")
            protocol = audit.read_json(self.protocol_path)
            protocol["data_sha256"] = audit.file_hash(self.data_path)
            protocol["manifest_sha256"] = audit.file_hash(paths[1])
            self.protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprints do not match features"):
                self.check()
        finally:
            for p, original in originals.items():
                p.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
