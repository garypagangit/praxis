import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from experiments.apt_benchmark.lateral_protection_experiment import run
from experiments.apt_benchmark.lateral_protection_experiment.specification import design

class RunnerIntegrationTests(unittest.TestCase):
    def test_predictions_follow_lock_and_resume_refuses_tampering(self):
        rng = np.random.default_rng(417)
        classes = np.array(['NormalTraffic', 'LateralMovement', 'InitialCompromise', 'DataExfiltration', 'Discovery', 'EstablishFoothold'])
        y = np.concatenate([np.repeat(np.arange(6), [1100,40,40,40,40,40]), np.repeat(np.arange(6), [240,40,40,40,40,40]), np.repeat(np.arange(6), 20)])
        split = np.repeat([0,1,2], [1300,440,120]); X = rng.normal(0,.3,(len(y),4)) + y[:,None] * 3
        data = {'X':X, 'y':y, 'split':split, 'classes':classes, 'feature_names':np.array(['a','b','c','d']),
                'group_sha256':np.array([f'{i:064x}' for i in range(len(y))])}
        p = design(); p['model_grids'] = {'xgboost':[{'n_estimators':3,'max_depth':2}], 'lightgbm':[{'n_estimators':3,'num_leaves':3,'min_child_samples':2}]}
        receipt = {'execution_binding':'synthetic-only'}
        with tempfile.TemporaryDirectory() as td:
            out = Path(td); lock = out / 'groups/32/20260921/SELECTION_LOCK.json'
            original = run.predict; calls = []
            def checked(*args):
                selection_X = X[run.partitions(data,p)['selection']]
                phase = 'selection' if np.array_equal(args[2],selection_X) else 'evaluation'
                if phase == 'selection': self.assertFalse(lock.exists())
                else: self.assertTrue(lock.exists())
                calls.append(phase)
                return original(*args)
            with patch.object(run, 'predict', side_effect=checked):
                run.run_group(data,p,receipt,out,{'budget':32,'seed':20260921})
            self.assertEqual(calls, ['selection']*8 + ['evaluation']*16)
            with patch.object(run, 'fit_model', side_effect=AssertionError('must not refit completed cells')):
                run.run_group(data,p,receipt,out,{'budget':32,'seed':20260921})
            model = out / 'cells/32/20260921/xgboost/natural/MODEL.joblib'
            with model.open('ab') as stream: stream.write(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                run.run_group(data,p,receipt,out,{'budget':32,'seed':20260921})

if __name__ == '__main__': unittest.main()
