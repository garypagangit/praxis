import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.ait_adapter import (
    classify_source, load_ait, normalized_text, source_timestamp,
)
from experiments.apt_benchmark.contracts import check_availability, check_feature_names, split_index


PROTOCOL = {'splits': {'fit': ['fitrun'], 'development': ['devrun'],
                       'calibration': ['calrun'], 'test': ['testrun']}}
RAW = ('type=LOGIN msg=audit(1641000000.125:51) pid=11 uid=0 node=host-a result=ok\n'
       '\n'
       'type=EXECVE msg=audit(1641000002.250:53) pid=12 uid=1000 node=host-a comm="curl"\n')


def fixture(root):
    for group in ('fitrun', 'devrun', 'calrun', 'testrun'):
        for family in ('gather', 'labels'):
            folder = root / group / family / 'intranet_server/logs'
            folder.mkdir(parents=True)
            (folder / 'audit.log').write_text(
                RAW if family == 'gather' else json.dumps({'line': 3, 'labels': ['execution'], 'rules': ['source-rule']}) + '\n',
                encoding='utf-8', newline='\n')


class ContractTests(unittest.TestCase):
    def test_forbidden_feature_metadata_case_and_aliases(self):
        check_feature_names(['count_read', 'hash_17', 'source_type'])
        for name in ('Label', ' y ', 'Stages', 'scenario', 'RULES', 'line_number', 'event_at', 'impact_at', 'host_id'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                check_feature_names([name])

    def test_future_times_and_nonfinite_or_boolean_times_rejected(self):
        check_availability(event_at=1., feature_available_at=2., decision_at=2.)
        for event, feature, decision in ((3, 2, 4), (1, 4, 3), (True, 2, 3), (1, float('nan'), 3)):
            with self.subTest(times=(event, feature, decision)), self.assertRaises(ValueError):
                check_availability(event_at=event, feature_available_at=feature, decision_at=decision)

    def test_group_overlap_empty_roles_and_path_identifiers_fail(self):
        self.assertEqual(split_index(PROTOCOL)['testrun'], 'test')
        for bad in ('fitrun', '../outside'):
            changed = copy.deepcopy(PROTOCOL)
            changed['splits']['test'] = [bad]
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split_index(changed)
        for bad in ([], 'testrun'):
            changed = copy.deepcopy(PROTOCOL)
            changed['splits']['test'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                split_index(changed)


class AdapterTests(unittest.TestCase):
    def test_exact_original_one_based_join_keeps_blank_source_line(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            x, y, rows, report = load_ait(root, PROTOCOL)
            self.assertEqual(x.shape, (12, 128))
            np.testing.assert_array_equal(y, [0, 0, 1] * 4)
            self.assertEqual([row['line_number'] for row in rows[:3]], [1, 2, 3])
            self.assertEqual(rows[2]['id'], 'fitrun/intranet_server/logs/audit.log:3')
            self.assertEqual(rows[2]['stages'], ['execution'])
            self.assertIsNone(rows[1]['event_at'])
            self.assertEqual(report['parseable_event_time_rows'], 8)
            self.assertEqual(report['files'][0]['rows'], 3)

    def test_annotations_and_rules_cannot_change_features(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            before, y_before, _, _ = load_ait(root, PROTOCOL)
            for label in root.glob('*/labels/intranet_server/logs/audit.log'):
                label.write_text(json.dumps({'line': 1, 'labels': ['entirely_different_stage'],
                                             'rules': ['injected-marker'], 'scenario': 'label-only',
                                             'timestamp': '2099-01-01'}) + '\n', encoding='utf-8')
            after, y_after, _, _ = load_ait(root, PROTOCOL)
            np.testing.assert_array_equal(before, after)
            self.assertFalse(np.array_equal(y_before, y_after))

    def test_timestamp_host_and_identity_patterns_are_masked(self):
        pairs = [
            ('audit', 'type=LOGIN msg=audit(1641000000.1:4) pid=99 uid=1000 hostname=first node="node-one" addr=192.0.2.1',
             'type=LOGIN msg=audit(1777000000.5:8) pid=12 uid=2000 hostname=second node="node-two" addr=198.51.100.2'),
            ('auth', 'Jan  2 03:04:05 first sshd[123]: Accepted user from 192.0.2.3 port 22',
             'Feb 12 13:14:15 second sshd[456]: Accepted user from 198.51.100.5 port 222'),
            ('apache_access', '192.0.2.1 - - [01/Jan/2022:00:00:00 +0000] "GET / HTTP/1.1" 200 42',
             '198.51.100.2 - - [02/Feb/2023:11:11:11 +0200] "GET / HTTP/1.1" 200 42'),
            ('apache_error', '[Mon Jan 02 03:04:05.123456 2023] client 2001:db8::1 failed',
             '[Tue Feb 03 04:05:06.654321 2024] client 2001:db8:abcd::99 failed'),
        ]
        for source, left, right in pairs:
            with self.subTest(source=source):
                self.assertEqual(normalized_text(left, source), normalized_text(right, source))
        # Operation/privilege content remains visible; not all payloads collapse.
        self.assertNotEqual(normalized_text('uid=0 comm="curl"', 'audit'),
                            normalized_text('uid=1000 comm="whoami"', 'audit'))

    def test_source_time_uses_explicit_zone_only(self):
        expected = datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp()
        self.assertEqual(source_timestamp('[01/Jan/2022:02:00:00 +0200]', 'apache_access'), expected)
        self.assertEqual(source_timestamp('msg=audit(1640995200.125:9)', 'audit'), expected + .125)
        self.assertIsNone(source_timestamp('Jan 1 01:02:03 hostname text', 'auth'))
        self.assertIsNone(source_timestamp('[Mon Jan 01 01:02:03 2022] text', 'apache_error'))
        with self.assertRaises(ValueError):
            source_timestamp('msg=audit(' + '9' * 400 + ':1)', 'audit')

    def test_unknown_type_and_label_without_raw_fail(self):
        self.assertEqual(classify_source(Path('auth.log.1')), 'auth')
        self.assertEqual(classify_source(Path('audit.log.12')), 'audit')
        for name in ('audit.log.gz', 'auth.log.1.gz', 'access.log.gz', 'audit.log.extra'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                classify_source(Path(name))
        with self.assertRaises(ValueError):
            classify_source(Path('unqualified.log'))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            (root / 'fitrun/gather/intranet_server/logs/audit.log').unlink()
            with self.assertRaisesRegex(ValueError, 'matching raw source'):
                load_ait(root, PROTOCOL)

    def test_unpaired_raw_not_silently_labeled_benign(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            extra = root / 'fitrun/gather/intranet_server/logs/auth.log'
            extra.write_text('unknown uncovered source\n', encoding='utf-8')
            _, _, rows, report = load_ait(root, PROTOCOL)
            self.assertEqual(report['rows'], 12)
            self.assertFalse(any(row['source_type'] == 'auth' for row in rows))
            (root / 'fitrun/labels/intranet_server/logs/audit.log').unlink()
            with self.assertRaisesRegex(ValueError, 'No qualified raw/label source pairs'):
                load_ait(root, PROTOCOL)

    def test_duplicate_annotations_invalid_numbers_and_unknown_labels_fail(self):
        invalid = [
            [{'line': 1, 'labels': ['a']}, {'line': 1, 'labels': ['b']}],
            [{'line': True, 'labels': ['a']}], [{'line': 0, 'labels': ['a']}],
            [{'line': 4, 'labels': ['a']}], [{'line': 1, 'labels': []}],
            [{'line': 1, 'labels': ['   ']}], [{'line': 1, 'labels': None}],
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture(root)
            target = root / 'fitrun/labels/intranet_server/logs/audit.log'
            for annotations in invalid:
                target.write_text(''.join(json.dumps(item) + '\n' for item in annotations), encoding='utf-8')
                with self.subTest(annotations=annotations), self.assertRaises(ValueError):
                    load_ait(root, PROTOCOL)


if __name__ == '__main__':
    unittest.main()
