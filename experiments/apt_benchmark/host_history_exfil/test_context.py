"""Causal feature and saved-output integrity tests; no model fits."""
import csv
import inspect
import json

import numpy as np
import pytest

from . import audit, context, run


def events():
    return dict(start=np.array([1., 2., 5., 5., 12., 400_005.]),
                end=np.array([4., 5., 6., 11., 15., 400_010.]),
                src=np.array(['10.1.3.1', '10.1.3.1', '10.1.3.1', '10.1.4.2', '10.1.3.1', '10.1.3.1']),
                dst=np.array(['10.1.5.9', '10.1.5.9', '10.1.5.9', '10.1.5.9', '10.1.4.2', '10.1.5.9']),
                forward_bytes=np.array([10., 20., 30., 40., 50., 60.]),
                reverse_bytes=np.array([1., 2., 3., 4., 5., 6.]),
                remote_admin=np.array([1., 0., 0., 1., 0., 0.]))


def test_future_equal_time_and_unfinished_flows_are_excluded():
    d = events()
    history, _, latest, _ = context.history_features(**d)
    assert not history[0].any()
    assert not history[1].any()  # Row zero is still unfinished.
    assert latest[2] == 4  # End==start at 5 is excluded.
    assert history[2, 0] == np.log1p(1)
    assert history[2, 1] == np.log1p(10)
    assert history[2, 18 + 1] == np.log1p(1)  # Reverse endpoint orientation.
    assert history[4, 0] == np.log1p(3)
    assert np.all(latest < d['start'])


def test_window_lower_boundary_is_inclusive_and_old_counts_expire():
    state = context.WindowState()
    state.add(10., 'peer', 9, 2, 1, 0, 1)
    at_boundary, latest = state.query(300_010., 300_000, 'peer', True)
    assert at_boundary[0] == np.log1p(1) and latest == 10
    expired, latest = state.query(300_011., 300_000, 'peer', True)
    assert expired == [0.] * 8 + [1.]
    assert latest == -1


def test_history_and_wrong_host_control_are_input_order_invariant():
    d = events()
    # Include tied completion times and tied start times.
    d['end'][3] = 6
    original = context.history_features(**d)
    order = np.array([5, 3, 1, 4, 0, 2])
    reordered = context.history_features(**{k: v[order] for k, v in d.items()})
    for expected, actual in zip(original, reordered):
        np.testing.assert_allclose(actual[np.argsort(order)], expected, rtol=0, atol=1e-12)


def test_future_hosts_do_not_change_wrong_host_donors_or_history():
    d = events()
    short = context.history_features(**d)
    future = {'start': 900_000., 'end': 900_001., 'src': '10.1.1.200',
              'dst': '10.1.2.200', 'forward_bytes': 10**9,
              'reverse_bytes': 10**9, 'remote_admin': 1.}
    augmented = context.history_features(**{k: np.append(v, future[k]) for k, v in d.items()})
    for original, actual in zip(short, augmented):
        np.testing.assert_array_equal(original, actual[:-1])
    assert np.all(short[3] < d['start'])


def test_label_free_signature_and_static_role_one_hot():
    names = set(inspect.signature(context.history_features).parameters)
    assert names == {'start', 'end', 'src', 'dst', 'forward_bytes', 'reverse_bytes', 'remote_admin'}
    src = ['10.1.1.1', '10.1.2.2', '10.1.3.3', '10.1.4.4', '10.1.5.5', '192.168.1.1']
    dst = list(reversed(src))
    matrix = context.role_features(src, dst)
    assert matrix.shape == (6, 8)
    np.testing.assert_array_equal(matrix[:, :4].argmax(1), [1, 1, 1, 2, 3, 0])
    np.testing.assert_array_equal(matrix[:, 4:].argmax(1), [0, 3, 2, 1, 1, 1])
    np.testing.assert_array_equal(matrix.sum(1), np.full(6, 2))
    assert context.role('fe80::1') == audit.independent_role('fe80::1') == 0


@pytest.mark.parametrize('change', ['backwards', 'nonfinite', 'length'])
def test_invalid_history_inputs_rejected(change):
    d = events()
    if change == 'backwards':
        d['end'][0] = 0
    elif change == 'nonfinite':
        d['start'][0] = np.nan
    else:
        d['dst'] = d['dst'][:-1]
    with pytest.raises(ValueError):
        context.history_features(**d)


