import importlib.util
from pathlib import Path
import unittest
import tempfile

PATH = Path(__file__).resolve().parents[1] / "experiments/apt_final/data_audit.py"
SPEC = importlib.util.spec_from_file_location("apt_final_data_audit", PATH)
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


class DataAuditTests(unittest.TestCase):
    def test_explicit_units_and_reject_silent_unit_error(self):
        self.assertEqual(audit.epoch_seconds(1622052177000, "ms"), 1622052177)
        self.assertEqual(audit.epoch_seconds(1622052177, "s"), 1622052177)
        for value, unit in [(1622052177000, "s"), (1622052177, "ms"), (float("nan"), "s"), (1, "auto")]:
            with self.assertRaises(ValueError):
                audit.epoch_seconds(value, unit)

    def test_naive_times_remain_unresolved(self):
        self.assertEqual(audit.host_timestamp("Jun 13 00:17:01 ubuntu CRON"), (None, "no_unambiguous_absolute_time"))
        self.assertEqual(audit.host_timestamp("7/17/2021 10:23:32 PM"), (None, "no_unambiguous_absolute_time"))
        self.assertAlmostEqual(audit.host_timestamp("msg=audit(1622052177.500:7):")[0], 1622052177.5)
        self.assertEqual(audit.host_timestamp("2021-05-26T18:02:57Z")[0], 1622052177)

    def test_interval_not_point_match_and_no_arbitrary_many_to_one_choice(self):
        flow = {"id": "f", "hosts": ["h", "h"], "start": 10, "end": 100}
        events = [{"id": "e1", "host": "h", "time": 15}, {"id": "e2", "host": "h", "time": 90}]
        result = audit.interval_candidates([flow], events)
        self.assertEqual(result["candidate_pairs"], 2)
        self.assertEqual(result["flow_candidate_multiplicity"], {"multiple": 1})
        self.assertIsNone(result["validated_join_rate"])
        self.assertIsNone(result["timestamp_skew_distribution"])

    def test_duplicate_join_identifiers_fail(self):
        event = {"id": "e", "host": "h", "time": 20}
        flow = {"id": "f", "hosts": ["h"], "start": 10, "end": 30}
        with self.assertRaises(ValueError):
            audit.interval_candidates([flow], [event, event])
        with self.assertRaises(ValueError):
            audit.interval_candidates([flow, flow], [event])

    def test_negative_interval_and_tolerance_fail(self):
        with self.assertRaises(ValueError):
            audit.interval_candidates([{"id": "f", "hosts": [], "start": 30, "end": 10}], [])
        with self.assertRaises(ValueError):
            audit.interval_candidates([], [], -1)

    def test_rows_are_not_independent_groups(self):
        rows = [{"split": "confirmation", "label": 1, "group_id": "one-campaign"} for _ in range(35)]
        counts = audit.stage_group_counts(rows)["confirmation/1"]
        self.assertEqual(counts, {"rows": 35, "distinct_group_ids": 1})

    def test_hold_fail_closed_and_checks_independent(self):
        args = dict(join_verified=True, clock_verified=True, campaign_verified=False,
                    independent_stage_counts_verified=True)
        self.assertEqual(audit.hold_reasons(**args), ["CAMPAIGN_INDEPENDENCE_UNVERIFIED"])
        self.assertEqual(len(audit.hold_reasons(join_verified=False, clock_verified=False,
                                             campaign_verified=False, independent_stage_counts_verified=False)), 4)

    def test_incomplete_csv_label_is_recorded_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "network-flows"
            folder.mkdir()
            (folder / "sample.csv").write_text(
                "bidirectional_first_seen_ms,bidirectional_last_seen_ms,src_ip,dst_ip,Stage\n"
                "1622052177000,1622052178000,h1,h2\n", encoding="utf-8")
            _, summaries, flows, _ = audit.raw_samples(root, 128, 4096)
            self.assertEqual(summaries[0]["schema_or_label_failures"], 1)
            self.assertEqual(summaries[0]["sample_stage_counts"], {"undeclared_or_empty_label": 1})
            self.assertEqual(len(flows), 1)


if __name__ == "__main__":
    unittest.main()
