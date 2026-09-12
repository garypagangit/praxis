"""Offline collector tests; all AWS and Git operations are mocked."""
import copy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch
import collect


class CollectorTests(unittest.TestCase):
    def test_semantic_audit_ignores_only_timestamp_and_absolute_local_prefix(self):
        a={'audit_utc':'before','qualification':{'passed':False},'input_receipts':[{'file':'C:/old/data.json','sha256':'123'}]}
        b=copy.deepcopy(a);b['audit_utc']='after';b['input_receipts'][0]['file']='/new/data.json'
        self.assertEqual(collect.semantic_audit(a),collect.semantic_audit(b))
        b['qualification']['passed']=True
        self.assertNotEqual(collect.semantic_audit(a),collect.semantic_audit(b))
        b=copy.deepcopy(a);b['input_receipts'][0]['sha256']='changed'
        self.assertNotEqual(collect.semantic_audit(a),collect.semantic_audit(b))

    def test_snapshot_download_uses_ifmatch_and_atomic_replacement(self):
        client=MagicMock()
        client.get_object.return_value={'Body':io.BytesIO(b'new-data')}
        with tempfile.TemporaryDirectory() as name:
            out=Path(name);target=out/'outputs'/'cell.json';target.parent.mkdir();target.write_bytes(b'old-data')
            item={'name':'outputs/cell.json','size':8,'etag':'frozen-etag'}
            receipts=collect.download_snapshot(client,'prefix/',[item],out)
            self.assertEqual(target.read_bytes(),b'new-data')
            self.assertEqual(client.get_object.call_args.kwargs['IfMatch'],'frozen-etag')
            self.assertEqual(receipts[0]['sha256'],collect.digest(target))
            client.get_object.return_value={'Body':io.BytesIO(b'short')}
            with self.assertRaises(collect.PendingCollection):
                collect.download_snapshot(client,'prefix/',[item],out)
            self.assertEqual(target.read_bytes(),b'new-data')

    def test_changed_terminal_inventory_retries_before_any_download(self):
        run_id='fp006-logic-1234567890'
        status={'run_id':run_id,'state':'COMPLETED','updated_utc':'now','elapsed_seconds':1}
        with tempfile.TemporaryDirectory() as name, patch.object(collect.boto3,'Session'), \
             patch.object(collect,'get_status',return_value=(status,'etag')), \
             patch.object(collect,'inventory',side_effect=[[{'name':'a'}],[{'name':'b'}]]), \
             patch.object(collect,'remaining_pause'), patch.object(collect,'download_snapshot') as download:
            with self.assertRaises(collect.PendingCollection): collect.collect(run_id,Path(name),wait=False)
            download.assert_not_called()

    def test_output_directory_cannot_be_reused_for_another_run(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name);collect.write(out/'collector_identity.json',{'run_id':'fp006-logic-aaaaaaaaaa'})
            with self.assertRaises(ValueError),patch.object(collect.boto3,'Session') as session:
                collect.collect('fp006-logic-bbbbbbbbbb',out)
            session.assert_not_called()

    def test_running_or_unstable_cloud_run_cannot_publish(self):
        with patch.object(collect.subprocess,'check_output') as git:
            for receipt in [{'cloud_state':'RUNNING','stable_inventory_verified':True},
                            {'cloud_state':'COMPLETED','stable_inventory_verified':False}]:
                with self.assertRaises(ValueError): collect.publish_completion(Path('.'),receipt)
            git.assert_not_called()

    def test_stable_failure_publishes_only_explicit_negative_incomplete_review(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);here=base/'repo'/'final_praxis'/'option'/'logic';here.mkdir(parents=True)
            (here/'protocol.json').write_text('{}')
            out=base/'download';(out/'independent_audit').mkdir(parents=True)
            result={'status':'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY','validated_unique_cells':48,
                'all_technical_checks':False,'protocol_sha256':collect.digest(here/'protocol.json'),
                'qualification':{'passed':False,'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'}}
            collect.write(out/'independent_audit/audit.json',result)
            (out/'independent_audit/RESULTS.md').write_text('Failed; incomplete cohort; cannot qualify.')
            receipt={'run_id':'fp006-logic-1234567890','cloud_state':'FAILED',
                'stable_inventory_verified':True,'independent_audit_exitcode':2}
            def git(*args,**kwargs):
                command=args[0]
                if command[1:]==['branch','--show-current']: return 'Final-Praxis-006-Cognitive-Expert-Containment'
                if command[1:]==['rev-parse','HEAD']: return 'a'*40
                return ''
            with patch.object(collect,'HERE',here),patch.object(collect.subprocess,'check_output',side_effect=git), \
                 patch.object(collect.subprocess,'run',return_value=subprocess.CompletedProcess(['mock-git'],0)):
                collect.publish_completion(out,receipt,deadline=time.monotonic()+10)
                published=json.loads((here/'completed/AUDIT.json').read_text())
                self.assertIs(published['qualification']['passed'],False)
                status=(here/'STATUS.md').read_text()
                self.assertIn('**FAILED**',status)
                self.assertIn('**Validated cells:** 48/816',status)
                self.assertIn('not a completed experiment',status)
                for bad in [{'passed':True,'decision':'PASS_USEFUL_LOGIC_PREREQUISITE_ONLY'},
                            {'passed':False,'decision':'PASS_USEFUL_LOGIC_PREREQUISITE_ONLY'},
                            {'passed':0,'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'}]:
                    collect.write(out/'independent_audit/audit.json',{**result,'qualification':bad})
                    with self.assertRaises(ValueError): collect.publish_completion(out,receipt)

    def test_push_retry_preserves_existing_audit_timestamp_and_provenance(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);here=base/'repo'/'final_praxis'/'option'/'logic';here.mkdir(parents=True)
            (here/'protocol.json').write_text('{}')
            out=base/'download';(out/'independent_audit').mkdir(parents=True)
            result={'status':'COMPLETE','validated_unique_cells':816,'all_technical_checks':True,
                'protocol_sha256':collect.digest(here/'protocol.json'),'qualification':{'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'},
                'audit_utc':'new','input_receipts':[{'file':'C:/new/data.json','sha256':'123'}]}
            collect.write(out/'independent_audit/audit.json',result)
            (out/'independent_audit/RESULTS.md').write_text('Scientific failure, complete cohort.')
            completed=here/'completed';completed.mkdir()
            old=copy.deepcopy(result);old['audit_utc']='original';old['input_receipts'][0]['file']='C:/old/data.json'
            collect.write(completed/'AUDIT.json',old)
            receipt={'run_id':'fp006-logic-1234567890','cloud_state':'COMPLETED',
                'stable_inventory_verified':True,'independent_audit_exitcode':0}
            collect.write(completed/'ARTIFACTS.json',receipt)
            old_hash=collect.digest(completed/'AUDIT.json');artifact_hash=collect.digest(completed/'ARTIFACTS.json')
            def git(*args,**kwargs):
                command=args[0]
                if command[1:]==['branch','--show-current']: return 'Final-Praxis-006-Cognitive-Expert-Containment'
                if command[1:]==['rev-parse','HEAD']: return 'a'*40
                return ''
            with patch.object(collect,'HERE',here),patch.object(collect.subprocess,'check_output',side_effect=git), \
                 patch.object(collect.subprocess,'run',return_value=subprocess.CompletedProcess(['mock-git'],0)) as mutation:
                collect.publish_completion(out,receipt,deadline=time.monotonic()+10)
                self.assertEqual(collect.digest(completed/'AUDIT.json'),old_hash)
                self.assertEqual(collect.digest(completed/'ARTIFACTS.json'),artifact_hash)
                self.assertTrue((out/'publication_receipt.json').exists())
                self.assertTrue(all(call.args[0][0]=='git' for call in mutation.call_args_list))
                changed=copy.deepcopy(result);changed['qualification']['decision']='DIFFERENT'
                collect.write(out/'independent_audit/audit.json',changed)
                with self.assertRaises(ValueError): collect.publish_completion(out,receipt)


if __name__=='__main__': unittest.main()
