import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from experiments.apt_benchmark.host_auth_context.host_events import (
    clean_line, linux_kind, linux_records, qualify_windows_clock,
    strict_earlier_window_count, windows_kind, windows_records, write_arrays,
)


class HostEventQualificationTests(unittest.TestCase):
    def test_author_annotations_and_direction_marks_do_not_enter_event(self):
        event = 'Logon Type:\t3'
        self.assertEqual(clean_line(event + ',Normal,Benign,Benign,None'), event)
        self.assertEqual(clean_line(event + ',Anything,Lateral Movement,Detected,APT'), event)
        self.assertEqual(clean_line('New Time:\u200e2021-06-26T00:33:09Z'),
                         'New Time:2021-06-26T00:33:09Z')

    def test_linux_multiline_wrapper_not_multiple_events(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '10_1_3_8-audit_labeled'
            p.write_text("LogEvent,Activity,Stage,DefenderResponse,Signature\n"
                         "type=USER_AUTH msg=audit(1624035209.126:45): msg='op=PAM:authentication res=success'\n"
                         'AUID="example" UID="example",Normal,Benign,Benign,None\n')
            rows = list(linux_records(p))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['kind'], 'linux_auth_success')
            self.assertEqual(rows[0]['record_time_ms'], 1624035209126)

    def test_unknown_auth_result_fails_instead_of_assuming_success(self):
        with self.assertRaises(ValueError):
            linux_kind('USER_AUTH', None)
        self.assertIsNone(linux_kind('USER_CMD', 'success'))

    def test_windows_multiline_and_annotation_invariance(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / '10_1_3_17-windows-securityevents.csv'
            p.write_text('Keywords,Date and Time,Source,Event ID,Task Category,Activity,Stage,DefenderResponse,Signature\n'
                         'Audit Success,6/25/2021 5:33:09 PM,Microsoft-Windows-Security-Auditing,4624,Logon,Normal,Benign,Benign,None\n'
                         'Logon Type:\t3,Normal,Benign,Benign,None\n'
                         'Network Information:,Normal,Benign,Benign,None\n'
                         'Audit Success,6/25/2021 5:33:10 PM,Microsoft-Windows-Security-Auditing,4648,Logon,Other,Lateral Movement,Benign,APT\n')
            rows = list(windows_records(p))
            self.assertEqual(len(rows), 2)
            self.assertEqual(windows_kind(rows[0]), 'windows_logon_network_success')
            self.assertEqual(windows_kind(rows[1]), 'windows_explicit_credentials_attempt')
            self.assertNotIn('Lateral Movement', rows[1]['payload'])

    def test_explicit_credentials_attempt_is_not_success(self):
        self.assertEqual(windows_kind({'event_id': 4648, 'payload': ''}),
                         'windows_explicit_credentials_attempt')
        self.assertEqual(windows_kind({'event_id': 4624, 'payload': 'Logon Type: 10'}),
                         'windows_logon_remoteinteractive_success')
        with self.assertRaises(ValueError):
            windows_kind({'event_id': 4624, 'payload': ''})

    def test_utc_anchor_offset_qualifies_and_inconsistency_fails(self):
        from datetime import datetime, timezone
        records = []
        for day in [25, 26, 27]:
            t = datetime(2021, 6, day, 17, 33, 9, tzinfo=timezone.utc).timestamp() * 1000
            records.append({'event_id': 4616, 'local_ms': t,
                            'payload': f'New Time: 2021-06-{day+1}T00:33:09.500Z\nPrevious Time: 2021-06-{day+1}T00:33:09.499Z'})
        clock = qualify_windows_clock(records)
        self.assertEqual(clock['utc_offset_added_ms'], 7 * 3600000)
        self.assertEqual(clock['availability_guard_ms'], 1000)
        records[0]['local_ms'] += 3600000
        with self.assertRaises(ValueError):
            qualify_windows_clock(records)

    def test_strict_earlier_excludes_equal_and_future_observations(self):
        self.assertEqual(strict_earlier_window_count(np.array([5., 8., 10., 11.]), 10., 5.), 2)
        self.assertEqual(strict_earlier_window_count(np.array([5., 8., 10., 11.]), 10., 2.), 1)
        with self.assertRaises(ValueError):
            strict_earlier_window_count(np.array([8., 5.]), 10., 5.)

    def test_saved_arrays_no_object_labels_or_message_bodies(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'EVENTS.npz'
            row = {'host': '10.1.3.8', 'time_ms': 12., 'record_time_ms': 12.,
                   'family': 'linux_audit', 'event_sha256': 'a' * 64,
                   'kind': 'linux_auth_failure'}
            write_arrays(path, [row], True)
            with np.load(path, allow_pickle=False) as x:
                self.assertEqual(x['kind'][0], 1)
                self.assertEqual(set(x.files), {'host', 'time_ms', 'record_time_ms',
                                                'family', 'event_sha256', 'kind', 'kind_names'})
                self.assertTrue(all(x[k].dtype.kind != 'O' for k in x.files))


if __name__ == '__main__':
    unittest.main()