def test_calibration_threshold_uses_strict_ties_and_highest_f1_tie():
    labels = np.array([True, False, True, False])
    scores = np.array([.9, .9, .5, .1])
    threshold = run.f1_threshold(labels, scores)
    assert threshold == .1
    np.testing.assert_array_equal(scores > threshold, [True, True, True, False])
    # Thresholds -1 and .2 both yield F1=2/3; higher threshold wins.
    assert run.f1_threshold(np.array([True, False, False, True]), np.array([.9, .2, .2, .1])) == .2
    assert run.f1_threshold(np.zeros(3, dtype=bool), np.array([.1, .2, .2])) == .2


def synthetic_raw(tmp_path):
    essential = ['id', 'expiration_id', 'src_ip', 'dst_ip', 'src_port', 'dst_port',
                 'bidirectional_first_seen_ms', 'bidirectional_last_seen_ms',
                 'src2dst_bytes', 'dst2src_bytes', 'protocol']
    header = essential + [f'numeric_{i}' for i in range(77 - len(essential))]
    header += ['application_name', 'application_category_name', 'application_is_guessed',
               'requested_server_name', 'client_fingerprint', 'server_fingerprint',
               'user_agent', 'content_type', 'Activity', 'Stage', 'DefenderResponse', 'Signature']
    files = []
    for index, (split, stage) in enumerate([('fit', 'Benign'), ('calibration', 'Data Exfiltration'), ('test', 'Lateral Movement')]):
        values = {n: '1' for n in header[:77]}
        values.update(src_ip='10.1.3.1', dst_ip='10.1.5.9', src_port='3000', dst_port='445',
                      bidirectional_first_seen_ms=str(100 + index * 100),
                      bidirectional_last_seen_ms=str(101 + index * 100),
                      src2dst_bytes='20', dst2src_bytes='2')
        row = [values[n] for n in header[:77]]
        # A deliberately expanded free-text middle contains a plausible wrong
        # stage. The final four annotation fields remain right anchored.
        row += ['app', 'category', '1', 'server', 'client', 'server', 'agent', 'content', 'Benign', 'extra']
        row += ['RemoteSystemDiscovery', stage, 'None', 'None' if stage == 'Benign' else 'APT']
        path = tmp_path / f'capture_{index}.csv'
        with path.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream); writer.writerow(header); writer.writerow(row)
        files.append({'source_file': path.name, 'sha256': run.sha(path), 'rows': 1,
                      'right_anchored_stage_counts': {stage: 1}, 'split': split})
    path = tmp_path / 'INPUTS.json'
    path.write_text(json.dumps({'private_raw_root': str(tmp_path), 'files': files}), encoding='utf-8')
    return path


def test_parser_uses_right_annotation_anchor_and_stable_numeric_prefix(tmp_path, monkeypatch):
    inputs = synthetic_raw(tmp_path)
    monkeypatch.setattr(run, 'INPUT_SHA', run.sha(inputs))
    target = tmp_path / 'prepared'
    run.prepare(inputs, target)
    with np.load(target / 'DATA.npz', allow_pickle=False) as data:
        np.testing.assert_array_equal(data['y'], [0, 3, 2])
        np.testing.assert_array_equal(data['split'], [0, 1, 2])
        assert data['current'].shape[0] == 3
        assert not any('Stage' in name or 'Activity' in name or 'first_seen' in name for name in data['feature_names'])
        assert np.all(data['latest_history_end'] < data['start'])


def test_prepare_rejects_unresolved_annotation_instead_of_skipping(tmp_path, monkeypatch):
    inputs = synthetic_raw(tmp_path)
    manifest = json.loads(inputs.read_text())
    path = tmp_path / manifest['files'][0]['source_file']
    path.write_text(path.read_text().replace('RemoteSystemDiscovery,Benign,None,None', 'RemoteSystemDiscovery,UNKNOWN,None,None'))
    manifest['files'][0]['sha256'] = run.sha(path)
    inputs.write_text(json.dumps(manifest))
    monkeypatch.setattr(run, 'INPUT_SHA', run.sha(inputs))
    with pytest.raises(ValueError, match='Unresolved right-anchored'):
        run.prepare(inputs, tmp_path / 'prepared')


