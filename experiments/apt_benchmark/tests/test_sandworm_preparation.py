"""External data boundary checks; no model fits."""
import unittest
import contextlib
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
from experiments.apt_benchmark.tabular_followup.prepare_sandworm import canonical_features,unique_view
from experiments.apt_benchmark.tabular_followup import prepare_sandworm as adapter


class SandwormPreparationTests(unittest.TestCase):
    def test_fingerprints_use_source_order_and_canonical_missing_values(self):
        frame=pd.DataFrame({'b':[float('inf'),float('nan')],'a':[-0.0,0.0],'Label':['private','private']})
        x,groups,bad=canonical_features(frame,['a','b'])
        self.assertEqual(bad,2);self.assertEqual(groups[0],groups[1]);self.assertEqual(x.shape,(2,2))

    def test_conflicting_procedures_fail_closed_even_if_both_are_attacks(self):
        with self.assertRaisesRegex(ValueError,'Conflicting procedure'):
            unique_view(np.zeros((2,1)),np.asarray(['a','a']),np.asarray(['ssh_intrusion','smb_intrusion']))

    def test_sorted_unique_mapping_reconstructs_every_raw_predictor(self):
        x=np.array([[3.],[1.],[3.],[2.]])
        first,mapping=unique_view(x,np.asarray(['c','a','c','b']),np.asarray(['Normal','ssh_intrusion','Normal','Normal']))
        self.assertEqual(first.tolist(),[1,3,0]);self.assertEqual(mapping.tolist(),[2,0,2,1])
        np.testing.assert_array_equal(x[first][mapping],x)

    def test_saved_contract_loads_without_pickle_and_preserves_binary_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source';source.mkdir();features=[f'f{i}' for i in range(73)]
            frame=pd.DataFrame(np.arange(146,dtype=float).reshape(2,73),columns=features)
            frame['Label']=['Normal','ssh_intrusion'];frame['Timestamp']=['2025-02-18 11:00:00.000000']*2
            csv=root/'input.csv';frame.to_csv(csv,index=False)
            np.savez_compressed(source/'DATA.npz',feature_names=np.asarray(features),group_sha256=np.asarray(['not-a-target-row']))
            (source/'MANIFEST.json').write_text(json.dumps({'feature_columns':features}),encoding='utf-8')
            with patch.multiple(adapter,CSV_SHA=adapter.sha(csv),SOURCE_DATA_SHA=adapter.sha(source/'DATA.npz'),
                                SOURCE_MANIFEST_SHA=adapter.sha(source/'MANIFEST.json'),EXPECTED_LABEL_COUNTS={'Normal':1,'ssh_intrusion':1}):
                with contextlib.redirect_stdout(io.StringIO()):adapter.prepare(csv,source,root/'prepared')
            with np.load(root/'prepared'/'DATA.npz',allow_pickle=False) as saved:
                arrays={name:saved[name] for name in saved.files}
            self.assertTrue(all(value.dtype.kind!='O' for value in arrays.values()))
            self.assertEqual(arrays['X'].shape,(2,73))
            np.testing.assert_array_equal(arrays['y_binary'],arrays['procedure_labels']!='Normal')


if __name__=='__main__':unittest.main()
