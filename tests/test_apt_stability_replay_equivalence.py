import copy
import unittest
from experiments.apt_final.normal_stability_continuation.analysis import compare_replay as helper


def fixture():
    config = {"datasets": ["tiny"], "folds": [{"name": "A"}], "encoder_seeds": [11, 22], "bank_seeds": [31, 32],
              "strategies": {"clean": {}}, "representations": ["local_knn", "gin_knn"], "conditions": {"clean": 0, "masked": .5}}
    records = []
    for values in sorted(helper.expected_grid(config)):
        row = dict(zip(helper.IDENTITY, values))
        row.update(duplicate_of_encoder_seed=11 if row["representation"] == "local_knn" and row["encoder_seed"] != 11 else None,
                   metrics={"n": 100, "f1": .25, "recall": .5, "false_positive_rate": .01,
                            "by_node_type": {"0": {"n": 50, "false_positive_rate": .02}}})
        records.append(row)
    bindings = {field: "fixed" for field in helper.BINDINGS}
    return ({**bindings, "status": "NORMAL_PHASE_COMPLETE", "records": records},
            {**bindings, "status": "ATTACK_REPLAY_RUNNING", "records": copy.deepcopy(records[:4])},
            {**bindings, "status": "COMPLETE_FIXED_FAMILY_DEVELOPMENT", "normal_records": copy.deepcopy(records),
             "attack_records": copy.deepcopy(records)}, config)


class CompareReplay(unittest.TestCase):
    def test_complete_replay_and_reordered_records_match(self):
        normal, partial, final, config = fixture()
        final["normal_records"].reverse()
        final["elapsed_seconds"] = 98765
        final["private_artifacts"] = {"different/runtime/path": "ignored"}
        report = helper.compare(normal, partial, final, config)
        self.assertEqual(report["status"], "PASS_EXACT_REPLAY_OF_COMPLETED_RECORDS")
        self.assertEqual(report["phases"]["normal"]["exactly_equal_overlapping_records"], 16)
        self.assertEqual(report["phases"]["attack"]["new_final_records_without_attempt1_comparator"], 12)

    def test_single_nested_change_has_zero_tolerance(self):
        normal, partial, final, config = fixture()
        final["normal_records"][0]["metrics"]["by_node_type"]["0"]["false_positive_rate"] += 1e-12
        with self.assertRaises(ValueError):
            helper.compare(normal, partial, final, config)

    def test_duplicate_missing_and_unexpected_identities_fail(self):
        for kind in ("duplicate", "missing", "unexpected"):
            normal, partial, final, config = fixture()
            if kind == "duplicate": final["attack_records"].append(copy.deepcopy(final["attack_records"][0]))
            elif kind == "missing": final["attack_records"].pop()
            else: final["attack_records"][0]["bank_seed"] = 999
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                helper.compare(normal, partial, final, config)

    def test_binding_and_duplicate_marker_changes_fail(self):
        for kind in ("binding", "marker"):
            normal, partial, final, config = fixture()
            if kind == "binding": final["config_sha256"] = "different"
            else: final["normal_records"][0]["duplicate_of_encoder_seed"] = 999
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                helper.compare(normal, partial, final, config)

    def test_self_check_does_not_claim_completed_replay(self):
        normal, partial, _, config = fixture()
        report = helper.compare(normal, partial, None, config, self_check=True)
        self.assertEqual(report["status"], "SELF_CHECK_ONLY_NO_NEW_RESULT")
        self.assertEqual(report["phases"]["attack"]["candidate_records"], 4)

    def test_nonfinite_bool_and_metric_inventory_changes_fail(self):
        for value in (float("nan"), float("inf"), True):
            normal, partial, final, config = fixture()
            final["attack_records"][0]["metrics"]["recall"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                helper.compare(normal, partial, final, config)
        normal, partial, final, config = fixture()
        final["normal_records"][0]["metrics"]["extra"] = 1
        with self.assertRaises(ValueError):
            helper.compare(normal, partial, final, config)


if __name__ == "__main__":
    unittest.main()
