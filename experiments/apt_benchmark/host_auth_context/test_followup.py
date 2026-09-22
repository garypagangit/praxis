"""Synthetic causality, fair-control and decision-policy checks; no fits."""
import json

import numpy as np
import pytest

from . import audit, features, policy, run


def sources():
    events = {'host': np.array(['10.1.3.1'] * 5 + ['10.1.3.2', '10.1.3.3', '10.1.4.2']),
              'time_ms': np.array([4., 5., 6., 300005., 400000., 3., 2., 2.]),
              'kind': np.array([0, 0, 1, 0, 1, 1, 0, 0]),
              'kind_names': np.array(['success', 'failure'])}
    observed = {'host': np.array(['10.1.3.1', '10.1.3.2', '10.1.3.3', '10.1.4.2', '10.1.3.1']),
                'time_ms': np.array([1., 1., 1., 1., 300005.]),
                'family': np.array(['linux_audit', 'linux_audit', 'windows_security', 'linux_audit', 'linux_audit'])}
    return events, observed


def test_strict_past_and_inclusive_lower_window_boundary():
    events, observed = sources()
    result = features.build(np.array([4., 5., 300005.]), np.array(['10.1.3.1'] * 3), events, observed)
    np.testing.assert_array_equal(result['auth'][0], np.zeros(4))
    np.testing.assert_allclose(result['auth'][1], [np.log1p(1), 0, np.log1p(1), 0])
    # 5 is exactly the lower 5m boundary; 300005 is equal to query time.
    np.testing.assert_allclose(result['auth'][2], [np.log1p(1), np.log1p(1), np.log1p(2), np.log1p(1)])
    np.testing.assert_array_equal(result['latest_auth'], [-1., 4., 6.])
    assert np.all(result['latest_auth'] < [4., 5., 300005.])


def test_future_inventory_cannot_change_past_availability_or_donors():
    events, observed = sources()
    times, hosts = np.array([8., 8., .5]), np.array(['10.1.3.1', '10.1.3.99', '10.1.3.1'])
    expected = features.build(times, hosts, events, observed)
    future = {'host': ['10.1.3.99', '10.1.3.77'], 'time_ms': [900000., 900001.],
              'family': ['linux_audit', 'linux_audit']}
    observed = {key: np.append(values, future[key]) for key, values in observed.items()}
    for key, value in [('host', ['10.1.3.99', '10.1.3.77']), ('time_ms', [900000., 900001.]), ('kind', [0, 1])]:
        events[key] = np.append(events[key], value)
    actual = features.build(times, hosts, events, observed)
    for key in expected:
        np.testing.assert_array_equal(actual[key], expected[key])
    np.testing.assert_array_equal(expected['availability'][1:], np.zeros((2, 7)))


def test_wrong_host_is_prior_different_and_same_family_and_role():
    events, observed = sources()
    result = features.build(np.array([1., 8., 8.]), np.array(['10.1.3.1', '10.1.3.1', '10.1.3.3']), events, observed)
    assert result['donor'].tolist() == ['', '10.1.3.2', '']
    assert result['availability'][:, 6].tolist() == [0., 1., 0.]
    np.testing.assert_allclose(result['wrong_auth'][1], [0, np.log1p(1), 0, np.log1p(1)])
    assert result['latest_wrong_auth'][1] == 3


def test_input_order_and_ignored_annotation_fields_do_not_change_features():
    events, observed = sources()
    times, hosts = np.array([5., 8., 300005.]), np.array(['10.1.3.1'] * 3)
    expected = features.build(times, hosts, events, observed)
    e = {key: values[::-1] if key != 'kind_names' else values for key, values in events.items()}
    o = {key: values[::-1] for key, values in observed.items()}
    e['Stage'] = np.full(len(e['host']), 'Data Exfiltration')
    o['attacker_label'] = np.ones(len(o['host']))
    actual = features.build(times[::-1], hosts[::-1], e, o)
    for key, value in expected.items():
        np.testing.assert_array_equal(actual[key] if key.endswith('names') else actual[key][::-1], value)


