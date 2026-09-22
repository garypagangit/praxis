"""Independent arithmetic/provenance audit; no fits, inference or model loading.

Uses previously independent four-class metric helpers, never the new scientific
runner, feature builder, policy or host parser. Auth joins are checked directly
at all movement anchors plus a fixed distributed sample.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np

from ..host_history_exfil import audit as common

require, compare, digest, read = common.require, common.compare, common.digest, common.read
CLASSES = common.CLASSES
SEEDS = common.SEEDS
NEW_ARMS = ['current_availability', 'context_availability', 'current_auth', 'context_auth',
            'context_wrong_auth', 'auth_availability_only', 'availability_only']
PRIOR_ARMS = common.ARMS
KINDS = ['linux_auth_success', 'linux_auth_failure', 'linux_login_success',
         'linux_login_failure', 'linux_session_start', 'linux_session_end',
         'windows_logon_network_success', 'windows_logon_remoteinteractive_success',
         'windows_logon_other_success', 'windows_logon_failure', 'windows_explicit_credentials_attempt']
SOURCE = Path(__file__).parent


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def decision_counts(y, base, exfil, unsupported):
    movement = base == 2
    queue = (base != 0) | exfil
    automatic = exfil & ~(movement | unsupported)
    unresolved = exfil & (movement | unsupported)
    result = {'exfil_flag': common.alert_counts(y, exfil),
              'automatic_exfil': common.alert_counts(y, automatic),
              'review_union_count': int(np.count_nonzero(queue)),
              'review_union_benign_count': int(np.count_nonzero(queue & (y == 0))),
              'baseline_review_count': int(np.count_nonzero(base != 0)),
              'additional_review_count': int(np.count_nonzero(exfil & (base == 0))),
              'retained_baseline_alerts': not bool(np.any((base != 0) & ~queue)),
              'by_true_class': {}}
    for label, name in enumerate(CLASSES):
        at = y == label
        result['by_true_class'][name] = {
            'support': int(np.count_nonzero(at)),
            'movement_flag': int(np.count_nonzero(at & movement)),
            'exfil_flag': int(np.count_nonzero(at & exfil)),
            'both_flags': int(np.count_nonzero(at & movement & exfil)),
            'unsupported_exfil_review': int(np.count_nonzero(at & exfil & unsupported)),
            'unresolved_review': int(np.count_nonzero(at & unresolved)),
            'resolved_movement_only': int(np.count_nonzero(at & movement & ~exfil)),
            'resolved_exfil_only': int(np.count_nonzero(at & automatic)),
            'any_review': int(np.count_nonzero(at & queue)),
            'neither_target_flag': int(np.count_nonzero(at & ~(movement | exfil)))}
    require(result['retained_baseline_alerts'], 'baseline review flag lost')
    require(result['review_union_count'] == result['baseline_review_count'] + result['additional_review_count'], 'queue count identity')
    return result


def independent_policies(ycal, cal_score, cal_role, ytest, test_score, test_role, base):
    counts = np.zeros((16, 2), dtype=np.int64)
    for role, positive in zip(cal_role, ycal == 3):
        counts[int(role), int(positive)] += 1
    supports = {str(role): {'positive': int(counts[role, 1]), 'negative': int(counts[role, 0])} for role in range(16)}
    unsupported = (counts[test_role, 0] < 100) | (counts[test_role, 1] < 20)
    result = {'calibration_role_support': supports, 'policies': {}}
    for budget in (None, .001, .005, .01, .02):
        name = 'calibration_f1' if budget is None else f'tail_{budget:g}'
        threshold = common.best_f1_threshold(ycal == 3, cal_score) if budget is None else common.tail_threshold(cal_score[ycal != 3], budget)
        variants = [('global', {}, np.full(len(test_score), threshold))]
        if budget is not None:
            role_cuts = {}
            for role in range(16):
                eligible = (cal_role == role) & (ycal != 3)
                role_cuts[str(role)] = common.tail_threshold(cal_score[eligible], budget) if counts[role, 0] >= 100 else threshold
            variants.append(('role_tail', role_cuts, np.asarray([role_cuts[str(role)] for role in test_role])))
        for variant, cuts, thresholds in variants:
            flags = test_score > thresholds
            detail = {'global_cut': threshold, 'role_cuts': cuts,
                      'global_calibration_nonexfil_rate': float(np.mean(cal_score[ycal != 3] > threshold)),
                      'all_test': decision_counts(ytest, base, flags, unsupported), 'role_strata': {}}
            for role in np.unique(test_role):
                at = test_role == role
                detail['role_strata'][str(role)] = decision_counts(ytest[at], base[at], flags[at], unsupported[at])
            result['policies'][name + '__' + variant] = detail
    return result


def independent_arm(d, cal, test, pc, pt, base):
    roles = 4 * d['src_role'] + d['dst_role']
    y = d['y'][test]
    result = {'stage': common.metrics(y, pt),
              'decisions': independent_policies(d['y'][cal], pc[:, 3], roles[cal], y, pt[:, 3], roles[test], base),
              'by_source_host': {}, 'by_capture': {}, 'role_strata': {}}
    for host in np.unique(d['src'][test]):
        at = d['src'][test] == host
        if np.any((y[at] == 2) | (y[at] == 3)):
            result['by_source_host'][str(host)] = common.metrics(y[at], pt[at])
    for capture in np.unique(d['capture'][test]):
        at = d['capture'][test] == capture
        result['by_capture'][str(capture)] = common.metrics(y[at], pt[at])
    for role in np.unique(roles[test]):
        at = roles[test] == role
        result['role_strata'][str(role)] = common.metrics(y[at], pt[at])
    return result


def qualification_check(events, observed, receipt, bindings):
    require(events['kind_names'].tolist() == KINDS == receipt['kind_names'], 'qualified event categories')
    require(len(events['host']) == receipt['auth_context_records'] and len(observed['host']) == receipt['observed_records'], 'qualified event totals')
    common_fields = {'host', 'time_ms', 'record_time_ms', 'family', 'event_sha256'}
    require(set(observed) == common_fields and set(events) == common_fields | {'kind', 'kind_names'}, 'safe event schema')
    source_hashes = {item['sha256'] for item in bindings}
    for item in receipt['sources']:
        require(item['sha256'] in source_hashes, 'raw host source omitted from freeze bindings')
    require(sum(item['parsed_records'] - item['duplicate_records'] for item in receipt['sources']) == len(observed['host']) + receipt.get('excluded_after_dedup', 0), 'raw dedup and exclusion count accounting')
    if receipt.get('excluded_after_dedup', 0):
        require(receipt['approved_for_event_time_replay'] and receipt['status'] == 'QUALIFIED_LINUX_RECORD_TIME_REPLAY_WINDOWS_EXCLUDED', 'qualified Linux-only scope')
        require(set(observed['family']) == {'linux_audit'} and set(events['family']) == {'linux_audit'}, 'excluded Windows records entered predictors')
        require(sum(receipt['excluded_by_host'].values()) == receipt['excluded_after_dedup'], 'Windows exclusion totals')
    require(receipt['parser_sha256'] == digest(SOURCE / 'host_events.py'), 'host parser source binding')
    require(receipt['labels_or_credentials_in_arrays'] is False and receipt['model_fits'] == 0, 'qualification scope')
    positions = {str(identity): i for i, identity in enumerate(observed['event_sha256'])}
    require(len(positions) == len(observed['host']), 'duplicate observed identities')
    require(len(set(events['event_sha256'])) == len(events['host']), 'duplicate auth identities')
    require(np.all((events['kind'] >= 0) & (events['kind'] < len(KINDS))), 'event kind values')
    for data in (events, observed):
        require(np.isfinite(data['time_ms']).all() and np.isfinite(data['record_time_ms']).all(), 'event finite times')
        require(np.isin(data['family'], ['linux_audit', 'windows_security']).all(), 'log family')
        delay = np.where(data['family'] == 'windows_security', 1000., 0.)
        require(np.array_equal(data['time_ms'], data['record_time_ms'] + delay), 'timestamp resolution guard')
    matched = np.asarray([positions.get(str(identity), -1) for identity in events['event_sha256']])
    require(np.all(matched >= 0), 'authentication is not a subset of observed events')
    for key in common_fields:
        require(np.array_equal(events[key], observed[key][matched]), 'auth/observed provenance: ' + key)
    for host, item in receipt['host_summary'].items():
        at = observed['host'] == host; auth_at = events['host'] == host
        require(int(at.sum()) == item['observed_records'] and int(auth_at.sum()) == item['auth_context_records'], 'host event counts')
        require(set(observed['family'][at]) == {item['family']}, 'host family receipt')
        actual = Counter(KINDS[int(kind)] for kind in events['kind'][auth_at])
        compare(item['kind_counts'], dict(actual), 'auth kind totals')
    anchors = 0
    for clock in receipt['windows_clocks'].values():
        require(clock['status'] == 'PASS_EXPORT_TIMEZONE' and clock['availability_guard_ms'] == 1000, 'Windows timezone qualification')
        rows = clock['anchors']; anchors += len(rows)
        require(len(rows) == clock['anchor_count'] and len(rows) >= 3, 'Windows anchor support')
        require(len({int(row['utc_new_ms'] // 86400000) for row in rows}) >= 2, 'Windows anchor days')
        for row in rows:
            difference = row['utc_new_ms'] - row['displayed_local_ms']
            offset = round(difference / 60000) * 60000
            require(offset == row['offset_ms'] == clock['utc_offset_added_ms'], 'Windows offset arithmetic')
            require(abs(difference - offset) <= 1001 and math_close(difference - offset, row['fractional_residual_ms']), 'Windows residual arithmetic')
    return {'observed_events': len(observed['host']), 'auth_events': len(events['host']),
            'raw_source_hashes_verified': len(receipt['sources']), 'windows_clock_anchors_verified': anchors,
            'meaning': 'Hash-bound parser output and export-offset arithmetic; absolute host synchronization and ingestion delay are not certified.'}


def math_close(a, b):
    return bool(np.isclose(a, b, rtol=0, atol=1e-6))


def feature_check(d, a, events, observed):
    n, k = len(d['y']), len(events['kind_names'])
    require(a['auth'].shape == (n, 2 * k) and a['wrong_auth'].shape == (n, 2 * k), 'auth dimensions')
    require(a['availability'].shape == (n, 7), 'availability dimensions')
    for name in ('auth', 'wrong_auth', 'availability'):
        require(np.isfinite(a[name]).all() and np.all(a[name] >= 0), 'auth finite features')
    require(np.all(a['latest_auth'] < d['start']) and np.all(a['latest_wrong_auth'] < d['start']), 'strict auth chronology')
    require(not np.any((a['donor'] != '') & (a['donor'] == d['src'])), 'self donor')
    host_data = {}
    for host in np.unique(observed['host']):
        at = observed['host'] == host
        families = np.unique(observed['family'][at])
        require(len(families) == 1, 'ambiguous family')
        host_data[str(host)] = {'family': str(families[0]), 'observed': observed['time_ms'][at],
                                'first': float(np.min(observed['time_ms'][at])),
                                'times': events['time_ms'][events['host'] == host],
                                'kinds': events['kind'][events['host'] == host]}
    # Check prior observation eligibility for every row, independently of samples.
    for host in np.unique(d['src']):
        at = np.flatnonzero(d['src'] == host)
        first = host_data[str(host)]['first'] if str(host) in host_data else np.inf
        seen = d['start'][at] > first
        require(np.array_equal(a['availability'][at, 0], seen.astype(float)), 'all-row source visibility')
        require(np.all(a['availability'][at[~seen]] == 0) and np.all(a['auth'][at[~seen]] == 0), 'future source inventory affects past')
        require(np.all(a['wrong_auth'][at[~seen]] == 0) and np.all(a['donor'][at[~seen]] == ''), 'unseen source received donor')
    for donor in np.unique(a['donor']):
        if not donor: continue
        at = np.flatnonzero(a['donor'] == donor)
        require(str(donor) in host_data, 'unknown donor')
        require(np.all(d['start'][at] > host_data[str(donor)]['first']), 'future donor inventory')
        for source in np.unique(d['src'][at]):
            require(host_data[str(source)]['family'] == host_data[str(donor)]['family'], 'cross-family donor')
            require(common.independent_role(str(source)) == common.independent_role(str(donor)), 'cross-role donor')
    anchors = set(np.flatnonzero(d['y'] == 2).tolist())
    for split in range(3):
        rows = np.flatnonzero(d['split'] == split)
        anchors.update(rows[np.linspace(0, len(rows) - 1, min(12, len(rows)), dtype=int)].tolist())
    def count_auth(host, time):
        if host is None: return np.zeros(2 * k), -1.
        item = host_data[host]; prior = item['times'] < time
        vector = []
        for window in (300000., 1800000.):
            inside = prior & (item['times'] >= time - window)
            vector.extend(np.log1p(np.bincount(item['kinds'][inside], minlength=k)).tolist())
        latest = float(np.max(item['times'][prior])) if np.any(prior) else -1.
        return np.asarray(vector), latest
    for i in sorted(anchors):
        host, time = str(d['src'][i]), d['start'][i]
        available = np.zeros(7); auth, wrong = np.zeros(2 * k), np.zeros(2 * k)
        donor, latest, wrong_latest = '', -1., -1.
        if host in host_data and host_data[host]['first'] < time:
            item = host_data[host]; prior = item['observed'] < time
            available[0] = 1
            available[1:3] = [np.log1p(np.sum(prior & (item['observed'] >= time - window))) for window in (300000., 1800000.)]
            available[3] = np.log1p(min(1800000., time - np.max(item['observed'][prior])) / 1000.)
            available[4:6] = [item['family'] == 'linux_audit', item['family'] == 'windows_security']
            auth, latest = count_auth(host, time)
            choices = [other for other, values in host_data.items() if other != host and values['first'] < time
                       and values['family'] == item['family'] and common.independent_role(other) == common.independent_role(host)]
            if choices:
                donor = min(choices, key=lambda other: hashlib.sha256(f'AUTH_DONOR_V1|{host}|{other}'.encode()).digest())
                available[6] = 1; wrong, wrong_latest = count_auth(donor, time)
        for name, value in [('auth', auth), ('wrong_auth', wrong), ('availability', available)]:
            require(np.allclose(a[name][i], value, rtol=1e-11, atol=1e-11), 'independent feature arithmetic: ' + name)
        require(a['donor'][i] == donor and a['latest_auth'][i] == latest and a['latest_wrong_auth'][i] == wrong_latest, 'independent donor/latest provenance')
    expected_names = [f'prior_{int(window/60000)}m_{name}' for window in (300000., 1800000.) for name in events['kind_names']]
    require(a['feature_names'].tolist() == expected_names, 'auth feature names')
    return {'rows_with_strict_chronology_and_visibility_checked': n,
            'anchors_with_direct_event_filtering': len(anchors),
            'sampling': 'All movement anchors plus twelve distributed rows per acquisition split'}


def audit(protocol, prepared, run):
    spec = read(protocol)
    bindings = spec['bindings']
    resolved = {}
    for item in bindings:
        path = Path(item['path']).resolve()
        require(path not in resolved, 'duplicate frozen binding')
        require(digest(path) == item['sha256'], 'frozen artifact/source hash: ' + path.name)
        resolved[path] = item['sha256']
    base_prepared, base_run, events_root = Path(spec['base_prepared']), Path(spec['base_run']), Path(spec['events'])
    required = [SOURCE / name for name in ('features.py', 'policy.py', 'run.py', 'host_events.py')]
    required += [SOURCE.parent / 'host_history_exfil' / name for name in ('run.py', 'context.py')]
    required += [base_prepared / 'DATA.npz', events_root / 'EVENTS.npz', events_root / 'OBSERVED.npz', events_root / 'QUALIFICATION.json']
    required += [base_run / str(seed) / 'PREDICTIONS.npz' for seed in SEEDS]
    require(all(path.resolve() in resolved for path in required), 'essential frozen source/input omitted')
    started, summary, complete = (read(run / name) for name in ('STARTED.json', 'SUMMARY.json', 'COMPLETE.json'))
    require(complete == {'summary_sha256': digest(run / 'SUMMARY.json'), 'started_sha256': digest(run / 'STARTED.json')}, 'completion binding')
    require(started['protocol_sha256'] == digest(protocol), 'protocol/prefit binding')
    require(started['cloud_compute_started'] is False, 'compute receipt')
    for key, value in started.items(): compare(summary['receipt'][key], value, 'summary prefit copy ' + key)
    require(started['mode'] in ('prediction_replay', 'auth_fits_and_replay'), 'mode')
    is_auth = started['mode'] == 'auth_fits_and_replay'
    require(summary['receipt']['models_fitted'] == (21 if is_auth else 0), 'model count')
    require(summary['receipt']['saved_prediction_arms_replayed'] == 18, 'replay count')
    require([row['seed'] for row in summary['seeds']] == SEEDS, 'complete seed roster')
    d = arrays(base_prepared / 'DATA.npz')
    require(np.sum((d['split'] == 1) & (d['y'] == 2)) == 0, 'declared absent movement calibration changed')
    require(d['end'][d['split'] == 0].max() < d['start'][d['split'] == 1].min() and d['end'][d['split'] == 1].max() < d['start'][d['split'] == 2].min(), 'source temporal order')
    checks = {}
    if is_auth:
        prep, qualification = read(prepared / 'PREPARATION.json'), read(events_root / 'QUALIFICATION.json')
        require(prep['protocol_sha256'] == digest(protocol), 'auth preparation protocol binding')
        require(started['auth_preparation_sha256'] == digest(prepared / 'PREPARATION.json'), 'auth preparation receipt binding')
        require(prep['auth_sha256'] == started['auth_data_sha256'] == digest(prepared / 'AUTH.npz'), 'auth feature hash binding')
        for name, value in qualification['artifact_sha256'].items():
            require(name in ('EVENTS.npz', 'OBSERVED.npz') and digest(events_root / name) == value, 'qualification output hash')
        events, observed, a = arrays(events_root / 'EVENTS.npz'), arrays(events_root / 'OBSERVED.npz'), arrays(prepared / 'AUTH.npz')
        checks['qualification'] = qualification_check(events, observed, qualification, bindings)
        checks['features'] = feature_check(d, a, events, observed)
        compare(prep['feature_names'], a['feature_names'].tolist(), 'feature receipt names')
        compare(prep['availability_names'], a['availability_names'].tolist(), 'availability receipt names')
        counts = {}
        for split, name in enumerate(('fit', 'calibration', 'test')):
            counts[name] = {}
            for label, stage in enumerate(CLASSES):
                at = (d['split'] == split) & (d['y'] == label)
                counts[name][stage] = {'rows': int(at.sum()), 'source_observed_prior': int(np.sum(at & (a['availability'][:, 0] > 0))),
                                       'any_auth_in_30m': int(np.sum(at & np.any(a['auth'] > 0, axis=1))),
                                       'eligible_donor': int(np.sum(at & (a['availability'][:, 6] > 0)))}
        compare(prep['counts'], counts, 'auth coverage counts')
        require(prep['latest_auth_before_flow_start'] is True and prep['latest_wrong_auth_before_flow_start'] is True, 'chronology receipt')
    cells = []
    for seed, copy in zip(SEEDS, summary['seeds']):
        directory = run / str(seed); result = read(directory / 'METRICS.json')
        filenames = ['METRICS.json', 'PREDICTIONS.npz'] + ([name + '.joblib' for name in NEW_ARMS] if is_auth else [])
        common.artifact_hashes(directory, read(directory / 'COMPLETE.json')['files'], filenames)
        compare(result, copy, 'summary/seed result binding')
        p, prior = arrays(directory / 'PREDICTIONS.npz'), arrays(base_run / str(seed) / 'PREDICTIONS.npz')
        expected_keys = {'fit_indices', 'cal_indices', 'test_indices', 'cal_y', 'test_y'}
        if is_auth: expected_keys |= {name + '__' + split for name in NEW_ARMS for split in ('cal', 'test')}
        require(set(p) == expected_keys, 'new prediction roster')
        for name in ('fit_indices', 'cal_indices', 'test_indices', 'cal_y', 'test_y'):
            require(np.array_equal(p[name], prior[name]), 'original fitting/support identity: ' + name)
        fit, cal, test = (p[name] for name in ('fit_indices', 'cal_indices', 'test_indices'))
        require(np.array_equal(cal, np.flatnonzero(d['split'] == 1)) and np.array_equal(test, np.flatnonzero(d['split'] == 2)), 'all held-out rows required')
        require(np.array_equal(p['cal_y'], d['y'][cal]) and np.array_equal(p['test_y'], d['y'][test]), 'prepared labels binding')
        expected_fit = []
        for label, cap in enumerate((20000, 5000, 5000, 5000)):
            pool = np.flatnonzero((d['split'] == 0) & (d['y'] == label))
            expected_fit.extend(sorted(pool, key=lambda i: hashlib.sha256(f"HOST_HISTORY_V1|{seed}|{d['group_sha256'][i]}".encode()).digest())[:cap])
        require(np.array_equal(fit, expected_fit), 'independent original support sampling')
        base = np.argmax(prior['current__test'], axis=1)
        expected = {'seed': seed, 'fit_counts': np.bincount(d['y'][fit], minlength=4).tolist(), 'arms': {}}
        roster = [('prior_' + name, prior[name + '__cal'], prior[name + '__test']) for name in PRIOR_ARMS]
        if is_auth: roster += [(name, p[name + '__cal'], p[name + '__test']) for name in NEW_ARMS]
        for name, pc, pt in roster:
            common.probabilities(pc, len(cal)); common.probabilities(pt, len(test))
            expected['arms'][name] = independent_arm(d, cal, test, pc, pt, base)
        compare(result, expected, f'seed {seed} independently reconstructed')
        cells.append({'seed': seed, 'prediction_arms_checked': len(roster), 'policies_per_arm': 9,
                      'prediction_sha256': digest(directory / 'PREDICTIONS.npz'), 'complete_sha256': digest(directory / 'COMPLETE.json')})
    return {'audit_status': 'PASS', 'run_status': 'COMPLETE', 'audited_utc': datetime.now(timezone.utc).isoformat(),
            'auditor_sha256': digest(__file__), 'auditor_metric_helper_sha256': digest(common.__file__),
            'mode': started['mode'], 'models_audited': 21 if is_auth else 0, 'prediction_arms_audited': 39 if is_auth else 18,
            'policies_per_arm': 9, 'artifact_hashes': {name: digest(run / name) for name in ('SUMMARY.json', 'STARTED.json', 'COMPLETE.json')},
            'protocol_sha256': digest(protocol), 'frozen_input_bindings_verified': len(bindings), 'checks': checks, 'seed_receipts': cells,
            'limitations': ['No refitting, inference replay or model deserialization; model file hashes verified.',
                            'Export timezone arithmetic and saved joins verified; absolute cross-host synchronization and ingestion delay are unmeasured.',
                            'Event parser outputs hash-bound; this audit does not independently reparse every raw host message.',
                            'Direct auth arithmetic checks cover every movement anchor plus a fixed distributed sample, not every feature value.',
                            'Stage annotations are not independent proof of successful movement or data theft.',
                            'Zero movement calibration examples; support flags do not establish a movement-error guarantee.',
                            'Preservation of baseline alert flags is a policy invariant, not learned movement improvement.',
                            'One exposed campaign and shared later cases; fitting seeds are not independent attacks.']}


def main():
    parser = argparse.ArgumentParser()
    for name in ('protocol', 'prepared', 'run', 'output'):
        parser.add_argument('--' + name, type=Path, required=name != 'prepared')
    args = parser.parse_args()
    require(not args.output.exists(), 'fresh audit output required')
    try:
        result = audit(args.protocol, args.prepared, args.run)
    except Exception as exc:
        result = {'audit_status': 'FAIL', 'run_status': 'NOT_VERIFIED', 'error': str(exc), 'auditor_sha256': digest(__file__)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('audit_status', 'models_audited', 'prediction_arms_audited', 'checks')}))


if __name__ == '__main__':
    main()
