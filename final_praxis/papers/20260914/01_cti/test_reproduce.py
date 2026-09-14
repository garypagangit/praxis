"""Synthetic refusal controls for the public reproduction boundary."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import reproduce as r


def cti_fixture():
    return [{"id": str(i), "condition": "vanilla", "correct": True,
             "parsed_answer": "A", "expected_output": "A", "raw_output": "Answer: A.",
             "dataset_stratum": r.cti.ATTACK_STRATUM if i < 1578 else r.cti.MISMATCH_STRATUM}
            for i in range(2500)]


def athena_fixture():
    return [{"id": str(i), "condition": c, "correct": True, "eligible": i < 998,
             "legacy_valid": True, "intended_ae_valid": True,
             "route_relationship_evidence": i < 1200, "source_type": "fixture",
             "attack_path_type": "fixture"}
            for i in range(2997) for c in r.router.POLICIES]


class ReproductionBoundaryTests(unittest.TestCase):
    def test_parser_is_actual_permissive_frozen_contract(self):
        parser = r.frozen_parser()
        self.assertEqual(parser("Answer: B."), "B")
        self.assertEqual(parser("assistant\nB"), "B")
        self.assertEqual(parser("Answer: E"), "")
        self.assertEqual(parser("There is no option here"), "")

    def test_raw_to_correctness_valid_fixture(self):
        self.assertEqual(len(r.validate_cti(cti_fixture(), ["vanilla"], r.frozen_parser())), 2500)

    def test_missing_task_refused(self):
        with self.assertRaisesRegex(ValueError, "assignment"):
            r.validate_cti(cti_fixture()[:-1], ["vanilla"], r.frozen_parser())

    def test_saved_correctness_mutation_refused(self):
        rows = cti_fixture()
        rows[72]["correct"] = False
        with self.assertRaisesRegex(ValueError, "correctness"):
            r.validate_cti(rows, ["vanilla"], r.frozen_parser())

    def test_truthy_string_is_not_boolean(self):
        rows = cti_fixture()
        rows[72]["correct"] = "false"
        with self.assertRaisesRegex(ValueError, "boolean"):
            r.validate_cti(rows, ["vanilla"], r.frozen_parser())

    def test_projection_valid_and_mutated_policy_refused(self):
        rows = athena_fixture()
        self.assertEqual(len(r.validate_derived(rows)), 2997)
        rows[2]["correct"] = False
        with self.assertRaisesRegex(ValueError, "policy selection"):
            r.validate_derived(rows)

    def test_modified_packaged_bytes_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = b"authenticated observations\n"
            (root / "rows").write_bytes(payload)
            manifest = {"artifacts": [{"file": "rows", "sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}]}
            (root / "PROVENANCE.json").write_text(json.dumps(manifest))
            self.assertEqual(r.verify_inputs(root), 1)
            (root / "rows").write_bytes(b"changed observations\n")
            with self.assertRaisesRegex(ValueError, "hash/length"):
                r.verify_inputs(root)

    def test_discordant_exact_tail_manual_value(self):
        # Two-sided binomial: 2*(choose(8,0)+choose(8,1))/2**8.
        self.assertEqual(r.common.exact_mcnemar_pvalue(7, 1), 18 / 256)


if __name__ == "__main__":
    unittest.main()
