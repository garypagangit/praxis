"""Hand-specified controls for the postrun checker; no candidate code runs."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import torch
from safetensors.torch import save_file
from audit_gpu_results import audit


class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        manifest = {'protocol_sha256': 'protocol', 'source_pin': 'pin',
                    'files': {'SOURCE_MANIFEST.json': 'source', 'worker.py': 'worker'}}
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps(manifest))
        self.report = {'provenance': {'protocol_sha256': 'protocol', 'source_pin': 'pin',
                                     'source_manifest_sha256': 'source', 'harness_files': {'worker.py': 'worker'}},
                       'assigned_positive': 16, 'completed_positive': 16, 'passed_positive': 16,
                       'assigned_negative': 4, 'completed_negative': 4, 'passed_negative': 4,
                       'timing_assigned': 9, 'timing_completed': 9, 'qualification_pass': True,
                       'instrumentation_complete': True, 'status': 'complete',
                       'comparisons': [], 'negative_controls': [], 'timing': []}
        self.values = {f'{s}/{kind}': torch.tensor([1.]) for s in range(2) for kind in ['loss', 'logits']}
        self.values.update({f'{s}/grad/p{i}': torch.tensor([1.]) for s in range(2) for i in range(16)})
        self.values.update({f'final/p{i}': torch.tensor([1.]) for i in range(16)})
        for q in ['none', 'nf4']:
            for seq in [12, 64]:
                save_file(self.values, str(self.root / f'reference_{q}_{seq}.safetensors'))
                self.report['negative_controls'].append({'quant': q, 'seq': seq, 'passed': True})
                for arm in ['ram', 'disk', 'staged_sync', 'staged_prefetch']:
                    path = self.root / f'{arm}_{q}_{seq}.safetensors'
                    save_file(self.values, str(path))
                    self.report['comparisons'].append({'quant': q, 'seq': seq, 'arm': arm, 'passed': True,
                        'artifact': path.name, 'artifact_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'staging': {'peak_slots': 2, 'peak_staging_bytes': 16, 'byte_bound': 16}})
        for block in range(3):
            for arm in ['disk', 'staged_sync', 'staged_prefetch']:
                self.report['timing'].append({'block': block, 'arm': arm, 'status': 'complete',
                    'samples': [{'step': i, 'warmup': i < 2, 'wall_seconds': 1.0} for i in range(5)]})

    def tearDown(self):
        self.temp.cleanup()

    def outcome(self):
        (self.root / 'GPU_QUALIFICATION.json').write_text(json.dumps(self.report))
        return audit(self.root, self.manifest)['artifact_reconciliation_pass']

    def test_complete_exact_fixture_passes(self):
        self.assertTrue(self.outcome())

    def test_duplicate_assignment_fails(self):
        self.report['comparisons'][-1] = copy.deepcopy(self.report['comparisons'][0])
        self.assertFalse(self.outcome())

    def test_claimed_pass_cannot_hide_wrong_tensor(self):
        row = self.report['comparisons'][0]
        values = dict(self.values)
        values['0/grad/p0'] = torch.tensor([2.])
        path = self.root / row['artifact']
        save_file(values, str(path))
        row['artifact_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertFalse(self.outcome())

    def test_changed_code_fails(self):
        self.report['provenance']['harness_files']['worker.py'] = 'changed'
        self.assertFalse(self.outcome())

    def test_unbounded_staging_fails(self):
        self.report['comparisons'][2]['staging']['peak_slots'] = 3
        self.assertFalse(self.outcome())

    def test_infinite_timing_fails(self):
        self.report['timing'][0]['samples'][0]['wall_seconds'] = float('inf')
        self.assertFalse(self.outcome())


if __name__ == '__main__':
    unittest.main()
