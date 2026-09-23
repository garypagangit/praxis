"""Synthetic checks for the standalone public verifier."""
import unittest
import numpy as np

from experiments.praxis_next.measurement_praxis.evidence.paired_reanalysis.verify_public import (
    point_metrics, quantities, bounds, compare, make_expected_specs,
)


class PublicVerifierTests(unittest.TestCase):
    def test_error_destinations_and_manual_f1(self):
        cm=np.array([[8,1,0,0],[0,2,1,0],[1,0,0,0],[1,2,0,5]])
        result=point_metrics(cm)
        self.assertAlmostEqual(result['macro_f1'],(16/19+4/8+0+10/13)/4)
        stage=result['stages']['DataExfiltration']
        self.assertEqual(stage['attack_to_benign_count'],1)
        self.assertEqual(stage['wrong_attack_stage_count'],2)
        self.assertEqual(stage['warning_recall'],7/8)
        self.assertEqual(stage['exact_stage_recall'],5/8)

    def test_absent_stage_is_undefined_but_count_zero(self):
        cm=np.diag([4,2,0,3])
        values=quantities(cm)
        self.assertTrue(np.isnan(values['macro_f1'][0]))
        self.assertTrue(np.isnan(values['LateralMovement.warning_recall'][0]))
        self.assertEqual(values['LateralMovement.attack_to_benign_count'][0],0)
        summary=bounds([np.nan,.2,.4])
        self.assertEqual(summary['valid_replicates'],2)
        self.assertEqual(summary['undefined_replicates'],1)
        self.assertEqual(summary['status'],'SUPPORT_CONDITIONAL')

    def test_repeat_whole_capture_counts(self):
        first=np.diag([1,2,1,2]);second=np.array([[2,0,0,0],[1,0,0,0],[0,0,0,0],[1,0,0,0]])
        values=quantities(2*first+second)
        expected=point_metrics(2*first+second)
        self.assertAlmostEqual(values['macro_f1'][0],expected['macro_f1'])
        self.assertEqual(values['attack_to_benign_count'][0],2)
        self.assertAlmostEqual(values['DataExfiltration.warning_recall'][0],4/5)

    def test_missing_scope_and_changed_value_rejected(self):
        specs=make_expected_specs()
        self.assertEqual(len(specs),36)
        for got,want in [({'x':1},{'x':2}),({'x':1},{'x':1,'y':0}),([1,2],[2,1]),(True,1)]:
            with self.assertRaises(ValueError):compare(got,want)


if __name__=='__main__':unittest.main()
