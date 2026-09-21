"""Analysis checks use synthetic saved scores only; no scientific model fits."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.tabular_batch.analyze_e1 import (
    analyze, compare_primary, file_hash, fit_support, recompute_metrics,
    validate_cv, value_hash,
)


def dump(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


def minimal_protocol():
    return {'experiment':'E1','samples_per_class':32,'n_splits':3,
            'seeds':list(range(20260921,20260931)),
            'models':['xgboost','lightgbm','tabicl_v2'],
            'model_grids':{'xgboost':[{'max_depth':2}],'lightgbm':[{'num_leaves':7}]},
            'e1_development_gate':{'high_risk_classes':['InitialCompromise','DataExfiltration'],'macro_f1_delta_min':.02,'mean_recall_delta_min':-.05},
            'e4':{'development_gate':{'candidate_to_comparator_mean_set_size_max':.9,'observed_pooled_coverage_min':.88,'observed_per_class_coverage_min':.85}}}


def fake_comparison_cell(model,seed,score,cv,coverage=1,size=1,risk_recall=1):
    stages={'InitialCompromise':{'recall':risk_recall},'DataExfiltration':{'recall':risk_recall},'NormalTraffic':{'recall':1}}
    counts=[{'class_label':n,'coverage':coverage,'count':10,'covered':round(10*coverage)} for n in stages]
    return {'model':model,'seed':seed,'inner_cv_selected_macro_f1':cv,
            'test_metrics':{'macro_f1':score,'per_stage':stages},
            'e4':{'evaluations':[{'nominal_coverage':.9,'method':'marginal','metrics':{'mean_set_size':size,'coverage':coverage,'count':30,'covered':round(30*coverage),'per_class':counts}}]}}


class AnalysisMetricsTests(unittest.TestCase):
    def test_hand_calculated_confusion_f1_auc_and_support(self):
        # Confusion [[1,1],[0,2]]; class F1s 2/3 and 4/5.
        y=np.array([0,0,1,1]);p=np.array([[.9,.1],[.4,.6],[.2,.8],[.3,.7]])
        m=recompute_metrics(y,p,['a','b'])
        self.assertEqual(m['confusion_matrix'],[[1,1],[0,2]])
        self.assertAlmostEqual(m['macro_f1'],(2/3+4/5)/2)
        self.assertEqual(m['per_stage']['a']['false_negative'],1)
        self.assertEqual(m['per_stage']['b']['false_positive'],1)
        self.assertEqual(m['per_stage']['a']['roc_auc_ovr'],1)
        self.assertEqual(m['per_stage']['a']['average_precision_ovr'],1)

    def test_invalid_probabilities_and_class_ids_are_rejected(self):
        for p,y in [(np.array([[.8,.8]]),np.array([0])),
                    (np.array([[np.nan,.2]]),np.array([0])),
                    (np.array([[1.1,-.1]]),np.array([0])),
                    (np.array([[.8,.2]]),np.array([2])),
                    (np.array([[.8,.2]]),np.array([0.]))]:
            with self.subTest(p=p,y=y),self.assertRaises(ValueError):recompute_metrics(y,p,['a','b'])

    def test_absent_true_class_does_not_acquire_a_fake_auc(self):
        m=recompute_metrics(np.array([0,0]),np.array([[.8,.2],[.7,.3]]),['a','b'])
        self.assertIsNone(m['roc_auc_ovr_macro'])
        self.assertIsNone(m['per_stage']['b']['average_precision_ovr'])
        self.assertEqual(m['per_stage']['b']['support'],0)

    def test_comparator_uses_cv_even_when_other_baseline_wins_test(self):
        protocol=minimal_protocol();cells=[]
        for seed in protocol['seeds']:
            cells.extend([fake_comparison_cell('xgboost',seed,.4,.9,size=2),
                          fake_comparison_cell('lightgbm',seed,.95,.8,size=2),
                          fake_comparison_cell('tabicl_v2',seed,.7,None)])
        result=compare_primary(cells,protocol)
        self.assertTrue(all(r['comparator_selected_on_inner_cv']=='xgboost' for r in result['per_seed']))
        self.assertAlmostEqual(result['e1']['mean_paired_macro_f1_delta']['mean'],.3)
        self.assertEqual(result['e1']['status'],'PASS')
        self.assertEqual(result['e4']['status'],'PASS')

    def test_small_sets_do_not_override_bad_stage_coverage(self):
        protocol=minimal_protocol();cells=[]
        for seed in protocol['seeds']:
            cells.extend([fake_comparison_cell('xgboost',seed,.5,.9,size=2),
                          fake_comparison_cell('lightgbm',seed,.5,.8,size=2),
                          fake_comparison_cell('tabicl_v2',seed,.8,None,coverage=.8)])
        result=compare_primary(cells,protocol)
        self.assertEqual(result['e4']['status'],'FAIL')
        self.assertFalse(result['e4']['guards']['every_class_coverage'])

    def test_recall_harm_overrides_f1_gain_and_partial_seeds_never_pass(self):
        protocol=minimal_protocol();cells=[]
        for seed in protocol['seeds']:
            cells.extend([fake_comparison_cell('xgboost',seed,.5,.9),
                          fake_comparison_cell('lightgbm',seed,.5,.8),
                          fake_comparison_cell('tabicl_v2',seed,.8,None,risk_recall=.8)])
        self.assertEqual(compare_primary(cells,protocol)['e1']['status'],'FAIL')
        self.assertEqual(compare_primary(cells[:-3],protocol)['e1']['status'],'INCOMPLETE')

    def test_cv_arithmetic_and_winner_are_checked(self):
        protocol=minimal_protocol()
        c={'model':'xgboost','inner_cv':{'candidates':[{'parameters':{'max_depth':2},'fold_macro_f1':[.6,.7,.8],'mean_macro_f1':.7}],
             'selected_candidate_index':0,'selected_parameters':{'max_depth':2},'selected_mean_macro_f1':.7,'selection_data':'selected fit support only'}}
        self.assertAlmostEqual(validate_cv(c,protocol),.7)
        c['inner_cv']['candidates'][0]['mean_macro_f1']=.9
        with self.assertRaises(ValueError):validate_cv(c,protocol)


class SavedArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name);self.data_path=self.base/'DATA.npz';self.protocol_path=self.base/'protocol.json'
        classes=np.array(['DataExfiltration','InitialCompromise'])
        split=np.array([0]*80+[1]*20+[2]*20,dtype=np.int8)
        y=np.array([0]*40+[1]*40+[0]*10+[1]*10+[0]*10+[1]*10,dtype=np.int32)
        fingerprints=np.array([value_hash(i) for i in range(len(y))])
        self.data={'X':np.arange(len(y)*2).reshape(len(y),2).astype(float),'y':y,'split':split,'group_sha256':fingerprints,'classes':classes,'feature_names':np.array(['a','b'])}
        np.savez(self.data_path,**self.data)
        dump(self.base/'MANIFEST.json',{'data_npz_sha256':file_hash(self.data_path)})
        self.protocol=minimal_protocol();self.protocol['seeds']=[20260921]
        self.protocol.update(data_npz_sha256=file_hash(self.data_path),manifest_sha256=file_hash(self.base/'MANIFEST.json'))
        dump(self.protocol_path,self.protocol)

    def make_run(self,name,model,device='cpu'):
        root=self.base/name;seed=self.protocol['seeds'][0]
        fit=fit_support(self.data,seed,32)
        support={'indices':fit.tolist(),'fingerprints':self.data['group_sha256'][fit].tolist()}
        common={'data_sha256':file_hash(self.data_path),'manifest_sha256':file_hash(self.base/'MANIFEST.json'),'protocol_sha256':file_hash(self.protocol_path),'code_sha256':{'runner.py':'frozen'}}
        execution={**common,'models':[model],'requested_device':device,'versions':{},'supports':{str(seed):support}}
        prefit={'execution':execution,'execution_binding':value_hash(execution)}
        dump(root/'PREFIT_RECEIPT.json',prefit)
        binding=value_hash({**common,'seed':seed,'support':support})
        d=root/'cells'/model/str(seed);d.mkdir(parents=True)
        cal=np.flatnonzero(self.data['split']==1);test=np.flatnonzero(self.data['split']==2)
        calp=np.eye(2)[self.data['y'][cal]]*.8+.1;testp=np.eye(2)[self.data['y'][test]]*.8+.1
        np.savez(d/'PREDICTIONS.npz',calibration_probabilities=calp,test_probabilities=testp,calibration_y=self.data['y'][cal],test_y=self.data['y'][test],calibration_indices=cal,test_indices=test,selected_fit_indices=fit,selected_fit_fingerprints=self.data['group_sha256'][fit],classes=self.data['classes'])
        cv=None
        if model in ('xgboost','lightgbm'):
            params=self.protocol['model_grids'][model][0]
            cv={'candidates':[{'parameters':params,'fold_macro_f1':[.5,.5,.5],'mean_macro_f1':.5}],'selected_candidate_index':0,'selected_parameters':params,'selected_mean_macro_f1':.5,'selection_data':'selected fit support only'}
        cell={'model':model,'seed':seed,'execution_binding':prefit['execution_binding'],'comparison_binding':binding,'common_binding':common,
              'prefit_receipt_sha256':file_hash(root/'PREFIT_RECEIPT.json'),'prediction_sha256':file_hash(d/'PREDICTIONS.npz'),
              'selected_fit_fingerprints_sha256':value_hash(support['fingerprints']),'samples_per_class':32,'selected_fit_rows':len(fit),
              'metrics':{'calibration':recompute_metrics(self.data['y'][cal],calp,self.data['classes'].tolist()),'test':recompute_metrics(self.data['y'][test],testp,self.data['classes'].tolist())},
              'inner_cv':cv,'actual_device':device,'timing_seconds':{},'versions':{}}
        dump(d/'CELL.json',cell)
        dump(d/'COMPLETE.json',{'execution_binding':prefit['execution_binding'],'comparison_binding':binding,'file_sha256':{n:file_hash(d/n) for n in ['CELL.json','PREDICTIONS.npz']}})
        return root,d

    def test_cpu_gpu_combination_recomputes_metrics_and_remains_incomplete(self):
        roots=[self.make_run('xgb','xgboost')[0],self.make_run('lgb','lightgbm')[0],self.make_run('gpu','tabicl_v2','cuda:0')[0]]
        r=analyze(self.data_path,self.protocol_path,roots)
        self.assertEqual(r['audit_status'],'PASS');self.assertEqual(r['completed_cell_count'],3)
        self.assertEqual(r['primary']['e1']['status'],'INCOMPLETE')
        self.assertEqual(r['primary']['per_seed'][0]['comparator_selected_on_inner_cv'],'xgboost')
        self.assertEqual(r['cells'][0]['test_metrics']['macro_f1'],1)

    def test_byte_tampering_is_rejected(self):
        root,d=self.make_run('one','tabicl_v2')
        with (d/'PREDICTIONS.npz').open('ab') as stream:stream.write(b'tamper')
        with self.assertRaisesRegex(ValueError,'digest mismatch'):analyze(self.data_path,self.protocol_path,[root])

    def test_rehashed_wrong_test_labels_are_rejected_against_source(self):
        root,d=self.make_run('one','tabicl_v2')
        with np.load(d/'PREDICTIONS.npz') as z:p={k:z[k] for k in z.files}
        p['test_y']=1-p['test_y'];np.savez(d/'PREDICTIONS.npz',**p)
        c=json.loads((d/'CELL.json').read_text());c['prediction_sha256']=file_hash(d/'PREDICTIONS.npz');dump(d/'CELL.json',c)
        marker=json.loads((d/'COMPLETE.json').read_text());marker['file_sha256']={n:file_hash(d/n) for n in ['CELL.json','PREDICTIONS.npz']};dump(d/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'labels differ'):analyze(self.data_path,self.protocol_path,[root])

    def test_duplicate_seed_model_root_is_rejected(self):
        root,_=self.make_run('one','tabicl_v2')
        with self.assertRaisesRegex(ValueError,'Duplicate completed'):analyze(self.data_path,self.protocol_path,[root,root])

    def test_rehashed_reported_metrics_cannot_override_predictions(self):
        root,d=self.make_run('one','tabicl_v2')
        c=json.loads((d/'CELL.json').read_text());c['metrics']['test']['macro_f1']=.2;dump(d/'CELL.json',c)
        marker=json.loads((d/'COMPLETE.json').read_text());marker['file_sha256']['CELL.json']=file_hash(d/'CELL.json');dump(d/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'macro_f1 disagrees'):analyze(self.data_path,self.protocol_path,[root])

    def test_changed_class_column_order_is_rejected(self):
        root,d=self.make_run('one','tabicl_v2')
        with np.load(d/'PREDICTIONS.npz') as z:p={k:z[k] for k in z.files}
        p['classes']=p['classes'][::-1];np.savez(d/'PREDICTIONS.npz',**p)
        c=json.loads((d/'CELL.json').read_text());c['prediction_sha256']=file_hash(d/'PREDICTIONS.npz');dump(d/'CELL.json',c)
        marker=json.loads((d/'COMPLETE.json').read_text());marker['file_sha256']={n:file_hash(d/n) for n in ['CELL.json','PREDICTIONS.npz']};dump(d/'COMPLETE.json',marker)
        with self.assertRaisesRegex(ValueError,'class order mismatch'):analyze(self.data_path,self.protocol_path,[root])

    def test_changed_prefit_receipt_and_different_protocol_are_rejected(self):
        root,_=self.make_run('one','tabicl_v2')
        p=json.loads((root/'PREFIT_RECEIPT.json').read_text());p['execution']['supports']['20260921']['indices'][0]=999
        dump(root/'PREFIT_RECEIPT.json',p)
        with self.assertRaisesRegex(ValueError,'prefit execution binding'):analyze(self.data_path,self.protocol_path,[root])


if __name__=='__main__':unittest.main()
