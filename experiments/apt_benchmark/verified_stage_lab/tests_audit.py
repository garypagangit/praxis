from pathlib import Path
import copy
import json
import tempfile
import unittest

import numpy as np
import pytest

from experiments.apt_benchmark.verified_stage_lab.audit import (
    AuditError, audit_collection, compare, four_class_metrics, outcome_metrics, sha256, verify_file_map,
)
from experiments.apt_benchmark.verified_stage_lab import features
from experiments.apt_benchmark.verified_stage_lab.tests_collect import collected


def fake_flow(episode, start, end=None, src='worker_0', dst='worker_1', block=0):
    return {'episode': episode, 'block': block, 'phase': 'current', 'start_ns': start,
            'end_ns': end if end is not None else start + 10, 'src': src, 'dst': dst,
            'request_bytes': 1200, 'response_bytes': 256, 'status': 200}


def fake_event(episode, when, arrival, kind='remote_job', phase='prior', size=17):
    return {'episode': episode, 'block': 0, 'phase': phase, 'time_ns': when,
            'controllerarrival_ns': arrival, 'kind': kind, 'success': True,
            'bytes': size, 'host': 'worker_1'}


class LabAuditTests(unittest.TestCase):
    def test_both_outcomes_are_positive_without_forcing_one_stage(self):
        truth = np.array([0, 1, 2, 3])
        metrics = four_class_metrics(truth, np.eye(4))
        self.assertEqual(metrics['macro_f1'], 1)
        self.assertEqual(metrics['accuracy'], 1)
        self.assertEqual(metrics['remote']['tp'], 2)
        self.assertEqual(metrics['transfer']['tp'], 2)

    def test_missed_remote_is_visible_despite_correct_transfer(self):
        metrics = four_class_metrics(np.array([0, 1, 2, 3]), np.eye(4)[[0, 0, 2, 2]])
        self.assertEqual(metrics['remote']['fn'], 2)
        self.assertEqual(metrics['remote']['recall'], 0)
        self.assertEqual(metrics['transfer']['recall'], 1)
        self.assertEqual(metrics['accuracy'], .5)

    def test_absent_positive_has_no_invented_ranking_success(self):
        result = outcome_metrics(np.zeros((3, 2), dtype=int),
                                 np.zeros((3, 2)), np.zeros((3, 2), dtype=int))
        self.assertIsNone(result['outputs']['R']['ap'])
        self.assertIsNone(result['outputs']['R']['roc_auc'])
        self.assertEqual(result['macro_f1'], 0)

    def test_invalid_probability_rows_fail(self):
        with self.assertRaises(AuditError):
            four_class_metrics(np.array([0]), np.ones((1, 4)))
        with self.assertRaises(AuditError):
            four_class_metrics(np.array([0]), np.array([[1., 0., np.nan, 0.]]))

    def test_bound_artifact_tampering_and_escape_fail(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'run'
            root.mkdir()
            p = root / 'evidence.json'
            p.write_text('{}')
            receipt = {'evidence.json': sha256(p)}
            verify_file_map(root, receipt)
            p.write_text('{"changed":true}')
            with self.assertRaises(AuditError):
                verify_file_map(root, receipt)
            outside = Path(d) / 'outside.json'
            outside.write_text('{}')
            with self.assertRaises(AuditError):
                verify_file_map(root, {'../outside.json': sha256(outside)})

    def test_metric_mutation_or_omitted_field_fails(self):
        compare({'score': .5, 'rows': 4}, {'score': .5, 'rows': 4})
        with self.assertRaises(AuditError):
            compare({'score': .6, 'rows': 4}, {'score': .5, 'rows': 4})
        with self.assertRaises(AuditError):
            compare({'score': .5}, {'score': .5, 'rows': 4})

    def test_history_requires_strict_event_and_actual_arrival_before_start(self):
        flow = fake_flow('a', 100)
        valid = fake_event('a', 80, 99)
        excluded = [fake_event('a', 80, 100), fake_event('a', 80, 101),
                    fake_event('a', 100, 100), fake_event('a', 101, 102),
                    fake_event('a', 70, 90, phase='current')]
        alone = features.build([flow], [valid])
        with_exclusions = features.build([flow], [valid, *excluded])
        np.testing.assert_array_equal(alone['clean__history'], with_exclusions['clean__history'])
        np.testing.assert_array_equal(alone['clean__current'], with_exclusions['clean__current'])
        self.assertEqual(with_exclusions['clean__latest_arrival'].tolist(), [99])
        self.assertEqual(with_exclusions['clean__history'][0, 3], np.log1p(1))

    def test_delay_equal_to_cutoff_is_unavailable(self):
        flow = fake_flow('a', 100_000_000)
        events = [fake_event('a', 40_000_000, 50_000_000),
                  fake_event('a', 40_000_000, 49_999_999, kind='file_write')]
        d = features.build([flow], events)
        self.assertEqual(d['delay50ms__history'][0, 3], 0)
        self.assertEqual(d['delay50ms__history'][0, 6], np.log1p(1))
        self.assertEqual(d['delay50ms__latest_arrival'][0], 99_999_999)

    def test_future_append_cannot_change_earlier_feature_vectors(self):
        flows = [fake_flow('a', 100), fake_flow('b', 200, src='worker_1', dst='worker_0')]
        events = [fake_event('a', 80, 90), fake_event('b', 180, 190, kind='file_write')]
        before = features.build(flows, events)
        after = features.build([*flows, fake_flow('future', 1000, src='worker_2')],
                               [*events, fake_event('future', 950, 980)])
        for condition in features.CONDITIONS:
            first_views, appended_views = features.views(before, condition), features.views(after, condition)
            for arm in first_views:
                np.testing.assert_array_equal(first_views[arm], appended_views[arm][:len(flows)])
        np.testing.assert_array_equal(before['donor'], after['donor'][:len(flows)])

    def test_wrong_history_uses_completed_other_source_same_block_snapshot(self):
        flows = [fake_flow('a', 100, src='worker_0'),
                 fake_flow('b', 200, src='worker_1', dst='worker_0'),
                 fake_flow('same', 240, src='worker_0'),
                 fake_flow('other_block', 250, src='worker_2', block=1),
                 fake_flow('unfinished', 280, end=310, src='worker_2'),
                 fake_flow('query', 300, src='worker_0')]
        events = [fake_event('a', 80, 90, kind='authentication'),
                  fake_event('b', 180, 190, kind='remote_job'),
                  # Arrived before the new query, but after the donor's own cutoff.
                  fake_event('b', 185, 210, kind='file_write')]
        d = features.build(flows, events)
        self.assertEqual(d['donor'][-1], 1)
        np.testing.assert_array_equal(d['clean__wrong_history'][-1], d['clean__history'][1])
        self.assertEqual(d['clean__wrong_history'][-1, 6], 0)
        self.assertEqual(d['clean__wrong_history'][-1, 3], np.log1p(1))
        self.assertEqual(d['donor'][3], -1)

    def test_forbidden_truth_and_rpc_fields_do_not_enter_predictors(self):
        flows = [fake_flow('a', 100)]
        events = [fake_event('a', 80, 90)]
        plain = features.build(flows, events)
        changed_flows, changed_events = copy.deepcopy(flows), copy.deepcopy(events)
        forbidden = {'completed_mask': 3, 'requested_mask': 2, 'prior_mask': 1,
                     'mode': 'success', 'capability': 'private', 'current_nonce': 'private',
                     'receipt_relpath': 'private', 'operation': 2, 'payload_sha256': 'private'}
        changed_flows[0].update(forbidden)
        changed_events[0].update(forbidden)
        changed = features.build(changed_flows, changed_events)
        for condition in features.CONDITIONS:
            for arm, values in features.views(plain, condition).items():
                np.testing.assert_array_equal(values, features.views(changed, condition)[arm])
        self.assertTrue(set(forbidden).isdisjoint(plain['current_names']))
        self.assertTrue(set(forbidden).isdisjoint(plain['history_names']))

    def test_duration_only_changes_explicit_timing_diagnostic(self):
        flows = [fake_flow('a', 100)]
        events = [fake_event('a', 80, 90)]
        plain = features.build(flows, events)
        altered = features.build([fake_flow('a', 100, end=10_000_000)], events)
        for condition in features.CONDITIONS:
            one, two = features.views(plain, condition), features.views(altered, condition)
            for arm in one:
                if arm == 'timing_diagnostic':
                    self.assertFalse(np.array_equal(one[arm], two[arm]))
                else:
                    np.testing.assert_array_equal(one[arm], two[arm])

    def test_role_permutation_changes_only_known_metadata(self):
        d = features.build([fake_flow('a', 100)], [fake_event('a', 80, 90)])
        for suffix in ['current', 'history', 'wrong_history', 'latest_arrival']:
            np.testing.assert_array_equal(d['clean__' + suffix], d['role_permutation__' + suffix])
        self.assertFalse(np.array_equal(d['clean__roles'], d['role_permutation__roles']))


def test_independent_audit_accepts_actual_bounded_collection(collected):
    root, _ = collected
    receipt, joined = audit_collection(root)
    assert receipt['audit_status'] == 'PASS'
    assert receipt['executions'] == 48
    assert receipt['unique_nonces'] == 96
    assert len(joined) == 48
    assert receipt['completed_mask_counts'] == {'0': 36, '1': 4, '2': 4, '3': 4}


def test_rehashed_false_completion_label_is_rejected(collected):
    root, _ = collected
    paths = [root / name for name in ['TRUTH.jsonl', 'COLLECT_RECEIPT.json', 'COMPLETE.json']]
    original = {p: p.read_bytes() for p in paths}
    try:
        rows = [json.loads(s) for s in paths[0].read_text().splitlines()]
        row = next(r for r in rows if r['completed_mask'] == 3)
        row['completed_mask'] = 0
        paths[0].write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        receipt = json.loads(paths[1].read_text())
        receipt['artifact_hashes']['TRUTH.jsonl'] = sha256(paths[0])
        receipt['completed_mask_counts']['3'] -= 1
        receipt['completed_mask_counts']['0'] += 1
        paths[1].write_text(json.dumps(receipt), encoding='utf-8')
        complete = json.loads(paths[2].read_text())
        complete['receipt_sha256'] = sha256(paths[1])
        paths[2].write_text(json.dumps(complete), encoding='utf-8')
        with pytest.raises(AuditError, match='independently verified completion'):
            audit_collection(root)
    finally:
        for path, content in original.items():
            path.write_bytes(content)


def test_rehashed_late_prior_arrival_is_rejected(collected):
    root, _ = collected
    paths = [root / name for name in ['TELEMETRY.jsonl', 'COLLECT_RECEIPT.json', 'COMPLETE.json']]
    original = {p: p.read_bytes() for p in paths}
    try:
        rows = [json.loads(s) for s in paths[0].read_text().splitlines()]
        event = next(r for r in rows if r['phase'] == 'prior')
        flows = [json.loads(s) for s in (root / 'FLOW.jsonl').read_text().splitlines()]
        current = next(f for f in flows if f['episode'] == event['episode'] and f['phase'] == 'current')
        event['controllerarrival_ns'] = current['start_ns']
        paths[0].write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        receipt = json.loads(paths[1].read_text())
        receipt['artifact_hashes']['TELEMETRY.jsonl'] = sha256(paths[0])
        paths[1].write_text(json.dumps(receipt), encoding='utf-8')
        complete = json.loads(paths[2].read_text())
        complete['receipt_sha256'] = sha256(paths[1])
        paths[2].write_text(json.dumps(complete), encoding='utf-8')
        with pytest.raises(AuditError, match='Prelude observation arrived after current start'):
            audit_collection(root)
    finally:
        for path, content in original.items():
            path.write_bytes(content)


if __name__ == '__main__':
    unittest.main()
