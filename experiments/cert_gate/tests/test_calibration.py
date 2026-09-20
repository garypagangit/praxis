"""Synthetic qualification of the calibration mathematics and decision contract."""
import copy
import itertools
import json
import unittest

import numpy as np
from scipy.stats import beta, binom

from experiments.cert_gate.calibration import (
    CALIBRATED, KEEP_ALL, Certificate, apply_certificate, calibrate,
    gate_decision, tolerance_rank,
)


class CalibrationTests(unittest.TestCase):
    def test_minimum_attack_count_is_299(self):
        for n in (0, 100, 200, 250, 298):
            with self.subTest(n=n):
                self.assertIsNone(tolerance_rank(n))
                certificate = calibrate(np.arange(n, dtype=float))
                self.assertEqual(certificate.mode, KEEP_ALL)
                self.assertEqual(certificate.violation_bound, 0.0)
                self.assertFalse(apply_certificate(certificate, [-1e300, 1e300]).any())
        certificate = calibrate(np.arange(299, dtype=float))
        self.assertEqual(certificate.mode, CALIBRATED)
        self.assertEqual(certificate.order_rank, 299)
        self.assertEqual(certificate.allowed_exceedances, 0)
        self.assertAlmostEqual(certificate.violation_bound, 0.99 ** 299, places=14)
        self.assertGreater(0.99 ** 298, 0.05)

    def test_larger_samples_allow_exact_registered_ranks(self):
        for n, allowed in ((300, 0), (500, 1), (1000, 4), (2000, 12)):
            with self.subTest(n=n):
                certificate = calibrate(np.arange(n, dtype=float))
                self.assertEqual(certificate.order_rank, n - allowed)
                self.assertEqual(certificate.allowed_exceedances, allowed)
                self.assertEqual(certificate.observed_exceedances, allowed)
                self.assertLessEqual(binom.cdf(allowed, n, 0.01), 0.05)
                self.assertGreater(binom.cdf(allowed + 1, n, 0.01), 0.05)

    def test_strict_ties_do_not_suppress_threshold_atom(self):
        certificate = calibrate(np.full(500, 0.7))
        self.assertEqual(certificate.observed_exceedances, 0)
        np.testing.assert_array_equal(
            apply_certificate(certificate, [0.6, 0.7, np.nextafter(0.7, 1.0)]),
            [False, False, True],
        )

    def test_all_attack_units_not_only_eligible_count(self):
        scores = np.arange(500, dtype=float)
        eligible = np.zeros(500, dtype=bool)
        eligible[-2:] = True
        certificate = calibrate(scores, eligible)
        self.assertEqual(certificate.n_attack, 500)
        self.assertEqual(certificate.n_eligible_attack, 2)
        self.assertEqual(certificate.order_rank, 499)
        self.assertEqual(certificate.threshold, 498.0)
        self.assertEqual(certificate.observed_exceedances, 1)
        self.assertFalse(gate_decision(certificate, 1e100, False))

    def test_all_ineligible_negative_infinity_is_not_claimed_zero_risk(self):
        certificate = calibrate(np.zeros(500), np.zeros(500, dtype=bool))
        self.assertEqual(certificate.threshold_kind, "negative_infinity")
        self.assertEqual(certificate.violation_bound, float(binom.cdf(1, 500, 0.01)))
        self.assertGreater(certificate.violation_bound, 0.0)
        self.assertFalse(gate_decision(certificate, 0.0, False))
        self.assertTrue(gate_decision(certificate, 0.0, True))

    def test_negative_infinity_threshold_can_allow_rare_eligible_attack(self):
        eligible = np.zeros(500, dtype=bool)
        eligible[0] = True
        certificate = calibrate(np.ones(500), eligible)
        self.assertEqual(certificate.threshold_kind, "negative_infinity")
        self.assertEqual(certificate.observed_exceedances, 1)

    def test_invalid_scores_rejected_even_when_ineligible_or_keep_all(self):
        keep_all = calibrate([])
        for bad in (np.nan, np.inf, -np.inf):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calibrate([bad], [False])
                with self.assertRaises(ValueError):
                    gate_decision(keep_all, bad, False)
        for bad in ([[1.0]], ["1.0"], [True], [1 + 2j]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calibrate(bad)

    def test_eligibility_must_be_explicit_booleans_with_matching_length(self):
        for bad in ([1], ["False"], [], [[True]], [True, False]):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    calibrate([0.5], bad)
        self.assertEqual(calibrate([], []).n_attack, 0)

    def test_invalid_probability_and_count_parameters(self):
        for value in (0, 1, -0.1, 1.1, np.nan, np.inf, True, "0.01"):
            for name in ("alpha", "delta"):
                with self.subTest(name=name, value=value):
                    with self.assertRaises(ValueError):
                        tolerance_rank(500, **{name: value})
                    with self.assertRaises(ValueError):
                        calibrate([], **{name: value})
        for value in (-1, 3.0, True, "500"):
            with self.assertRaises(ValueError):
                tolerance_rank(value)

    def test_stricter_alpha_or_delta_never_relaxes_suppression(self):
        scores = np.linspace(-1, 1, 2000)
        test_scores = np.linspace(-2, 2, 401)
        primary = apply_certificate(calibrate(scores), test_scores)
        for kwargs in ({"alpha": 0.005}, {"delta": 0.01}, {"alpha": 0.00001}):
            with self.subTest(kwargs=kwargs):
                stricter = apply_certificate(calibrate(scores, **kwargs), test_scores)
                self.assertFalse(np.any(stricter & ~primary))

    def test_continuous_uniform_population_violation_matches_exact_binomial(self):
        # Under Uniform(0,1), R(t)=1-t and T_(k) has Beta(k,n+1-k) law.
        # This is a population-risk calculation, not a finite test fraction.
        for n in (299, 500, 1000, 2000):
            rank = tolerance_rank(n)
            exact_order_statistic_probability = beta.cdf(0.99, rank, n + 1 - rank)
            binomial_bound = binom.cdf(n - rank, n, 0.01)
            self.assertAlmostEqual(exact_order_statistic_probability, binomial_bound, places=13)

    def test_actual_calibration_on_fresh_uniform_samples_matches_known_risk(self):
        rng = np.random.default_rng(20260920)
        repetitions, n = 2000, 299
        violations = 0
        for _ in range(repetitions):
            certificate = calibrate(rng.uniform(size=n))
            violations += 1.0 - certificate.threshold > certificate.alpha
        expected = float(binom.cdf(0, n, 0.01))
        # Fixed five-standard-deviation software check, with independent new
        # samples each repetition; not a repeated split of a shared data pool.
        se = np.sqrt(expected * (1 - expected) / repetitions)
        self.assertLess(abs(violations / repetitions - expected), 5 * se)

    def test_exact_enumeration_with_atoms_and_ineligibility_obeys_bound(self):
        support = [(0.0, False), (0.2, True), (0.8, True)]
        probabilities = np.array([0.4, 0.35, 0.25])
        n, alpha, delta = 3, 0.5, 0.5
        failure_probability = 0.0
        for sample in itertools.product(range(3), repeat=n):
            certificate = calibrate(
                [support[i][0] for i in sample], [support[i][1] for i in sample],
                alpha=alpha, delta=delta,
            )
            risk = float(probabilities @ apply_certificate(
                certificate, [item[0] for item in support], [item[1] for item in support],
            ))
            if risk > alpha:
                failure_probability += float(np.prod(probabilities[list(sample)]))
        self.assertLessEqual(failure_probability, binom.cdf(1, n, alpha) + 1e-14)

    def test_finite_test_exceedance_is_not_calibration_failure_probability(self):
        # A perfectly valid fixed policy with R=.01 exceeds .01 empirically
        # whenever K>=3 on a 200-attack test: probability 32.33%, not <=5%.
        probability = float(binom.sf(2, 200, 0.01))
        self.assertAlmostEqual(probability, 0.3233213054643432, places=13)
        self.assertGreater(probability, 0.05)

    def test_explicit_delta_allocation_for_three_candidates(self):
        self.assertIsNone(tolerance_rank(407, delta=0.05 / 3))
        self.assertEqual(tolerance_rank(408, delta=0.05 / 3), 408)
        certificate = calibrate(np.arange(408, dtype=float), delta=0.05 / 3)
        self.assertEqual(certificate.delta, 0.05 / 3)
        self.assertEqual(certificate.to_dict()["scope"], "PER_FIXED_SCORER_AND_ELIGIBILITY")

    def test_json_round_trip_for_every_threshold_kind(self):
        certificates = [
            calibrate([]), calibrate(np.arange(299, dtype=float)),
            calibrate(np.zeros(500), np.zeros(500, dtype=bool)),
        ]
        for certificate in certificates:
            with self.subTest(kind=certificate.threshold_kind):
                encoded = json.dumps(certificate.to_dict(), allow_nan=False)
                restored = Certificate.from_dict(json.loads(encoded))
                self.assertEqual(restored, certificate)
                np.testing.assert_array_equal(
                    apply_certificate(json.loads(encoded), [-1.0, 1.0], [True, False]),
                    apply_certificate(certificate, [-1.0, 1.0], [True, False]),
                )

    def test_metadata_is_json_safe_and_detached(self):
        metadata = {"scorer_sha256": "synthetic", "nested": {"x": 1}}
        certificate = calibrate([], metadata=metadata)
        metadata["nested"]["x"] = 2
        returned = certificate.metadata
        returned["nested"]["x"] = 3
        self.assertEqual(certificate.metadata["nested"]["x"], 1)
        for invalid in ({"x": np.nan}, {"x": object()}, ["not", "an", "object"]):
            with self.assertRaises(ValueError):
                calibrate([], metadata=invalid)

    def test_inconsistent_serialized_certificates_rejected(self):
        original = calibrate(np.arange(500, dtype=float)).to_dict()
        for key, value in (
            ("order_rank", 498), ("allowed_exceedances", 2),
            ("observed_exceedances", 2), ("violation_bound", 0.0),
            ("comparison", "greater_or_equal"), ("scope", "ANY_SELECTED_SCORER"),
            ("mode", KEEP_ALL), ("n_eligible_attack", 501),
            ("threshold", {"kind": "finite", "value": float("inf")}),
            ("threshold", {"kind": "negative_infinity", "value": None}),
        ):
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(original)
                changed[key] = value
                with self.assertRaises(ValueError):
                    Certificate.from_dict(changed)

    def test_scores_and_eligibility_inputs_are_not_mutated(self):
        scores = np.arange(500, dtype=float)
        eligible = np.arange(500) % 2 == 0
        before_scores, before_eligible = scores.copy(), eligible.copy()
        certificate = calibrate(scores, eligible)
        apply_certificate(certificate, scores, eligible)
        np.testing.assert_array_equal(scores, before_scores)
        np.testing.assert_array_equal(eligible, before_eligible)

    def test_finite_threshold_rejected_when_ineligible_count_forces_negative_infinity(self):
        document = calibrate(np.arange(500, dtype=float)).to_dict()
        # Rank 499 falls among the 499 -inf ineligible scores. A finite
        # threshold is impossible, even though all other counts look valid.
        document["n_eligible_attack"] = 1
        with self.assertRaisesRegex(ValueError, "invalid finite threshold"):
            Certificate.from_dict(document)


if __name__ == "__main__":
    unittest.main()
