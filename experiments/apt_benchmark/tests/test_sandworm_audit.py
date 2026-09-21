"""Numerical and tampering tests for an auditor that performs no scientific fits."""
import copy
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.metrics import average_precision_score,roc_auc_score

from experiments.apt_benchmark.tabular_followup import audit_sandworm_transfer as audit


class SandwormAuditTests(unittest.TestCase):
    def fixture(self):
        classes=np.asarray(['AttackA','NormalTraffic','AttackB'])
        source={'classes':classes,'X':np.asarray([[np.nan,1.],[2.,3.]]),'group_sha256':np.asarray(['s0','s1'])}
        target={'y_binary':np.asarray([0,1,1,0]),'procedure_labels':np.asarray(['Normal','ssh_intrusion','ssh_intrusion','Normal']),
                'group_sha256':np.asarray(['t0','t1','t2','t3']),'raw_to_unique':np.asarray([0,1,2,3,0])}
        probabilities=np.asarray([[.3,.4,.3],[.6,.2,.2],[.1,.8,.1],[.6,.2,.2]])
        saved={'source_classes':classes,'target_y_binary':target['y_binary'].copy(),'target_procedure_labels':target['procedure_labels'].copy(),
               'target_fingerprints':target['group_sha256'].copy(),'target_raw_to_unique':target['raw_to_unique'].copy(),
               'selected_fit_indices':np.asarray([0,1]),'selected_fit_fingerprints':source['group_sha256'].copy(),
               'imputer_statistics':np.asarray([2.,2.]),'target_probabilities':probabilities}
        return source,target,saved

    def test_weighted_ranking_ties_match_independent_library(self):
        y=np.asarray([0,1,1,0,0,1]);score=np.asarray([.3,.8,.8,.8,.1,.3]);weights=np.asarray([4,1,2,3,5,2])
        auc,ap=audit.ranking_metrics(y,score,weights)
        self.assertAlmostEqual(auc,roc_auc_score(y,score,sample_weight=weights),12)
        self.assertAlmostEqual(ap,average_precision_score(y,score,sample_weight=weights),12)

    def test_argmax_rule_and_raw_multiplicity_are_explicit(self):
        source,target,saved=self.fixture();weights=np.asarray([2,1,1,1])
        metrics=audit.recompute_metrics(saved['target_probabilities'],source['classes'],target,weights)
        self.assertEqual(metrics['confusion_matrix_normal_attack'],[[2,1],[1,1]])
        self.assertAlmostEqual(metrics['attack_f1'],.5);self.assertAlmostEqual(metrics['binary_macro_f1'],(2/3+.5)/2)
        self.assertEqual(metrics['per_procedure_attack_recall']['ssh_intrusion']['detected'],1)
        # Row0 has summed attack probability .6 but NormalTraffic is its largest individual class.
        self.assertEqual(metrics['false_positive'],1)

    def test_source_threshold_ties_are_not_attacks(self):
        target={'y_binary':np.asarray([0,1]),'procedure_labels':np.asarray(['Normal','ssh_intrusion'])}
        p=np.asarray([[.01,.99],[.02,.98]])
        result=audit.recompute_metrics(p,['Attack','NormalTraffic'],target,np.ones(2,dtype=int),decision_threshold=1-p[1,1])
        self.assertEqual(result['false_positive'],0);self.assertEqual(result['true_positive'],0)

    def test_malformed_probability_distribution_rejected(self):
        source,target,saved=self.fixture();bad=saved['target_probabilities'].copy();bad[0,0]+=.1
        with self.assertRaisesRegex(ValueError,'simplex'):audit.recompute_metrics(bad,source['classes'],target,np.ones(4,dtype=int))

    def test_prediction_target_relabeling_rejected(self):
        source,target,saved=self.fixture();audit.validate_prediction_arrays(saved,source,target,np.asarray([0,1]))
        saved['target_y_binary'][1]=0
        with self.assertRaisesRegex(ValueError,'target_y_binary'):audit.validate_prediction_arrays(saved,source,target,np.asarray([0,1]))

    def test_changed_support_and_target_fitted_imputer_rejected(self):
        source,target,saved=self.fixture();changed=copy.deepcopy(saved);changed['selected_fit_indices'][0]=1
        with self.assertRaisesRegex(ValueError,'selected_fit_indices'):audit.validate_prediction_arrays(changed,source,target,np.asarray([0,1]))
        saved['imputer_statistics'][0]=99
        with self.assertRaisesRegex(ValueError,'imputer'):audit.validate_prediction_arrays(saved,source,target,np.asarray([0,1]))

    def test_receipt_hash_and_reported_metric_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp);file=folder/'CELL.json';file.write_text('{}',encoding='utf-8');receipt={'CELL.json':audit.digest(file)}
            audit.verify_files(folder,receipt,['CELL.json']);file.write_text('{"tamper":true}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):audit.verify_files(folder,receipt,['CELL.json'])
        with self.assertRaisesRegex(ValueError,'numeric value'):audit.compare({'attack_f1':.9},{'attack_f1':.3})

    def test_aggregate_requires_full_roster_and_recomputes_pairs(self):
        source,target,saved=self.fixture();metric=audit.recompute_metrics(saved['target_probabilities'],source['classes'],target,np.ones(4,dtype=int))
        cells=[{'model':model,'actual_model':'xgboost' if model=='selected_gbdt' else model,'seed':1,
                'metrics':{'deduplicated_primary':metric,'raw_flow_sensitivity':metric}} for model in audit.MODELS]
        models,pairs,delta=audit.aggregate_verified(cells,[1]);self.assertEqual(delta,0);self.assertEqual(pairs[0]['attack_f1_delta'],0)
        self.assertEqual(models['tabicl_v2']['views']['deduplicated_primary']['attack_recall']['seed_count'],1)
        with self.assertRaisesRegex(ValueError,'roster'):audit.aggregate_verified(cells[:1],[1])

    def test_missing_source_calibration_keeps_primary_available(self):
        result=audit.source_threshold_diagnostic(None,None,None,None,None,None,None,None)
        self.assertEqual(result['status'],'PENDING_MATCHING_FULL_SOURCE_CALIBRATION')
        self.assertEqual(result['required_full_source_tabicl_cells'],10)

    def test_always_normal_reference_exposes_imbalance(self):
        reference=audit.always_normal_reference(2054,37)
        self.assertAlmostEqual(reference['accuracy'],2054/2091)
        self.assertAlmostEqual(reference['binary_macro_f1'],2054/4145)
        self.assertEqual(reference['attack_recall'],0)
        self.assertEqual(reference['confusion_matrix_normal_attack'],[[2054,0],[37,0]])
        self.assertAlmostEqual(reference['attack_average_precision_prevalence_reference'],37/2091)


if __name__=='__main__':unittest.main()
