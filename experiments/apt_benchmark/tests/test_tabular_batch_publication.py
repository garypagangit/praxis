"""Publication boundary checks; no model fits or private artifact mutations."""
from pathlib import Path
import json
import tempfile
import unittest

from experiments.apt_benchmark.tabular_batch.publish_results import (
    check_links,completed_pilot,e3_public,full_batch_status,inspect_public,sha,value_sha,
)


class PublicationBoundaryTests(unittest.TestCase):
    def test_rejects_private_rows_and_account_fields_at_any_depth(self):
        for value in [{'nested':[{'selected_fit_indices':[1,2]}]},
                      {'nested':{'fingerprints':['a']}},
                      {'query_weights':[1,2]},
                      {'account':'000000000000'},
                      {'source':'C:/private/data.npz'},
                      {'source':'s3://private-bucket/results'},
                      {'source':'arn:aws:iam::000000000000:role/example'}]:
            with self.subTest(value=value),self.assertRaises(ValueError):inspect_public(value)

    def test_aggregate_hashes_and_counts_are_allowed(self):
        inspect_public({'indices_sha256':'a'*64,'per_stage':{'InitialCompromise':{'support':15,'recall':.8}},
                        'query_weights':'Attack rows weight 1; normal rows use the declared sampling weight.',
                        'source':'https://example.org/paper','versions':{'torch':'2.5.1+cu121'}})

    def test_e3_projection_preserves_aggregate_and_removes_private_paths(self):
        source={'protocol':{},'summary':{'screen_status':'NEGATIVE_DEVELOPMENT'},'rows':[
            {'arm':'no_correction','seed':1,'noise_rate':.2,'model_file':'models/private.json',
             'prediction_file':'predictions/private.npz','model_sha256':'a'*64,
             'prediction_sha256':'b'*64,'test':{'macro_f1':.5},'treatment_trace':[{'changed':2}]}]}
        result=e3_public(source)
        self.assertNotIn('model_file',result['rows'][0]);self.assertNotIn('prediction_file',result['rows'][0])
        self.assertEqual(result['rows'][0]['test'],source['rows'][0]['test'])
        self.assertIn('model_file',source['rows'][0])
        inspect_public(result)
        source['rows'][0]['unexpected_raw_rows']=[1,2]
        with self.assertRaisesRegex(ValueError,'Unexpected E3'):e3_public(source)

    def test_link_verifier_rejects_missing_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'REPORT.md').write_text('[receipt](PUBLICATION.json)')
            with self.assertRaisesRegex(ValueError,'Broken local'):check_links(root)
            self.assertEqual(len(check_links(root,pending=('PUBLICATION.json',))),1)
            (root/'PUBLICATION.json').write_text('{}')
            self.assertEqual(len(check_links(root)),1)

    def test_primary_pass_does_not_complete_missing_secondary_foundations(self):
        source={'primary':{'e1':{'status':'PASS'},'e4':{'status':'PASS'}},'cells':[
            {'model':model,'seed':seed} for model in ('random_forest','xgboost','lightgbm','tabicl_v2')
            for seed in range(20260921,20260931)]}
        status=full_batch_status(source)
        self.assertEqual(status['e1'],'INCOMPLETE');self.assertEqual(status['e4'],'INCOMPLETE')
        source['cells'] += [{'model':'tabpfn_2_5_synthetic','seed':seed} for seed in range(20260921,20260931)]
        self.assertTrue(full_batch_status(source)['completed'])
        self.assertEqual(full_batch_status(source)['e1'],'PASS')

    def test_completed_pilot_rejects_modified_private_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);code=root/'code';code.mkdir();run=root/'run';run.mkdir()
            def write(path,value):path.write_text(json.dumps(value),encoding='utf-8')
            write(code/'protocol.json',{'scope':'pilot'});(code/'runner.py').write_text('# fixture')
            binding={'data_npz_sha256':'a'*64,'manifest_sha256':'b'*64,
                     'protocol_sha256':sha(code/'protocol.json'),'code_sha256':{'runner.py':sha(code/'runner.py')},
                     'query_indices':[1,2],'query_fingerprints':['private1','private2']}
            write(run/'PREFIT_RECEIPT.json',{'binding':binding,'binding_sha256':value_sha(binding)})
            write(run/'AGGREGATE.json',{'input_sha256':'a'*64,'protocol_sha256':binding['protocol_sha256'],
                                     'prefit_receipt_sha256':sha(run/'PREFIT_RECEIPT.json')})
            (run/'PREDICTIONS_PRIVATE.npz').write_bytes(b'private-array')
            write(run/'COMPLETE.json',{'binding_sha256':value_sha(binding),'artifact_sha256':{
                name:sha(run/name) for name in ('PREFIT_RECEIPT.json','AGGREGATE.json','PREDICTIONS_PRIVATE.npz')}})
            aggregate,receipt,protocol,digest=completed_pilot(run,code,'protocol.json','a'*64)
            self.assertNotIn('query_indices',json.dumps(receipt));inspect_public(receipt)
            (run/'PREDICTIONS_PRIVATE.npz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact changed'):completed_pilot(run,code,'protocol.json','a'*64)


if __name__=='__main__':unittest.main()