def test_ambiguous_family_and_invalid_time_are_rejected():
    events, observed = sources()
    observed['family'][-1] = 'windows_security'
    with pytest.raises(ValueError, match='Ambiguous'):
        features.build(np.array([8.]), np.array(['10.1.3.1']), events, observed)
    events, observed = sources(); events['time_ms'][0] = np.nan
    with pytest.raises(ValueError, match='event times'):
        features.build(np.array([8.]), np.array(['10.1.3.1']), events, observed)


def test_every_new_view_contains_identical_availability_without_identity_features():
    d = {'current': np.full((2, 3), 11.), 'roles': np.full((2, 8), 12.), 'history': np.full((2, 36), 13.)}
    availability = np.arange(14).reshape(2, 7)
    a = {'availability': availability, 'auth': np.full((2, 4), 14.), 'wrong_auth': np.full((2, 4), 15.),
         'donor': np.array(['PRIVATE_HOST_A', 'PRIVATE_HOST_B'])}
    views = run.views(d, a)
    expected_offsets = {'current_availability': 3, 'context_availability': 47,
                        'current_auth': 3, 'context_auth': 47, 'context_wrong_auth': 47,
                        'auth_availability_only': 0, 'availability_only': 0}
    assert set(views) == set(expected_offsets)
    for name, offset in expected_offsets.items():
        np.testing.assert_array_equal(views[name][:, offset:offset + 7], availability)
        assert views[name].dtype.kind in 'fiu'


def test_dual_flags_are_not_scored_as_resolved_and_review_keeps_other_attacks():
    y = np.array([2, 2, 3, 3, 0, 1])
    base = np.array([2, 0, 2, 0, 0, 1])
    exfil = np.array([True, True, True, True, True, False])
    unsupported = np.array([False, False, False, True, False, False])
    result = policy.decisions(y, base, exfil, unsupported)
    assert result['retained_baseline_alerts'] is True
    assert result['review_union_count'] == 6 and result['baseline_review_count'] == 3
    assert result['additional_review_count'] == 3
    assert result['by_true_class']['OtherAttackStage']['any_review'] == 1
    movement = result['by_true_class']['LateralMovement']
    assert movement['movement_flag'] == 1 and movement['both_flags'] == 1
    assert movement['resolved_movement_only'] == 0
    assert result['exfil_flag']['tp'] == 2
    assert result['automatic_exfil']['tp'] == 0
    assert result['by_true_class']['DataExfiltration']['unresolved_review'] == 2


def calibration():
    # Role 0 exactly meets both minima. Role 1 lacks one negative and role 2
    # lacks one positive. No movement labels exist in this calibration set.
    roles = np.repeat([0, 1, 2], [120, 119, 119])
    labels = np.concatenate([np.r_[np.zeros(100), np.full(20, 3)],
                             np.r_[np.zeros(99), np.full(20, 3)],
                             np.r_[np.zeros(100), np.full(19, 3)]]).astype(int)
    scores = np.concatenate([np.linspace(.01, .3, 120), np.linspace(.4, .8, 119), np.linspace(.1, .7, 119)])
    return labels, scores, roles


def test_role_support_minima_fallback_and_all_nine_policy_variants():
    y, scores, roles = calibration()
    result = policy.evaluate(y, scores, roles, np.array([3, 3, 3, 2]), np.ones(4),
                             np.array([0, 1, 2, 3]), np.zeros(4, dtype=int))
    assert len(result['policies']) == 9
    assert result['calibration_role_support']['0'] == {'positive': 20, 'negative': 100}
    assert result['calibration_role_support']['1'] == {'positive': 20, 'negative': 99}
    assert result['calibration_role_support']['2'] == {'positive': 19, 'negative': 100}
    assert result['calibration_role_support']['3'] == {'positive': 0, 'negative': 0}
    selected = result['policies']['tail_0.01__role_tail']
    assert selected['role_cuts']['1'] == selected['global_cut']
    assert selected['role_cuts']['3'] == selected['global_cut']
    assert selected['role_cuts']['0'] != selected['global_cut']
    assert selected['all_test']['exfil_flag']['tp'] == 3
    assert selected['all_test']['automatic_exfil']['tp'] == 1
    assert selected['all_test']['by_true_class']['LateralMovement']['unsupported_exfil_review'] == 1


