"""Boundary, source isolation and lost-observation checks for window features."""
import copy
import unittest

import numpy as np

from experiments.apt_benchmark.window_diagnostic.features import (
    TEXT_DIMENSIONS, assign_labels, roster_rows, stream_features, vectorizer,
)


def event(timestamp, event_id, parts, host="host-a", run="1"):
    return {"timestamp": timestamp, "event_id": event_id, "host": host, "run_id": run,
            "fragments": [{"channel": channel, "text": text} for channel, text in parts]}


def rows():
    return [{"window_id": f"w{i}", "run_id": "1", "family": "1", "split": "test",
             "start": i * 10, "end": (i + 1) * 10} for i in range(3)]


class WindowFeatureTests(unittest.TestCase):
    def assert_sparse_equal(self, left, right):
        self.assertEqual(left.shape, right.shape)
        self.assertEqual((left != right).nnz, 0)

    def test_absolute_complete_bins_preserve_empty_prefix(self):
        intervals = {"1": [{"start": 121.2, "end": 145.4, "labels": ["T1105"], "step_id": "s"}]}
        roster = roster_rows(intervals, ["1"], {"1": "test"})
        self.assertEqual([row["start"] for row in roster], list(range(10, 140, 10)))
        self.assertTrue(all("label" not in row for row in roster))
        matrix, rules, counts = stream_features(iter([]), roster)
        self.assertEqual(matrix["pooled_clean"].shape, (13, TEXT_DIMENSIONS + 8))
        self.assertEqual(matrix["pooled_clean"].nnz, 0)
        self.assertEqual(counts["source_events"], 0)
        self.assertTrue(all(row["clean_event_count"] == 0 for row in roster))
        self.assertTrue(np.all(rules["clean"] == 0))

    def test_half_open_bins_no_future_or_previous_context(self):
        source = [event(-0.1, "outside", [("SYSCALL", "outside token")]),
                  event(0, "a", [("SYSCALL", "early observed")]),
                  event(9.999, "b", [("PATH", "late observed")]),
                  event(10, "c", [("EXECVE", "curl")]),
                  event(30, "outside2", [("SYSCALL", "outside token")])]
        roster = rows()
        matrices, rules, counts = stream_features(iter(source), roster)
        self.assertEqual([row["clean_event_count"] for row in roster], [2, 1, 0])
        self.assertEqual(counts["events_outside_complete_bins"], 2)
        self.assertEqual(rules["clean"].tolist(), [0, 1, 0])
        initial, _, _ = stream_features(iter(source[:2]), rows())
        self.assert_sparse_equal(initial["first_clean"][0], matrices["first_clean"][0])
        self.assert_sparse_equal(initial["pooled_clean"][2], matrices["pooled_clean"][2])
        self.assertFalse(np.array_equal(initial["pooled_clean"][0].toarray(), matrices["pooled_clean"][0].toarray()))

    def test_labels_provenance_and_host_identity_do_not_enter_features(self):
        source = [event(1, "a", [("SYSCALL", "audit file")]),
                  event(2, "b", [("EXECVE", "wget")], host="host-b")]
        changed = copy.deepcopy(source)
        for item in changed:
            item.update(labels=["T1105"], source_step_ids=["secret-step"], target_eligible=True,
                        split="fit", family="secret-family", label_status="malicious")
            item["host"] = "renamed-" + item["host"]
            item["event_id"] = "renamed-" + item["event_id"]
            for part in item["fragments"]:
                part.update(source_member="attacker/secret", baseline_text="SECRET_LABEL", entity_keys=["privateID"])
        left, left_rules, _ = stream_features(iter(source), rows())
        right, right_rules, _ = stream_features(iter(changed), rows())
        for name in left:
            self.assert_sparse_equal(left[name], right[name])
        for name in left_rules:
            np.testing.assert_array_equal(left_rules[name], right_rules[name])

    def test_ablation_retains_invisible_first_and_does_not_replace(self):
        source = [event(1, "a", [("EXECVE", "curl"), ("PROCTITLE", "wget")]),
                  event(2, "b", [("SYSCALL", "rsync"), ("PATH", "download target")])]
        roster = rows()
        matrices, rules, _ = stream_features(iter(source), roster)
        self.assertEqual(matrices["first_command_absent"][0].nnz, 0)
        self.assertGreater(matrices["pooled_command_absent"][0].nnz, 0)
        self.assertEqual(roster[0]["clean_event_count"], 2)
        self.assertEqual(rules["clean"][0], 3)
        self.assertEqual(rules["command_absent"][0], 1)
        counts = np.expm1(matrices["pooled_command_absent"][0, TEXT_DIMENSIONS:].toarray()[0])
        np.testing.assert_allclose(counts, [1, 2, 1, 1, 0, 0, 1, 0], rtol=1e-6)

    def test_fixed_generic_markers_stripped_before_hashing(self):
        clean = [event(1, "a", [("SYSCALL", "audit file")])]
        marked = [event(1, "a", [("SYSCALL", "TECHNIQUE_MARKER audit scenario_marker file Challenge_Marker")])]
        left, left_rules, _ = stream_features(iter(clean), rows())
        right, right_rules, _ = stream_features(iter(marked), rows())
        for name in left:
            self.assert_sparse_equal(left[name], right[name])
        for name in left_rules:
            np.testing.assert_array_equal(left_rules[name], right_rules[name])

    def test_first_uses_timestamp_then_id_across_hosts(self):
        source = [event(1, "a", [("PATH", "first event")], host="z-host"),
                  event(1, "b", [("EXECVE", "curl")], host="a-host")]
        matrices, _, _ = stream_features(iter(source), rows())
        first_only, _, _ = stream_features(iter(source[:1]), rows())
        self.assert_sparse_equal(matrices["first_clean"], first_only["first_clean"])
        np.testing.assert_allclose(np.expm1(matrices["pooled_clean"][0, TEXT_DIMENSIONS + 2]), 2, rtol=1e-6)

    def test_rule_distinct_exact_lowercase_tokens(self):
        source = [event(1, "a", [("EXECVE", "CURL curl mycurl curlish /usr/bin/wget")]),
                  event(2, "b", [("PATH", "scp-file rsync sftp tftp")])]
        _, rules, _ = stream_features(iter(source), rows())
        self.assertEqual(rules["clean"][0], 6)
        self.assertEqual(rules["command_absent"][0], 4)

    def test_label_join_half_open_overlap_and_positive_precedence(self):
        roster = rows()
        intervals = {"1": [
            {"start": 0, "end": 10, "step_id": "other", "labels": ["T1059"]},
            {"start": 10, "end": 12, "step_id": "positive-a", "labels": ["T1105"]},
            {"start": 19, "end": 20, "step_id": "positive-b", "labels": ["T1105.001"]},
            {"start": 10, "end": 15, "step_id": "other-b", "labels": ["T1111"]},
        ]}
        assign_labels(roster, intervals)
        self.assertEqual([row["label"] for row in roster], [0, 1, -1])
        self.assertEqual(roster[1]["positive_source_step_ids"], ["positive-a", "positive-b"])
        self.assertEqual(roster[2]["positive_source_step_ids"], [])

    def test_pool_is_binary_presence_not_frequency_and_no_cross_event_bigrams(self):
        a = [event(1, "a", [("SYSCALL", "alpha")]), event(2, "b", [("PATH", "beta")])]
        b = a + [event(3, "c", [("PATH", "beta")])]
        left, _, _ = stream_features(iter(a), rows())
        right, _, _ = stream_features(iter(b), rows())
        self.assert_sparse_equal(left["pooled_clean"][:, :TEXT_DIMENSIONS], right["pooled_clean"][:, :TEXT_DIMENSIONS])
        hashed = vectorizer().transform(["alpha", "beta"])
        self.assertEqual(set(left["pooled_clean"][0, :TEXT_DIMENSIONS].indices), set(hashed.indices))
        self.assertAlmostEqual(float(left["pooled_clean"][0, :TEXT_DIMENSIONS].multiply(left["pooled_clean"][0, :TEXT_DIMENSIONS]).sum()), 1, places=6)

    def test_invalid_temporal_order_and_duplicates_rejected(self):
        a = event(2, "a", [("PATH", "file")])
        b = event(1, "b", [("PATH", "file")])
        with self.assertRaisesRegex(ValueError, "not ordered"):
            stream_features(iter([a, b]), rows())
        with self.assertRaisesRegex(ValueError, "duplicate"):
            stream_features(iter([a, a]), rows())


if __name__ == "__main__":
    unittest.main()
