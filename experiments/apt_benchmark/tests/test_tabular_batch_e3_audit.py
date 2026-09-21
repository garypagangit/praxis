"""Independent E3 audit checks, including rehashed semantic tampering."""
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch.audit_e3 import audit, compare, digest, independent_metrics, independent_treatment
from experiments.apt_benchmark.tabular_batch import run_e3


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False), encoding="utf-8")


def fixture(root):
    """Produce runner-format reports on hand-specified scores; train no model."""
    prepared, output = root / "prepared", root / "run"
    prepared.mkdir()
    output.mkdir()
    protocol = json.loads(run_e3.DEFAULT_PROTOCOL.read_text(encoding="utf-8"))
    protocol.update(classes=["A", "InitialCompromise"], seeds=[20260921], fit_per_class_cap=3, boosting_rounds=20)
    protocol["model_parameters"]["num_class"] = 2
    y = np.arange(36, dtype=np.int32) % 2
    split = np.asarray([0] * 18 + [1] * 6 + [2] * 12, dtype=np.int8)
    groups = np.asarray([f"fixture-{index}" for index in range(36)], dtype="U64")
    np.savez_compressed(prepared / "DATA.npz", X=np.arange(72).reshape(36, 2), y=y,
                        split=split, group_sha256=groups, classes=np.asarray(protocol["classes"]))
    protocol["dataset_npz_sha256"] = digest(prepared / "DATA.npz")
    write(prepared / "MANIFEST.json", {"classes": protocol["classes"], "data_npz_sha256": protocol["dataset_npz_sha256"]})
    protocol_path = root / "protocol.json"
    write(protocol_path, protocol)
    receipt, _, _ = run_e3.prepare_receipt(prepared, protocol_path)
    write(output / "PRE_FIT_RECEIPT.json", receipt)
    write(output / "PROTOCOL.json", protocol)
    write(output / "RUN_STARTED.json", {"receipt_sha256": digest(output / "PRE_FIT_RECEIPT.json")})
    test_indices = np.flatnonzero(split == 2)
    probabilities = np.asarray([[0.9, 0.1] if label == 0 else [0.1, 0.9] for label in y[test_indices]])
    rows = []
    for seed in protocol["seeds"]:
        fit = run_e3.select_fit_indices(y, split, groups, 3, seed, 2)
        for rate in protocol["noise_rates"]:
            noisy, mask = run_e3.inject_symmetric_noise(y[fit], rate, 2, seed)
            for arm in protocol["arms"]:
                state = {"assigned_labels": noisy.copy(), "active": np.ones(len(fit), bool),
                         "treated": np.zeros(len(fit), bool), "ever_candidate": np.zeros(len(fit), bool)}
                key = f"{seed}_{rate}_{arm}"
                prediction_path = output / (key + ".npz")
                model_path = output / (key + ".json")
                model_path.write_text("{}", encoding="utf-8")
                np.savez_compressed(prediction_path, probabilities=probabilities, y_test=y[test_indices],
                                    test_indices=test_indices, fit_indices=fit, clean_fit_labels=y[fit],
                                    noisy_fit_labels=noisy, hidden_noise_mask=mask,
                                    assigned_fit_labels=state["assigned_labels"], active_fit_mask=state["active"],
                                    treated_fit_mask=state["treated"], candidate_fit_mask=state["ever_candidate"])
                trace = [] if arm == "no_correction" else [{"after_round": 15, "candidates": 0, "changed": 0,
                                                           "active_count": len(fit), "treated_count": 0}]
                rows.append({"seed": seed, "noise_rate": rate, "arm": arm, "fit_count": len(fit), "fit_seconds": 0.0,
                             "test": run_e3.classification_metrics(y[test_indices], probabilities, protocol["classes"]),
                             "treatment_audit": run_e3.posthoc_treatment_metrics(y[fit], noisy, state, protocol["classes"]),
                             "treatment_trace": trace, "prediction_file": prediction_path.name,
                             "prediction_sha256": digest(prediction_path), "model_file": model_path.name,
                             "model_sha256": digest(model_path)})
    result = {"protocol": protocol, "rows": rows, "summary": run_e3.summarize(rows, protocol)}
    save_result(output, result)
    return prepared, output, protocol_path, result


def save_result(output, result):
    write(output / "RESULTS.json", result)
    write(output / "SUMMARY.json", result["summary"])
    write(output / "RUN_COMPLETE.json", {"run_count": len(result["rows"]), "results_sha256": digest(output / "RESULTS.json")})


