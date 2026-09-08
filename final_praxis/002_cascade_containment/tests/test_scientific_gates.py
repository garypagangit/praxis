"""Fixture-only decision tests, including deliberate audit corruption."""
import copy
import importlib
import unittest

BASE = "final_praxis.002_cascade_containment.harness."
common = importlib.import_module(BASE + "common")
registry = importlib.import_module(BASE + "scenario_registry")
fixtures = importlib.import_module(BASE + "generate_fixtures")
verifier = importlib.import_module(BASE + "independent_verify")
analysis = importlib.import_module(BASE + "analyze_cascade")


class ScientificGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = common.load_json(common.ROOT / "configs" / "experiment.json")
        cls.rows = []
        for case in registry.build_scenarios():
            for arm in common.ARMS:
                errors, row = verifier.verify_record(fixtures.fixture_record(case, arm), case)
                if errors: raise AssertionError(errors)
                cls.rows.append(row)

    def test_large_effect_fixture_passes_all_frozen_gates(self):
        result = analysis.analyze(self.rows, self.config)
        self.assertEqual(result["classification"], "Bounded Positive")
        self.assertTrue(all(result["gates"].values()))
        self.assertAlmostEqual(result["arms"]["A0"]["cer"], 1 / 3)

    def test_absent_phenomenon_cannot_be_positive(self):
        rows = copy.deepcopy(self.rows)
        for row in rows: row["invalid_action"] = 0; row["depth"] = 0
        result = analysis.analyze(rows, self.config)
        self.assertEqual(result["classification"], "Negative")
        self.assertFalse(result["gates"]["measurable_ungated_cascade"])

    def test_security_gain_cannot_hide_clean_utility_failure(self):
        rows = copy.deepcopy(self.rows)
        selected = [r for r in rows if r["arm"] == "A3" and r["condition"] == "clean"]
        for row in selected[:7]: row["success"] = 0
        result = analysis.analyze(rows, self.config)
        self.assertEqual(result["classification"], "Negative")
        self.assertFalse(result["gates"]["H2_clean_utility"])

    def test_handoff_claim_fails_when_only_final_action_matters(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            if row["arm"] == "A2": row["depth"] = 2 if row["condition"] == "injected" else 0
        result = analysis.analyze(rows, self.config)
        self.assertEqual(result["classification"], "Mixed")
        self.assertFalse(result["gates"]["H4_handoff_placement"])

    def test_missing_denominator_is_rejected(self):
        with self.assertRaises(ValueError): analysis.analyze(self.rows[:-1], self.config)

    def test_altered_raw_evidence_is_detected(self):
        case = registry.build_scenarios()[0]
        record = fixtures.fixture_record(case, "A0")
        record["stages"][1]["raw_response"]["text"] = '{}'
        self.assertTrue(verifier.verify_record(record, case)[0])

    def test_altered_input_evidence_is_detected(self):
        case = registry.build_scenarios()[0]
        record = fixtures.fixture_record(case, "A0")
        record["stages"][0]["messages"][1]["content"] = '{}'
        self.assertTrue(verifier.verify_record(record, case)[0])


if __name__ == "__main__": unittest.main()
