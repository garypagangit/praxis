"""Synthetic receipt tests only: no model, AWS, or external dependencies."""
import json
import tempfile
import unittest
from pathlib import Path
from audit_containment import audit, canonical, sha, choose_threshold, transitions


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value))


def fixture_tree(base):
    fixture = {s: [{'id': s+str(i), 'question': s+' question '+str(i),
                  'choices': {'label': list('ABCD'), 'text': ['one', 'two', 'three', 'four']}, 'answerKey': 'A'}
                 for i in range(n)] for s, n in [('calibration', 16), ('confirmation', 32)]}
    fp = base/'fixture.json'
    write(fp, fixture)
    lock = {'fixture_sha256': sha(fp.read_bytes()), 'calibration_ids': [r['id'] for r in fixture['calibration']],
            'confirmation_ids': [r['id'] for r in fixture['confirmation']], 'excluded_previous_test_ids': ['previous']}
    manifest = {'data_lock': lock, 'protocol': '006-stage2-v1', 'thresholds': [.5, 1., 1.5, 2.],
                'calibration_corruptions': ['clean', 'negate'], 'confirmation_corruptions': ['clean', 'negate', 'permute'],
                'permutation_shift': 17, 'checkpoint_settings': {'model': 'synthetic'}}
    write(base/'manifest.json', manifest)
    digest = sha(canonical(manifest))
    write(base/'environment.json', {'dtype': 'float32', 'threads': 4, 'model': manifest['checkpoint_settings'],
                                   'loading': {k: [] for k in ['missing_keys','unexpected_keys','mismatched_keys','error_msgs']}})
    write(base/'sanity.json', {'sham_abs_delta': 0., 'always_vs_permanent_abs_delta': 0.})
    # A disabled conditional is selected by the larger-threshold tie rule.
    candidates = [{'threshold': t, 'clean_correct': 16, 'corrupt_correct': 16, 'interventions': 0, 'eligible': 256}
                  for t in [.5, 1., 1.5, 2.]]
    calibration = {'manifest_sha256': digest, 'candidates': candidates, 'selected': candidates[-1],
                   'random_rate': 0., 'clean_baseline_correct': 16, 'selection_uses_confirmation': False}
    write(base/'calibration_frozen.json', calibration)
    metrics = {}
    for split in fixture:
        for row in fixture[split]:
            for corruption in (['clean','negate'] if split=='calibration' else ['clean','negate','permute']):
                policy_grid = [('none',2.),('permanent',2.)]+[('conditional',t) for t in [.5,1.,1.5,2.]] if split=='calibration' else [(p,2.) for p in ['none','permanent','conditional','random']]
                for policy, threshold in policy_grid:
                    eligible = 0 if policy=='permanent' else 2
                    scores = [{'log_likelihood': -1. if j==0 else -2., 'continuation_tokens': 1,
                               'choice_characters': len(row['choices']['text'][j]), 'token_ids': [10+j],
                               'routing_selection_counts': [60-eligible,eligible,0,0],
                               'monitor': {'eligible': eligible, 'interventions': 0, 'corrupted_selected': 0 if corruption=='clean' else eligible,
                                           'distance_sum': 0., 'effective_counts': [60-eligible,eligible,0,0]}} for j in range(4)]
                    ident = [digest,split,row['id'],corruption,policy,threshold,0.]
                    record = {'identity':ident, 'split':split, 'id':row['id'], 'corruption':corruption, 'policy':policy,
                              'threshold':threshold, 'random_rate':0., 'scores':scores,'prediction':'A','gold':'A','correct':True,
                              'eligible':4*eligible,'interventions':0,'seconds':.1}
                    write(base/'cells'/(sha(canonical(ident))+'.json'), record)
                    if split=='confirmation':
                        metrics[corruption+'/'+policy] = {'correct':32,'accuracy':1.,'interventions':0,'eligible':128*eligible}
    write(base/'summary.json', {'manifest_sha256': digest,'calibration':calibration,'candidate_forwards_this_execution':2308,
          'n':32,'metrics':metrics,'novel_method_established':False,'requires_further_confirmation':True,
          'clean_permanent_harms':0,'negation_damages_clean_correct':0,'conditional_recovers_negation_damage':0,'conditional_clean_losses':0})
    return fp


class TestAudit(unittest.TestCase):
    def test_complete_receipts_and_mutated_winner(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = fixture_tree(base)
            result = audit(base, fixture)
            self.assertEqual(result['integrity_status'], 'PASS', result['errors'])
            self.assertEqual(result['split_counts'], {'calibration':192,'confirmation':384})
            self.assertFalse(result['feasibility']['H_M1_at_least_two_damaged'])
            path = next((base/'cells').glob('*.json'))
            cell = json.loads(path.read_text())
            cell['prediction'] = 'B'
            write(path, cell)
            result = audit(base, fixture)
            self.assertEqual(result['integrity_status'], 'FAIL')
            self.assertTrue(any('raw likelihood winner' in e for e in result['errors']))
    def test_threshold_rejects_clean_harm_and_uses_ties(self):
        def candidate(t, clean, corrupt, interventions):
            return dict(threshold=t,clean_correct=clean,corrupt_correct=corrupt,interventions=interventions,eligible=100)
        rows = [candidate(.5,7,16,80), candidate(1.,8,12,40), candidate(1.5,8,12,40), candidate(2.,8,0,0)]
        self.assertEqual(choose_threshold(rows,8)['threshold'],1.5)
    def test_paired_correctness_direction(self):
        def row(correct, prediction): return {'correct':correct,'prediction':prediction}
        t = transitions([row(True,'A'),row(False,'B')],[row(False,'B'),row(True,'A')])
        self.assertEqual((t['CW'],t['WC'],t['net_correct'],t['prediction_changes']), (1,1,0,2))

if __name__ == '__main__':
    unittest.main()
