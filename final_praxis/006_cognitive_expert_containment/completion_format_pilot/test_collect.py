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
    def frozen_snapshot(self, base, state='COMPLETED'):
        """A minimal frozen bundle and terminal object inventory, without AWS."""
        here=base/'repo'/'final_praxis'/'option'/'completion_format_pilot'
        here.mkdir(parents=True)
        for name in collect.FROZEN_FILES:
            (here/name).write_text('{}',encoding='utf-8')
        collect.write(here/'data.json',{'pilot':[], 'fixture':'Unicode survives: café'})
        data_sha=collect.digest(here/'data.json')
        collect.write(here/'protocol.json',{'expected_cells':64,'data_sha256':data_sha})
        collect.write(here/'data_receipt.json',{'data_sha256':data_sha,'tokenizer_json_sha256':'b'*64})
        protocol_sha=collect.digest(here/'protocol.json')
        prereg_sha=collect.digest(here/'PREREGISTRATION.md')
        commit='1234567890'+'a'*30;run_id='fp006-format-'+commit[:10]
        prefix='code/final_praxis/006_cognitive_expert_containment/completion_format_pilot/'
        files={prefix+name:collect.digest(here/name) for name in collect.FROZEN_FILES}
        files['artifacts/tokenizer/tokenizer.json']='b'*64
        status={'run_id':run_id,'state':state,'updated_utc':'now','elapsed_seconds':1,
                'preregistration_sha256':prereg_sha}
        payloads={'bundle_manifest.json':{'commit':commit,'files':files},
                  'launch_receipt.json':{'run_id':run_id,'git_commit':commit,
                      'protocol_sha256':protocol_sha,'prereg_sha256':prereg_sha},
                  'cloud_status.json':status}
        if state=='COMPLETED':
            payloads.update({'outputs/technical.json':{'checks':{}},
                'outputs/pilot_completion.json':{'split':'pilot','complete':True,'cells':64,'protocol_sha256':protocol_sha},
                'outputs/generation_complete.json':{'status':'GENERATION_COMPLETE','cells':64,
                    'protocol_sha256':protocol_sha,'heldout_test_cells':0,'automatic_followup':False}})
            for index in range(64): payloads[f'outputs/cells/pilot-{index:02d}.json']={}
        audit={'status':'COMPLETE' if state=='COMPLETED' else 'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY',
               'validated_unique_cells':64 if state=='COMPLETED' else 0,
               'all_technical_checks':state=='COMPLETED','protocol_sha256':protocol_sha,
               'qualification':{'passed':False,'decision':collect.FAIL_DECISION}}
        return here,run_id,status,payloads,audit

    def collect_snapshot(self, base, here, run_id, status, payloads, audit):
        out=base/'download'
        objects=[{'name':name,'size':len(json.dumps(value).encode()),'etag':name}
                 for name,value in sorted(payloads.items())]
        def download(client,prefix,inventory,directory):
            for name,value in payloads.items(): collect.write(directory/name,value)
            return []
        def independent_audit(command,**kwargs):
            self.assertEqual(command[1],str(here/'audit.py'))
            self.assertIn(str(here/'data.json'),command)
            collect.write(out/'independent_audit/audit.json',audit)
            return subprocess.CompletedProcess(command,0 if audit['status']=='COMPLETE' else 2)
        with patch.object(collect,'HERE',here),patch.object(collect.boto3,'Session'), \
             patch.object(collect,'get_status',return_value=(status,'etag')), \
             patch.object(collect,'inventory',return_value=objects),patch.object(collect,'remaining_pause'), \
             patch.object(collect,'download_snapshot',side_effect=download), \
             patch.object(collect.subprocess,'run',side_effect=independent_audit) as auditor:
            result=collect.collect(run_id,out,wait=False)
            auditor.assert_called_once()
            return result

    def test_completed_64_cell_pilot_collects_without_test_marker(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);fixture=self.frozen_snapshot(base)
            self.assertNotIn('outputs/test_completion.json',fixture[3])
            result=self.collect_snapshot(base,*fixture)
            self.assertEqual(result['cloud_state'],'COMPLETED')
            self.assertTrue(result['stable_inventory_verified'])
            self.assertEqual(result['independent_audit_exitcode'],0)

    def test_stable_zero_cell_failure_collects_without_completion_or_technical_files(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);fixture=self.frozen_snapshot(base,state='FAILED')
            result=self.collect_snapshot(base,*fixture)
            self.assertEqual(result['cloud_state'],'FAILED')
            self.assertEqual(result['independent_audit_exitcode'],2)

    def test_frozen_runtime_data_and_tokenizer_hash_mismatches_fail_before_audit(self):
        names=list(collect.FROZEN_FILES)+['artifacts/tokenizer/tokenizer.json']
        for changed in names:
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as name:
                base=Path(name);here,run_id,status,payloads,audit=self.frozen_snapshot(base)
                prefix='code/final_praxis/006_cognitive_expert_containment/completion_format_pilot/'
                key=changed if changed.startswith('artifacts/') else prefix+changed
                payloads['bundle_manifest.json']['files'][key]='0'*64
                with self.assertRaises(ValueError):
                    self.collect_snapshot(base,here,run_id,status,payloads,audit)
                self.assertFalse((base/'download/independent_audit/audit.json').exists())

    def test_completion_markers_cannot_claim_test_execution_or_wrong_cohort(self):
        for mutation in ('wrong_count','wrong_protocol','automatic_followup','test_cells','test_marker'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as name:
                base=Path(name);here,run_id,status,payloads,audit=self.frozen_snapshot(base)
                marker=payloads['outputs/generation_complete.json']
                if mutation=='wrong_count': marker['cells']=63
                elif mutation=='wrong_protocol': marker['protocol_sha256']='0'*64
                elif mutation=='automatic_followup': marker['automatic_followup']=True
                elif mutation=='test_cells': marker['heldout_test_cells']=1
                else: payloads['outputs/test_completion.json']={}
                with self.assertRaises(ValueError):
                    self.collect_snapshot(base,here,run_id,status,payloads,audit)

    def test_completed_run_requires_all_64_independently_validated_cells(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);here,run_id,status,payloads,audit=self.frozen_snapshot(base)
            audit['validated_unique_cells']=63
            with self.assertRaises(collect.PendingCollection):
                self.collect_snapshot(base,here,run_id,status,payloads,audit)

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
        run_id='fp006-format-1234567890'
        status={'run_id':run_id,'state':'COMPLETED','updated_utc':'now','elapsed_seconds':1}
        with tempfile.TemporaryDirectory() as name, patch.object(collect.boto3,'Session'), \
             patch.object(collect,'get_status',return_value=(status,'etag')), \
             patch.object(collect,'inventory',side_effect=[[{'name':'a'}],[{'name':'b'}]]), \
             patch.object(collect,'remaining_pause'), patch.object(collect,'download_snapshot') as download:
            with self.assertRaises(collect.PendingCollection): collect.collect(run_id,Path(name),wait=False)
            download.assert_not_called()

    def test_output_directory_cannot_be_reused_for_another_run(self):
        with tempfile.TemporaryDirectory() as name:
            out=Path(name);collect.write(out/'collector_identity.json',{'run_id':'fp006-format-aaaaaaaaaa'})
            with self.assertRaises(ValueError),patch.object(collect.boto3,'Session') as session:
                collect.collect('fp006-format-bbbbbbbbbb',out)
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
            result={'status':'PARTIAL_OR_INVALID_DESCRIPTIVE_ONLY','validated_unique_cells':0,
                'all_technical_checks':False,'protocol_sha256':collect.digest(here/'protocol.json'),
                'qualification':{'passed':False,'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'}}
            collect.write(out/'independent_audit/audit.json',result)
            (out/'independent_audit/RESULTS.md').write_text('Failed; incomplete cohort; cannot qualify.')
            receipt={'run_id':'fp006-format-1234567890','cloud_state':'FAILED',
                'stable_inventory_verified':True,'independent_audit_exitcode':2}
            def git(*args,**kwargs):
                command=args[0]
                if command[1:]==['branch','--show-current']: return 'Final-Praxis-006-Cognitive-Expert-Containment'
                if command[1:]==['rev-parse','HEAD']: return 'a'*40
                return ''
            with patch.object(collect,'HERE',here),patch.object(collect.subprocess,'check_output',side_effect=git), \
                 patch.object(collect.subprocess,'run',return_value=subprocess.CompletedProcess(['mock-git'],0)):
                collect.publish_completion(out,receipt,deadline=time.monotonic()+10)
                published=json.loads((here/'completed/AUDIT.json').read_text(encoding='utf-8'))
                self.assertIs(published['qualification']['passed'],False)
                status=(here/'STATUS.md').read_text(encoding='utf-8')
                self.assertIn('**FAILED**',status)
                self.assertIn('**Validated cells:** 0/64',status)
                self.assertIn('not a completed experiment',status)
                for bad in [{'passed':True,'decision':'QUALIFIED_FOR_FRESH_TEST_REGISTRATION'},
                            {'passed':False,'decision':'QUALIFIED_FOR_FRESH_TEST_REGISTRATION'},
                            {'passed':0,'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'}]:
                    collect.write(out/'independent_audit/audit.json',{**result,'qualification':bad})
                    with self.assertRaises(ValueError): collect.publish_completion(out,receipt)

    def test_push_retry_preserves_existing_audit_timestamp_and_provenance(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);here=base/'repo'/'final_praxis'/'option'/'logic';here.mkdir(parents=True)
            (here/'protocol.json').write_text('{}')
            out=base/'download';(out/'independent_audit').mkdir(parents=True)
            result={'status':'COMPLETE','validated_unique_cells':64,'all_technical_checks':True,
                'protocol_sha256':collect.digest(here/'protocol.json'),'qualification':{'passed':False,'decision':'DO_NOT_ADVANCE_CURRENT_QUALIFICATION'},
                'audit_utc':'new','input_receipts':[{'file':'C:/new/data.json','sha256':'123'}]}
            collect.write(out/'independent_audit/audit.json',result)
            (out/'independent_audit/RESULTS.md').write_text('Scientific failure, complete cohort.')
            completed=here/'completed';completed.mkdir()
            old=copy.deepcopy(result);old['audit_utc']='original';old['input_receipts'][0]['file']='C:/old/data.json'
            collect.write(completed/'AUDIT.json',old)
            receipt={'run_id':'fp006-format-1234567890','cloud_state':'COMPLETED',
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

    def test_passing_publication_only_qualifies_a_new_registration(self):
        with tempfile.TemporaryDirectory() as name:
            base=Path(name);here=base/'repo'/'final_praxis'/'option'/'pilot';here.mkdir(parents=True)
            (here/'protocol.json').write_text('{}',encoding='utf-8')
            out=base/'download';(out/'independent_audit').mkdir(parents=True)
            result={'status':'COMPLETE','validated_unique_cells':64,'all_technical_checks':True,
                'protocol_sha256':collect.digest(here/'protocol.json'),
                'qualification':{'passed':True,'decision':collect.PASS_DECISION}}
            collect.write(out/'independent_audit/audit.json',result)
            (out/'independent_audit/RESULTS.md').write_text('Pilot qualification only.',encoding='utf-8')
            receipt={'run_id':'fp006-format-1234567890','cloud_state':'COMPLETED',
                     'stable_inventory_verified':True,'independent_audit_exitcode':0}
            def git(command,**kwargs):
                if command[1:]==['branch','--show-current']: return 'Final-Praxis-006-Cognitive-Expert-Containment'
                if command[1:]==['rev-parse','HEAD']: return 'a'*40
                return ''
            with patch.object(collect,'HERE',here),patch.object(collect.subprocess,'check_output',side_effect=git), \
                 patch.object(collect.subprocess,'run',return_value=subprocess.CompletedProcess(['mock-git'],0)):
                collect.publish_completion(out,receipt,deadline=time.monotonic()+10)
                status=(here/'STATUS.md').read_text(encoding='utf-8')
                self.assertIn('Completion-format pilot',status)
                self.assertIn('64/64',status)
                self.assertIn('separately preregistered fresh held-out qualification',status)
                self.assertIn('does not start it automatically',status)
                self.assertIn('two-hour stop watchdog',status)


if __name__=='__main__': unittest.main()