def test_independent_counts_match_defined_metrics_and_absent_stages():
    y = np.array([0, 0, 1, 2, 2, 3, 3])
    p = np.array([[.8,.1,.05,.05], [.1,.2,.3,.4], [.1,.7,.1,.1],
                  [.05,.1,.7,.15], [.7,.1,.1,.1], [.1,.1,.4,.4], [.1,.1,.1,.7]])
    audit.compare(run.metrics(y, p), audit.metrics(y, p))
    use = y != 2
    absent = audit.metrics(y[use], p[use])
    audit.compare(run.metrics(y[use], p[use]), absent)
    assert absent['per_class']['LateralMovement']['ap'] is None
    assert absent['lateral_any_attack_recall'] is None
    assert absent['exfil_vs_lateral_ap'] is None
    assert absent['per_class']['LateralMovement']['support'] == 0
    wrong = json.loads(json.dumps(absent))
    wrong['benign_false_attack_count'] += 1
    with pytest.raises(audit.AuditError, match='benign_false_attack_count'):
        audit.compare(wrong, absent)


def test_independent_thresholds_ties_and_corrupted_probabilities():
    y = np.array([True, False, False, True])
    scores = np.array([.9,.2,.2,.1])
    assert audit.best_f1_threshold(y, scores) == run.f1_threshold(y, scores) == .2
    scores = np.array([.1,.2,.2,.9,.9])
    threshold = audit.tail_threshold(scores, .2)
    assert threshold == .9 and not (scores > threshold).any()
    assert audit.tail_threshold(np.zeros(1000), .001) == 0
    p = np.full((2,4), .25)
    audit.probabilities(p, 2)
    p[1, 3] += .1
    with pytest.raises(audit.AuditError, match='row sums'):
        audit.probabilities(p, 2)


def test_independent_raw_binding_rejects_changed_labels_and_model_hash(tmp_path, monkeypatch):
    inputs = synthetic_raw(tmp_path)
    monkeypatch.setattr(run, 'INPUT_SHA', run.sha(inputs))
    target = tmp_path / 'prepared'
    run.prepare(inputs, target)
    with np.load(target / 'DATA.npz', allow_pickle=False) as z:
        d = {key: z[key] for key in z.files}
    receipt = audit.read(target / 'PREPARATION.json')
    counts = audit.raw_data_check(d, audit.read(inputs), receipt)
    assert counts['raw_rows_verified'] == 3
    d['y'][0] = 3
    with pytest.raises(audit.AuditError, match='label/endpoint'):
        audit.raw_data_check(d, audit.read(inputs), receipt)
    model = tmp_path / 'model.joblib'; model.write_bytes(b'original saved model')
    hashes = {model.name: audit.digest(model)}
    audit.artifact_hashes(tmp_path, hashes, [model.name])
    model.write_bytes(b'changed model')
    with pytest.raises(audit.AuditError, match='artifact hash'):
        audit.artifact_hashes(tmp_path, hashes, [model.name])


def test_independent_direct_history_detects_rehashed_feature_corruption():
    d = events()
    history, wrong, latest, wrong_latest = context.history_features(**d)
    record = {**d, 'y': np.array([0,0,2,3,0,3]), 'split': np.array([0,0,1,1,2,2]),
              'feature_names': np.array(['src2dst_bytes','dst2src_bytes','dst_remote_admin_service']),
              'current': np.column_stack([d['forward_bytes'],d['reverse_bytes'],d['remote_admin']]),
              'history': history, 'wrong_history': wrong, 'latest_history_end': latest,
              'latest_wrong_history_end': wrong_latest,
              'src_role': np.array([context.role(v) for v in d['src']]),
              'dst_role': np.array([context.role(v) for v in d['dst']])}
    assert audit.history_spot_checks(record)['history_anchors_independently_recomputed'] == 6
    record['history'][4, 1] += .001
    with pytest.raises(audit.AuditError, match='history arithmetic'):
        audit.history_spot_checks(record)
