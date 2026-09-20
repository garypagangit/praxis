"""Synthetic checks of evidence isolation, missingness and paired perturbations."""
from copy import deepcopy
import json
import math
import unittest

from experiments.cert_gate.evidence_checker import (
    evidence_group_sha, evidence_eligible, evidence_view, has_evidence, perturb,
)
from experiments.cert_gate.feature_grouping import feature_group_sha
from experiments.cert_gate.scorers import serialize_features


class EvidenceCheckerTests(unittest.TestCase):
    def test_view_excludes_shortcuts_and_labels_without_aliasing(self):
        source = {"Label": "Attack", "attack_type": "test", "rule_name": "rule-a",
                  "host": "host-a", "sip": "10.0.0.1", "proto": "HTTP",
                  "uri": "/test", "req_header": {"Accept": ["text/plain"]}}
        before = deepcopy(source)
        view = evidence_view(source)
        self.assertEqual(set(view), {"proto", "uri", "req_header"})
        changed = {**source, "Label": "Non-Attack", "rule_name": "rule-b", "host": "host-b"}
        self.assertEqual(serialize_features(view), serialize_features(evidence_view(changed)))
        view["req_header"]["Accept"].append("application/json")
        self.assertEqual(source, before)

    def test_semantic_empty_views_do_not_qualify(self):
        empty_values = (None, "", " \t\n", "-", " NULL ", "None", "N/A", [], {},
                        {"field": [None, "-", {"nested": "n/a"}]}, "[]", '{"a":null}', False)
        for value in empty_values:
            with self.subTest(value=value):
                self.assertFalse(has_evidence({"proto": "HTTP", "method": "GET", "req_body": value}))
        self.assertTrue(has_evidence({"rsp_status": 200}))
        self.assertTrue(has_evidence({"req_body": {"nested": ["-", "observed value"]}}))
        self.assertTrue(has_evidence({"uri": "/"}))

    def test_eligibility_is_strict_and_invalid_scores_fail_closed(self):
        row = {"uri": "/test"}
        self.assertTrue(evidence_eligible(row, 0.00001))
        for margin in (0, -0.01, None, True, "0.5", math.inf, -math.inf, math.nan):
            with self.subTest(margin=margin):
                self.assertFalse(evidence_eligible(row, margin))
        self.assertFalse(evidence_eligible({"method": "GET", "req_body": "null"}, 1.0))

    def test_grouping_matches_shared_normalizer_and_cross_rule_duplicates(self):
        first = {"rule_name": "A", "host": "one", "uri": "http://10.1.2.3/test",
                 "req_body": "query=benign", "Label": "Attack"}
        second = {**first, "rule_name": "B", "host": "two", "uri": "http://10.9.8.7/test",
                  "Label": "Non-Attack"}
        self.assertEqual(evidence_group_sha(first), feature_group_sha(evidence_view(first)))
        self.assertEqual(evidence_group_sha(first), evidence_group_sha(second))
        self.assertNotEqual(evidence_group_sha(first), evidence_group_sha({**second, "req_body": "different evidence"}))

    def test_paired_notes_preserve_original_fields_and_have_equal_length(self):
        source = {"req_header": "GET /test HTTP/1.1\r\nHost: example.test",
                  "req_body": "original content", "Label": "Attack", "nested": {"a": []}}
        before = deepcopy(source)
        clean, neutral, directive = [perturb(source, mode) for mode in ("clean", "neutral", "directive")]
        self.assertEqual(clean, source)
        self.assertEqual(source, before)
        self.assertEqual(len(neutral["req_header"]), len(directive["req_header"]))
        self.assertNotEqual(neutral["req_header"], directive["req_header"])
        for row in (neutral, directive):
            self.assertTrue(row["req_header"].startswith(source["req_header"]))
            self.assertEqual({k: v for k, v in row.items() if k != "req_header"},
                             {k: v for k, v in source.items() if k != "req_header"})
        clean["nested"]["a"].append(1)
        self.assertEqual(source, before)

    def test_structured_header_conversion_and_condition_guard(self):
        source = {"req_header": {"Z": "last", "A": ["first"]}}
        row = perturb(source, "neutral")
        canonical = json.dumps(source["req_header"], sort_keys=True, ensure_ascii=False,
                               separators=(",", ":"), allow_nan=False)
        self.assertTrue(row["req_header"].startswith(canonical + "\r\nX-Research-Note: "))
        self.assertIsInstance(source["req_header"], dict)
        with self.assertRaises(ValueError):
            perturb(source, "adaptive_search")


if __name__ == "__main__":
    unittest.main()