def test_test_labels_and_scores_cannot_change_calibration_cuts_or_support():
    y, scores, roles = calibration()
    first = policy.evaluate(y, scores, roles, np.array([0, 3]), np.array([.1, .9]), np.array([0, 1]), np.array([0, 2]))
    second = policy.evaluate(y, scores, roles, np.array([2, 0]), np.array([.99, .01]), np.array([0, 1]), np.array([1, 3]))
    assert first['calibration_role_support'] == second['calibration_role_support']
    for name in first['policies']:
        for key in ('global_cut', 'role_cuts', 'global_calibration_nonexfil_rate'):
            assert first['policies'][name][key] == second['policies'][name][key]


def test_strict_tail_ties_do_not_spend_false_positive_budget():
    scores = np.array([.1, .2, .2, .9, .9])
    assert policy.tail_cut(scores, .2) == .9
    assert np.sum(scores > policy.tail_cut(scores, .2)) == 0
    assert policy.tail_cut(np.zeros(1000), .001) == 0
    with pytest.raises(ValueError, match='No calibration negatives'):
        policy.tail_cut(np.array([]), .01)


def test_frozen_binding_rejects_modified_input_before_use(tmp_path):
    artifact = tmp_path / 'input.npz'; artifact.write_bytes(b'frozen input bytes')
    specification = {'bindings': [{'path': str(artifact), 'sha256': run.sha(artifact)}]}
    protocol = tmp_path / 'protocol.json'; protocol.write_text(json.dumps(specification))
    assert run.verify(protocol) == specification
    artifact.write_bytes(b'changed input')
    with pytest.raises(ValueError, match='Frozen source/artifact changed'):
        run.verify(protocol)


def test_independent_policy_audit_matches_all_variants_and_detects_overclaim():
    yc, pc, rc = calibration()
    yt, pt = np.array([0, 1, 2, 3, 3]), np.array([.95, .95, .95, .95, .95])
    rt, base = np.array([0, 1, 0, 1, 2]), np.array([0, 1, 2, 0, 3])
    expected = audit.independent_policies(yc, pc, rc, yt, pt, rt, base)
    actual = policy.evaluate(yc, pc, rc, yt, pt, rt, base)
    audit.compare(actual, expected)
    bad = json.loads(json.dumps(actual))
    # Preserve the raw exfil flag count but falsely call an unsupported review
    # an automatically resolved true exfiltration. The audit must reject it.
    bad['policies']['tail_0.01__global']['all_test']['automatic_exfil']['tp'] += 1
    with pytest.raises(audit.common.AuditError, match='automatic_exfil.tp'):
        audit.compare(bad, expected)


def test_independent_auth_join_check_detects_feature_and_future_donor_tampering():
    events, observed = sources()
    d = {'start': np.array([4., 5., 6., 7., 8., 300005.]),
         'src': np.array(['10.1.3.1'] * 6), 'y': np.array([0, 2, 3, 0, 2, 3]),
         'split': np.array([0, 0, 1, 1, 2, 2])}
    a = features.build(d['start'], d['src'], events, observed)
    assert audit.feature_check(d, a, events, observed)['anchors_with_direct_event_filtering'] == 6
    a['auth'][4, 0] += .01
    with pytest.raises(audit.common.AuditError, match='independent feature arithmetic'):
        audit.feature_check(d, a, events, observed)
    a = features.build(d['start'], d['src'], events, observed)
    # A plausible host identity of a different logging family is insufficient.
    a['donor'][4] = '10.1.3.3'
    with pytest.raises(audit.common.AuditError, match='cross-family donor'):
        audit.feature_check(d, a, events, observed)