class E3AuditTests(unittest.TestCase):
    def test_manual_confusion_math_handles_unsupported_class(self):
        result = independent_metrics(np.asarray([0, 0, 1, 1]),
                                     np.asarray([[0.9, 0.1, 0], [0.4, 0.6, 0], [0.2, 0.8, 0], [0.3, 0.7, 0]]),
                                     ["a", "b", "c"])
        self.assertEqual(result["confusion_matrix"], [[1, 1, 0], [0, 2, 0], [0, 0, 0]])
        self.assertEqual(result["per_stage"]["a"]["recall"], 0.5)
        self.assertEqual(result["per_stage"]["b"]["precision"], 2 / 3)
        self.assertAlmostEqual(result["macro_f1"], ((2 / 3) + 0.8) / 3)
        self.assertIsNone(result["per_stage"]["c"]["average_precision"])

    def test_posthoc_masks_distinguish_wrong_changes_and_correct_repairs(self):
        arrays = {"clean_fit_labels": np.asarray([0, 0, 1, 1]),
                  "noisy_fit_labels": np.asarray([0, 1, 1, 0]),
                  "assigned_fit_labels": np.asarray([1, 0, 1, 0]),
                  "active_fit_mask": np.asarray([True, True, True, False]),
                  "treated_fit_mask": np.asarray([True, True, False, True]),
                  "candidate_fit_mask": np.ones(4, bool),
                  "hidden_noise_mask": np.asarray([False, True, False, True])}
        result = independent_treatment(arrays, ["a", "b"])
        self.assertEqual(result["actual_treatment"]["precision"], 2 / 3)
        self.assertEqual(result["originally_clean_removed_or_mislabeled"], 1)
        self.assertEqual(result["noisy_labels_corrected_and_retained"], 1)
        self.assertEqual(result["noisy_examples_removed"], 1)

    def test_full_fixture_and_independent_metrics_pass_without_fits(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, _ = fixture(Path(temporary))
            result = audit(prepared, output, protocol_path)
            self.assertEqual(result["audit_status"], "PASS")
            self.assertEqual(result["run_status"], "COMPLETE")
            self.assertEqual(result["audited_cells"], 6)
            self.assertEqual(result["independent_summary"]["screen_status"], "NEGATIVE_DEVELOPMENT")

    def test_rehashed_test_label_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            row = result["rows"][0]
            path = output / row["prediction_file"]
            with np.load(path) as archive:
                arrays = {key: archive[key] for key in archive.files}
            arrays["y_test"][0] = 1 - arrays["y_test"][0]
            np.savez_compressed(path, **arrays)
            row["prediction_sha256"] = digest(path)
            save_result(output, result)
            with self.assertRaisesRegex(ValueError, "Test labels differ"):
                audit(prepared, output, protocol_path)

    def test_rehashed_metric_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            result["rows"][0]["test"]["macro_f1"] = 0.5
            save_result(output, result)
            with self.assertRaisesRegex(ValueError, "macro_f1"):
                audit(prepared, output, protocol_path)

    def test_rehashed_noise_mask_and_protocol_corruption_tamper_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            row = next(row for row in result["rows"] if row["noise_rate"] == 0.2)
            path = output / row["prediction_file"]
            with np.load(path) as archive:
                arrays = {key: archive[key] for key in archive.files}
            arrays["noisy_fit_labels"] = arrays["clean_fit_labels"].copy()
            arrays["hidden_noise_mask"][:] = False
            arrays["assigned_fit_labels"] = arrays["clean_fit_labels"].copy()
            np.savez_compressed(path, **arrays)
            row["prediction_sha256"] = digest(path)
            save_result(output, result)
            with self.assertRaisesRegex(ValueError, "Injected corruption differs"):
                audit(prepared, output, protocol_path)

    def test_rehashed_gate_tamper_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            result["summary"]["screens"]["gradient_gmm_removal_adaptation"]["all_gates_pass"] = True
            save_result(output, result)
            with self.assertRaisesRegex(ValueError, "all_gates_pass"):
                audit(prepared, output, protocol_path)

    def test_model_byte_tamper_and_baseline_treatment_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            (output / result["rows"][0]["model_file"]).write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Model checksum"):
                audit(prepared, output, protocol_path)

    def test_partial_run_remains_incomplete_and_has_no_gate_verdict(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, output, protocol_path, result = fixture(Path(temporary))
            (output / "RESULTS.json").unlink()
            (output / "RUN_COMPLETE.json").unlink()
            write(output / "RESULTS.partial.json", result["rows"][:-1])
            report = audit(prepared, output, protocol_path)
            self.assertEqual(report["run_status"], "INCOMPLETE")
            self.assertEqual(len(report["missing_cells"]), 1)
            self.assertIsNone(report["independent_summary"])

    def test_comparison_rejects_boolean_counts_nonfinite_and_extra_fields(self):
        for actual, expected in ((True, 1), (float("nan"), 0.5), ({"a": 1, "b": 2}, {"a": 1})):
            with self.assertRaises(ValueError):
                compare(actual, expected)


if __name__ == "__main__":
    unittest.main()
