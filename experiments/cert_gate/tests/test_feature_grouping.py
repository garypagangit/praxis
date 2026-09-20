"""Check grouping of the identity variants detected before model fitting."""
import copy
import hashlib
import unittest

from experiments.cert_gate.feature_grouping import exact_feature_sha, feature_group_sha
from experiments.cert_gate.scorers import serialize_features


class FeatureGroupingTests(unittest.TestCase):
    def test_address_variants_group_without_changing_model_evidence(self):
        left = {"host": "192.0.2.1", "uri": "http://192.0.2.1:8080/check",
                "req_body": "callback=198.51.100.5", "method": "GET"}
        right = {"host": "203.0.113.9", "uri": "http://203.0.113.9:8080/check",
                 "req_body": "callback=192.0.2.8", "method": "GET"}
        before = copy.deepcopy(left)
        self.assertNotEqual(exact_feature_sha(left), exact_feature_sha(right))
        self.assertEqual(feature_group_sha(left), feature_group_sha(right))
        self.assertEqual(left, before)
        self.assertIn("192.0.2.1", serialize_features(left))
        self.assertEqual(exact_feature_sha(left), hashlib.sha256(
            serialize_features(left).encode("utf-8")).hexdigest())

    def test_targets_and_excluded_random_identity_fields_never_define_groups(self):
        left = {"req_body": "same evidence", "Label": "Attack", "attack_type": "a",
                "kill_chain_all": "one", "sip": "192.0.2.1", "sport": 1000}
        right = {"req_body": "same evidence", "Label": "Non-Attack", "attack_type": "b",
                 "kill_chain_all": "two", "sip": "203.0.113.1", "sport": 2000}
        self.assertEqual(exact_feature_sha(left), exact_feature_sha(right))
        self.assertEqual(feature_group_sha(left), feature_group_sha(right))

    def test_invalid_octets_and_long_numeric_sequences_are_not_masked(self):
        for text in ("256.2.3.4", "01.2.3.4", "1.2.3.4.5", "1000.2.3.4"):
            with self.subTest(text=text):
                alert = {"req_body": text}
                self.assertEqual(feature_group_sha(alert), exact_feature_sha(alert))

    def test_version_like_valid_ipv4_spelling_is_conservatively_grouped(self):
        self.assertEqual(feature_group_sha({"req_body": "version=v1.2.3.4"}),
                         feature_group_sha({"req_body": "version=v5.6.7.8"}))

    def test_non_address_evidence_and_ports_remain_distinct(self):
        base = {"uri": "http://192.0.2.1:8080/check", "method": "GET"}
        for changed in ({**base, "method": "POST"},
                        {**base, "uri": "http://203.0.113.1:8443/check"},
                        {**base, "uri": "http://203.0.113.1:8080/other"}):
            self.assertNotEqual(feature_group_sha(base), feature_group_sha(changed))


if __name__ == "__main__":
    unittest.main()
