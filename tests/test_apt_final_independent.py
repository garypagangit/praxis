"""Independent refusal tests for scientific claims and frozen source provenance.

These tests do not train models or access cloud services.  They exercise failure
cases where a successful run would falsely imply verified scientific inputs.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[1]
CLI_PATH = REPO / "experiments" / "apt_final" / "run.py"
SPEC = importlib.util.spec_from_file_location("apt_final_cli_independent", CLI_PATH)
cli = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cli)
ENGINE_SPEC = importlib.util.spec_from_file_location("apt_final_engine_independent", CLI_PATH.with_name("engine.py"))
engine = importlib.util.module_from_spec(ENGINE_SPEC)
assert ENGINE_SPEC.loader is not None
ENGINE_SPEC.loader.exec_module(engine)


def put_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj), encoding="utf-8")


class ScientificReleaseRefusal(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.receipt = self.root / "receipt.json"

    def test_bare_pass_word_is_not_verified_readiness(self):
        # E3 has no mandatory raw-data arguments, making the no-path case vital.
        put_json(self.receipt, {"status": "PASS", "group_evidence": "claimed"})
        with self.assertRaises(ValueError):
            cli.require_e0(self.receipt)

    def test_synthetic_receipt_cannot_release_scientific_stage(self):
        put_json(self.receipt, {"status": "PASS", "scope": "SYNTHETIC_SMOKE_NOT_SCIENTIFIC_EVIDENCE",
                               "real_telemetry": False, "group_evidence": "fixture groups"})
        with self.assertRaises(ValueError):
            cli.require_e0(self.receipt)

    def test_hold_cannot_release_even_with_hash_matching_inputs(self):
        rows = self.root / "rows.jsonl"
        rows.write_text('{"id":"example"}\n', encoding="utf-8")
        put_json(self.receipt, {"status": "HOLD_DATA_CONTRACT", "real_telemetry": True,
                               "rows_sha256": cli.digest(rows), "group_evidence": "pending audit"})
        with self.assertRaises(ValueError):
            cli.require_e0(self.receipt, rows)

    def test_stale_rows_cannot_be_released_by_previous_hash(self):
        rows = self.root / "rows.jsonl"
        rows.write_text('{"id":"replaced-after-audit"}\n', encoding="utf-8")
        put_json(self.receipt, {"status": "PASS", "scope": "REAL_NORMALIZED_DATA",
                               "real_telemetry": True,
                               "rows_sha256": hashlib.sha256(b"previous bytes").hexdigest(),
                               "group_evidence": {"source": "purported audit"}})
        with self.assertRaises(ValueError):
            cli.require_e0(self.receipt, rows)


class CommittedSourceBinding(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.here = self.root / "experiments" / "apt_final"
        self.here.mkdir(parents=True)
        self.config = self.here / "development.json"
        put_json(self.config, {"scope": "DEVELOPMENT_ONLY"})
        self.code = self.here / "engine.py"
        self.code.write_text("VERSION = 1\n", encoding="utf-8")
        self.run_git("init", "-q")
        self.run_git("config", "core.autocrlf", "false")
        self.run_git("add", ".")
        self.run_git("-c", "user.name=APT test", "-c", "user.email=apt-test@example.invalid",
                     "-c", "commit.gpgsign=false", "commit", "-qm", "qualification fixture")
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(cli, "REPO", self.root).start()
        mock.patch.object(cli, "HERE", self.here).start()
        self.registration = self.root / "registration.json"
        cli.register(self.config, self.registration)

    def run_git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.root, stderr=subprocess.STDOUT)

    def test_exact_committed_sources_verify(self):
        self.assertEqual(cli.verify_registration(self.config, self.registration)["config_sha256"],
                         cli.digest(self.config))

    def test_modified_configuration_is_refused(self):
        put_json(self.config, {"scope": "DEVELOPMENT_ONLY", "unregistered_threshold": 0.2})
        with self.assertRaises(ValueError):
            cli.verify_registration(self.config, self.registration)

    def test_added_runnable_source_is_refused(self):
        (self.here / "late_policy.py").write_text("THRESHOLD = 0.2\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            cli.verify_registration(self.config, self.registration)

    def test_rewriting_receipt_hash_does_not_hide_changed_code(self):
        self.code.write_text("VERSION = 2\n", encoding="utf-8")
        receipt = json.loads(self.registration.read_text(encoding="utf-8"))
        receipt["files"][self.code.relative_to(self.root).as_posix()] = cli.digest(self.code)
        put_json(self.registration, receipt)
        with self.assertRaises(ValueError):
            cli.verify_registration(self.config, self.registration)


class EngineBoundaryRefusal(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.rows = self.root / "rows.jsonl"
        self.edges = self.root / "edges.jsonl"
        self.rows.write_text(json.dumps({"id": "sample", "group_id": "g", "split": "development",
                                         "host_id": "host", "time": 0, "label": 0,
                                         "features": [1.]}) + "\n", encoding="utf-8")
        self.edges.write_text("", encoding="utf-8")

    def test_direct_engine_does_not_accept_handmade_release(self):
        receipt = self.root / "receipt.json"
        put_json(receipt, {"status": "PASS", "rows_sha256": engine.sha256(self.rows),
                           "edges_sha256": engine.sha256(self.edges)})
        with self.assertRaises(ValueError):
            engine._authorize(self.rows, self.edges, receipt, False)

    def test_smoke_requires_explicit_synthetic_rows(self):
        with self.assertRaises(ValueError):
            engine._authorize(self.rows, self.edges, None, True)

    def test_changed_checkpoint_is_rejected_before_deserialization(self):
        checkpoint = self.root / "checkpoint.pt"
        old_hash = hashlib.sha256(b"frozen checkpoint").hexdigest()
        checkpoint.write_bytes(b"modified checkpoint")
        # Torch is not needed to verify that changed bytes cannot be loaded.
        fake_torch = mock.Mock()
        with mock.patch.dict("sys.modules", {"torch": fake_torch}):
            with self.assertRaises(ValueError):
                engine._predict_checkpoint(checkpoint, [], [], old_hash)
        fake_torch.load.assert_not_called()

    def test_prediction_mutation_breaks_stage_integrity(self):
        stage = self.root / "e2"
        stage.mkdir()
        predictions = stage / "predictions.jsonl"
        predictions.write_text('{"id":"original"}\n', encoding="utf-8")
        put_json(stage / "RESULTS.json", {"stage": "E2", "status": "SMOKE_NOT_EVIDENCE",
                                          "predictions_sha256": engine.sha256(predictions)})
        predictions.write_text('{"id":"changed"}\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            engine._bound_report(stage, "E2")

    def test_confirmation_cannot_enter_gate_fitting(self):
        # This must reject before accessing features or fitting any estimator.
        fake_numpy, fake_sklearn = mock.Mock(), mock.Mock()
        with mock.patch.dict("sys.modules", {"numpy": fake_numpy,
                                              "sklearn.linear_model": fake_sklearn}):
            with self.assertRaises(ValueError):
                engine._fit_policies([{"split": "confirmation"}], [0, 1])
        fake_sklearn.LogisticRegression.assert_not_called()

    def test_gate_stage_rejects_changed_upstream_configuration(self):
        stage = self.root / "e2"
        stage.mkdir()
        predictions = stage / "predictions.jsonl"
        predictions.write_text('{"split":"gate_train"}\n', encoding="utf-8")
        put_json(stage / "RESULTS.json", {"stage": "E2", "status": "SMOKE_NOT_EVIDENCE",
                                          "config": {"scope": "SYNTHETIC_SMOKE_NOT_SCIENTIFIC_EVIDENCE", "epochs": 3},
                                          "labels": [0, 1], "predictions_sha256": engine.sha256(predictions)})
        changed = {"scope": "SYNTHETIC_SMOKE_NOT_SCIENTIFIC_EVIDENCE", "epochs": 99}
        with mock.patch.object(engine, "_fit_policies", side_effect=AssertionError("Fit started before provenance validation")):
            with self.assertRaises(ValueError):
                engine.run_e3(changed, stage, self.root / "e3", smoke=True)

    def test_confirmation_group_cannot_reuse_a_development_group(self):
        stage = self.root / "e1"
        stage.mkdir()
        predictions = stage / "predictions.jsonl"
        predictions.write_text('{"id":"development-original"}\n', encoding="utf-8")
        put_json(stage / "RESULTS.json", {"stage": "E1", "status": "SMOKE_NOT_EVIDENCE",
                                          "config": {}, "labels": [0, 1], "seeds": [101],
                                          "development_group_ids": ["g"],
                                          "input_hashes": {"rows_sha256": "original", "edges_sha256": "original"},
                                          "predictions_sha256": engine.sha256(predictions)})
        policy = self.root / "POLICY_FREEZE.json"
        put_json(policy, {"status": "SMOKE_NOT_EVIDENCE", "config": {}, "labels": [0, 1],
                          "seeds": [101], "e1_results_sha256": engine.sha256(stage / "RESULTS.json")})
        self.rows.write_text(json.dumps({"id": "new-id-but-reused-campaign", "group_id": "g",
                                         "split": "confirmation", "host_id": "host", "time": 20,
                                         "label": 0, "features": [1.], "synthetic": True}) + "\n", encoding="utf-8")
        with mock.patch.object(engine, "_paired_replay", side_effect=AssertionError("Replay started before campaign check")):
            with self.assertRaises(ValueError):
                engine.run_e4({}, stage, policy, self.rows, self.edges, self.root / "e4", smoke=True)


if __name__ == "__main__":
    unittest.main()
