"""Synthetic interface checks only; never load Qwen or read a real dataset."""
from dataclasses import FrozenInstanceError
import json
import unittest

import numpy as np
from sklearn.exceptions import NotFittedError

from experiments.cert_gate.scorers import (
    FittedScoreFusion, LinearSVMScorer, QwenConfig,
    parse_benignness_json, serialize_features,
)


class ScorerTests(unittest.TestCase):
    def test_labels_derived_tags_and_randomized_addresses_do_not_enter_features(self):
        alert = {"rule_name": "Fixture", "req_body": "recorded text", "rsp_status": 200}
        noisy = {**alert, "Label": "Attack", "ground_truth": 1,
                 "attack_type": "derived attack", "kill_chain_all": "derived stage",
                 "sip": "192.0.2.1", "dip": "198.51.100.1", "sport": 123, "dport": 80}
        changed = {**noisy, "Label": "Non-Attack", "attack_type": "different",
                   "kill_chain_all": "different", "sip": "203.0.113.1", "sport": 456}
        self.assertEqual(serialize_features(alert), serialize_features(noisy))
        self.assertEqual(serialize_features(alert), serialize_features(changed))
        self.assertEqual(json.loads(serialize_features(noisy)), alert)
        self.assertNotEqual(serialize_features(alert), serialize_features({**alert, "req_body": "new evidence"}))

    def test_llm_schema_accepts_only_numeric_finite_benignness(self):
        for response, expected in [('{"benignness":0}', 0.0),
                                   (' {"benignness": 0.75}\n', 0.75),
                                   ('{"benignness":1}', 1.0)]:
            with self.subTest(response=response):
                self.assertEqual(parse_benignness_json(response), expected)
        invalid = [
            '{"benignness":true}', '{"benignness":"0.8"}',
            '{"benignness":NaN}', '{"benignness":Infinity}', '{"benignness":1e400}',
            '{"benignness":-0.01}', '{"benignness":1.01}',
            '{"benignness":0.1,"benignness":0.9}',
            '{"benignness":0.5,"reason":"extra"}',
            '[{"benignness":0.5}]', 'null', '{}',
            '```json\n{"benignness":0.5}\n```', '{"benignness":0.5} trailing',
            '{"benignness":' + '9' * 400 + '}',
        ]
        for response in invalid:
            with self.subTest(response=response):
                with self.assertRaises(ValueError):
                    parse_benignness_json(response)

    def test_qwen_config_requires_immutable_revision_without_loading_weights(self):
        config = QwenConfig("Qwen/fixture-model", "a" * 40)
        self.assertTrue(config.local_files_only)
        with self.assertRaises(FrozenInstanceError):
            config.revision = "b" * 40
        for revision in [None, "", "main", "latest", "abc123"]:
            with self.subTest(revision=revision):
                with self.assertRaises(ValueError):
                    QwenConfig("Qwen/fixture-model", revision)
        for model in ["", "unversioned-local-directory", "C:/models/qwen"]:
            with self.subTest(model=model):
                with self.assertRaises(ValueError):
                    QwenConfig(model, "a" * 40)

    def test_svm_score_orientation_and_feature_blinding_on_synthetic_fit(self):
        benign = {"rule_name": "Fixture", "req_body": "approved scheduled maintenance health check"}
        attack = {"rule_name": "Fixture", "req_body": "unapproved exploit credential theft command"}
        scorer = LinearSVMScorer(seed=13)
        with self.assertRaises(NotFittedError):
            scorer.score([benign])
        before = scorer.metadata()["config_sha256"]
        scorer.fit([benign, attack] * 4, [0, 1] * 4)
        scores = scorer.score([benign, attack])
        self.assertGreater(scores[0], 0)
        self.assertLess(scores[1], 0)
        np.testing.assert_allclose(
            scorer.score([{**benign, "Label": "Attack"}, {**attack, "Label": "Non-Attack"}]),
            scores,
        )
        metadata = scorer.metadata()
        self.assertEqual(metadata["config_sha256"], before)
        self.assertEqual(len(metadata["fit_sha256"]), 64)
        self.assertEqual(scorer.pipeline.named_steps["tfidf"].ngram_range, (3, 5))

    def test_fusion_orientation_uses_precomputed_columns_and_fitting_only(self):
        columns = np.array([[2, .95], [1.5, .8], [1, .9],
                            [-2, .05], [-1.5, .2], [-1, .1]])
        labels = [0, 0, 0, 1, 1, 1]
        fusion = FittedScoreFusion(seed=13)
        with self.assertRaises(NotFittedError):
            fusion.score(columns)
        fusion.fit(columns, labels)
        scores = fusion.score([[2, .9], [-2, .1]])
        self.assertGreater(scores[0], .5)
        self.assertLess(scores[1], .5)
        self.assertTrue(np.isfinite(scores).all())
        self.assertEqual(len(fusion.metadata()["fit_sha256"]), 64)
        with self.assertRaises(ValueError):
            fusion.fit(columns, labels, split_role="calibration")
        with self.assertRaises(ValueError):
            LinearSVMScorer().fit([], [], split_role="test")

    def test_malformed_fusion_data_and_nonbinary_fit_labels_are_rejected(self):
        for data in [[[.2]], [[1, float("nan")]], [[1, 1.2]], [[1, .2, 3]]]:
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    FittedScoreFusion().fit(data, [0])
        for labels in [[0, 0], [0, 2], [0, float("nan")], ["0", "1"], [0]]:
            with self.subTest(labels=labels):
                with self.assertRaises(ValueError):
                    FittedScoreFusion().fit([[1, .8], [-1, .2]], labels)


if __name__ == "__main__":
    unittest.main()
