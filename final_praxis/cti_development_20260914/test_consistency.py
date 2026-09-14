"""Adversarial controls for the index checker; no experiment execution."""
import copy
import json
import unittest
from pathlib import Path
from check_consistency import audit


class EvidenceControls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((Path(__file__).parent / 'EVIDENCE_INDEX.json').read_text())

    def test_current_index(self):
        self.assertTrue(all(r['passed'] for r in audit(self.index)))

    def test_changed_correct_count_rejected(self):
        value = copy.deepcopy(self.index)
        value['comparisons'][0]['treatment_correct'] += 1
        self.assertFalse(all(r['passed'] for r in audit(value)))

    def test_failed_router_cannot_be_relabelled_pass(self):
        value = copy.deepcopy(self.index)
        value['external_status'] = 'PASS'
        self.assertFalse(all(r['passed'] for r in audit(value)))

    def test_fabricated_approval_rejected(self):
        value = copy.deepcopy(self.index)
        value['academic_approval_claimed'] = True
        self.assertFalse(all(r['passed'] for r in audit(value)))

    def test_source_hash_change_rejected(self):
        value = copy.deepcopy(self.index)
        value['comparisons'][0]['source_sha256'] = '0' * 64
        self.assertFalse(all(r['passed'] for r in audit(value)))

    def test_missing_comparison_rejected(self):
        value = copy.deepcopy(self.index)
        value['comparisons'].pop()
        self.assertFalse(all(r['passed'] for r in audit(value)))


if __name__ == '__main__':
    unittest.main()
