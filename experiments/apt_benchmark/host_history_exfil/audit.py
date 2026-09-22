"""Independent read-only audit of the completed host-history pilot.

No model deserialization, fitting, prediction, or imports from run/context.
Raw parsing, saved metrics, calibration choices and support selection are
recomputed. History arithmetic is independently spot-checked, not fully replayed.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import ipaddress
import json
import math
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score

CLASSES = ['Benign', 'OtherAttackStage', 'LateralMovement', 'DataExfiltration']
ROLES = ['OTHER_ADDRESS', 'DEPARTMENT', 'PUBLIC_SERVICES', 'PRIVATE_SERVICES']
ARMS = ['current', 'current_roles', 'current_history', 'current_roles_history',
        'current_roles_wrong_host_history', 'roles_only']
SEEDS = [20260922, 20260923, 20260924]
STAGES = {'Benign': 0, 'Reconnaissance': 1, 'Establish Foothold': 1,
          'Cover up': 1, 'Lateral Movement': 2, 'Data Exfiltration': 3}
SOURCE = Path(__file__).parent


class AuditError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AuditError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def compare(actual, expected, where='root'):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), where + ': keys')
        for key in expected:
            compare(actual[key], expected[key], where + '.' + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), where + ': length')
        for i, value in enumerate(expected):
            compare(actual[i], value, f'{where}[{i}]')
    elif isinstance(expected, (float, np.floating)):
        require(isinstance(actual, (float, int)) and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-11), where + ': numerical mismatch')
    else:
        require(actual == expected, where + ': value')


def probabilities(p, n):
    require(p.shape == (n, 4), 'probability shape')
    require(np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), 'probability range')
    require(np.allclose(p.sum(1), 1, rtol=1e-8, atol=1e-8), 'probability row sums')


def artifact_hashes(directory, hashes, expected):
    require(set(hashes) == set(expected), 'artifact roster')
    for name, checksum in hashes.items():
        require(Path(name).name == name, 'unsafe artifact name')
        require(digest(directory / name) == checksum, 'artifact hash: ' + name)


def independent_role(host):
    address = ipaddress.ip_address(host)
    if address.version != 4:
        return 0
    octets = host.split('.')
    if octets[:2] != ['10', '1']:
        return 0
    subnet = int(octets[2])
    return 1 if subnet in (1, 2, 3) else 2 if subnet == 4 else 3 if subnet == 5 else 0


def best_f1_threshold(y, scores):
    """Independent grouped frontier with exact integer ratio comparisons."""
    values, groups = np.unique(scores, return_inverse=True)
    total = np.bincount(groups, minlength=len(values))
    positives = np.bincount(groups, weights=y, minlength=len(values)).astype(np.int64)
    tp, fp, support = int(np.sum(y)), int(np.sum(~y)), int(np.sum(y))
    best, numerator, denominator = -1., 2 * tp, (support + tp + fp) or 1
    for value, count, positive in zip(values, total, positives):
        tp -= int(positive); fp -= int(count - positive)
        num, den = 2 * tp, (support + tp + fp) or 1
        if num * denominator >= numerator * den:
            best, numerator, denominator = float(value), num, den
    return best


def tail_threshold(scores, budget):
    allowed = int(Decimal(str(budget)) * len(scores))
    require(0 <= allowed < len(scores), 'tail rank unsupported')
    return float(np.sort(scores)[::-1][allowed])


def alert_counts(y, flags):
    counts = np.bincount(y[flags], minlength=4)
    tp, fp = int(counts[3]), int(counts[:3].sum())
    fn = int(np.sum(y == 3)) - tp
    return {'tp': tp, 'fp': fp, 'fn': fn,
            'precision': tp / (tp + fp) if tp + fp else 0.,
            'recall': tp / (tp + fn) if tp + fn else None,
            'f1': 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.,
            'false_exfil_by_true_class': {name: int(counts[k]) for k, name in enumerate(CLASSES[:3])}}


def metrics(y, p):
    predicted = np.argmax(p, axis=1)
    matrix = np.bincount(4 * y + predicted, minlength=16).reshape(4, 4)
    support, flagged = matrix.sum(axis=1), matrix.sum(axis=0)
    stages = {}
    for k, name in enumerate(CLASSES):
        tp = int(matrix[k, k]); den = int(support[k] + flagged[k])
        stages[name] = {
            'support': int(support[k]),
            'precision': tp / int(flagged[k]) if flagged[k] else 0.,
            'recall': tp / int(support[k]) if support[k] else 0.,
            'f1': 2 * tp / den if den else 0.,
            'ap': float(average_precision_score(y == k, p[:, k])) if support[k] else None,
            'roc_auc': float(roc_auc_score(y == k, p[:, k])) if 0 < support[k] < len(y) else None}
    pair = np.isin(y, [2, 3])
    score = p[pair, 3] / np.maximum(p[pair, 2] + p[pair, 3], 1e-12)
    return {'rows': len(y), 'macro_f1_all_four': float(np.mean([v['f1'] for v in stages.values()])),
            'confusion': matrix.tolist(), 'per_class': stages,
            'exfil_vs_lateral_ap': float(average_precision_score(y[pair] == 3, score)) if support[2] and support[3] else None,
            'exfil_vs_lateral_exfil_prevalence': float(np.mean(y[pair] == 3)) if pair.any() else None,
            'lateral_any_attack_recall': float(np.sum(matrix[2, 1:]) / support[2]) if support[2] else None,
            'benign_false_attack_count': int(matrix[0, 1:].sum())}


def expected_arm(d, cal, test, pc, pt):
    y = d['y']; threshold = best_f1_threshold(y[cal] == 3, pc[:, 3])
    result = {'test': metrics(y[test], pt),
              'exfil_f1_threshold': {'threshold': threshold, **alert_counts(y[test], pt[:, 3] > threshold)},
              'role_strata': {}, 'by_test_capture': {}, 'non_exfil_budget_thresholds': {}}
    for src, dst in sorted(set(zip(d['src_role'][test].tolist(), d['dst_role'][test].tolist()))):
        selected = (d['src_role'][test] == src) & (d['dst_role'][test] == dst)
        result['role_strata'][ROLES[src] + '->' + ROLES[dst]] = metrics(y[test][selected], pt[selected])
    for capture in np.unique(d['capture'][test]):
        selected = d['capture'][test] == capture
        result['by_test_capture'][str(capture)] = metrics(y[test][selected], pt[selected])
    negatives = pc[y[cal] != 3, 3]
    for budget in (.001, .005, .01, .02):
        cut = tail_threshold(negatives, budget)
        fpr = float(np.sum(negatives > cut) / len(negatives))
        require(fpr <= budget, 'strict tail empirical budget violated')
        result['non_exfil_budget_thresholds'][str(budget)] = {
            'threshold': cut, 'calibration_non_exfil_fpr': fpr, **alert_counts(y[test], pt[:, 3] > cut)}
    return result


def raw_data_check(d, manifest, receipt):
    """Reparse every qualified raw row and verify retained data without models."""
    excluded = {'id', 'expiration_id', 'src_ip', 'dst_ip', 'src_mac', 'dst_mac', 'src_oui',
                'dst_oui', 'src_port', 'dst_port', 'vlan_id', 'tunnel_id'}
    index = {str(key): i for i, key in enumerate(d['group_sha256'])}
    require(len(index) == len(d['y']), 'prepared duplicate observable keys')
    seen, raw_counts, raw_receipts = {}, 0, []
    expected_names = d['feature_names'].tolist()
    header = None
    for capture, item in enumerate(manifest['files']):
        path = Path(manifest['private_raw_root']) / item['source_file']
        require(digest(path) == item['sha256'], 'raw file hash: ' + item['source_file'])
        counts = Counter(); rows = 0
        with path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.reader(stream); names = next(reader)
            if header is None:
                header = names
            require(names == header and len(names) == 89, 'raw schema')
            positions = {name: j for j, name in enumerate(names)}
            features = [name for name in names[:77] if name not in excluded
                        and 'first_seen' not in name and 'last_seen' not in name]
            require(features + ['dst_remote_admin_service', 'dst_web_service', 'dst_dns_service'] == expected_names,
                    'raw feature selection')
            for rownum, row in enumerate(reader, 2):
                require(len(row) >= 89 and row[-3] in STAGES, 'raw annotation anchor')
                stage, signature = row[-3], row[-1]
                require(signature == 'None' if stage == 'Benign' else signature in {'APT', 'AA', 'SH'}, 'raw signature')
                src, dst = row[positions['src_ip']], row[positions['dst_ip']]
                require(src != dst, 'self-flow requires separately specified endpoint accounting')
                sport, dport = int(row[positions['src_port']]), int(row[positions['dst_port']])
                start, end = float(row[positions['bidirectional_first_seen_ms']]), float(row[positions['bidirectional_last_seen_ms']])
                nums = [float(row[positions[name]]) for name in features]
                nums.extend([float(dport in (22, 135, 139, 445, 3389, 5985, 5986)),
                             float(dport in (80, 443, 8080, 8443)), float(dport == 53)])
                require(np.isfinite(nums).all() and 0 < start <= end, 'raw nonfinite/time')
                key = hashlib.sha256(json.dumps([src, dst, sport, dport, start, end, *nums], separators=(',', ':')).encode()).hexdigest()
                label = STAGES[stage]
                state = seen.setdefault(key, [capture, rownum, 0, 0])
                state[2] |= 1 << label; state[3] += 1
                if key in index:
                    i = index[key]
                    require(np.array_equal(d['current'][i], nums), 'raw numeric predictor mismatch')
                    require(d['y'][i] == label and d['src'][i] == src and d['dst'][i] == dst,
                            'raw label/endpoint mismatch')
                    require(d['start'][i] == start and d['end'][i] == end, 'raw timestamp mismatch')
                    require(d['capture'][i] == state[0] and d['source_row'][i] == state[1], 'raw first-row provenance')
                    expected_split = {'fit': 0, 'calibration': 1, 'cal': 1, 'test': 2}[item['split']]
                    require(d['split'][i] == expected_split, 'raw capture split mismatch')
                rows += 1; counts[stage] += 1
        require(rows == item['rows'] and dict(counts) == item['right_anchored_stage_counts'], 'raw row/stage totals')
        raw_counts += rows
        raw_receipts.append({'source_file': item['source_file'], 'sha256': item['sha256'],
                             'rows': rows, 'right_anchored_stage_counts': dict(counts)})
    retained = {key for key, (_, _, mask, _) in seen.items() if mask.bit_count() == 1}
    require(retained == set(index), 'prepared retained/quarantined identity roster')
    duplicates = sum(count - 1 for _, _, mask, count in seen.values() if mask.bit_count() == 1)
    conflicts = sum(count for _, _, mask, count in seen.values() if mask.bit_count() > 1)
    require(receipt['duplicate_rows_removed'] == duplicates and receipt['conflicting_rows_quarantined'] == conflicts,
            'dedup/quarantine counts')
    compare(receipt['source_files'], raw_receipts, 'raw receipts')
    return {'raw_rows_verified': raw_counts, 'retained_rows_verified': len(index),
            'duplicate_rows_removed': duplicates, 'conflicting_rows_quarantined': conflicts,
            'raw_files_verified': len(raw_receipts)}


def history_spot_checks(d):
    """Direct event filtering, independent of the streaming implementation."""
    host_rows = defaultdict(list)
    for i, (src, dst) in enumerate(zip(d['src'], d['dst'])):
        host_rows[str(src)].append((i, True)); host_rows[str(dst)].append((i, False))
    hosts = sorted(host_rows)
    entries = {host: np.asarray(rows, dtype=np.int64) for host, rows in host_rows.items()}
    first_end = {host: float(np.min(d['end'][rows[:, 0]])) for host, rows in entries.items()}
    columns = {name: i for i, name in enumerate(d['feature_names'].tolist())}
    forward = d['current'][:, columns['src2dst_bytes']]
    reverse = d['current'][:, columns['dst2src_bytes']]
    admin = d['current'][:, columns['dst_remote_admin_service']]
    anchors = set(np.flatnonzero(d['y'] == 2).tolist())
    for split in range(3):
        pool = np.flatnonzero(d['split'] == split)
        anchors.update(pool[np.linspace(0, len(pool) - 1, min(12, len(pool)), dtype=int)].tolist())
    def direct(host, peer, at):
        if host is None or first_end[host] >= at:
            return [0.] * 18, -1.
        rows = entries[host]; indexes, outgoing = rows[:, 0], rows[:, 1].astype(bool)
        ends = d['end'][indexes]
        out, latest = [], -1.
        for window in (300_000, 1_800_000):
            take = (ends < at) & (ends >= at - window)
            ids, orientation = indexes[take], outgoing[take]
            peers = np.where(orientation, d['dst'][ids], d['src'][ids])
            tx = np.where(orientation, forward[ids], reverse[ids]).sum()
            rx = np.where(orientation, reverse[ids], forward[ids]).sum()
            internal = np.where(orientation, d['dst_role'][ids], d['src_role'][ids]) != 0
            raw = [len(ids), tx, rx, len(set(peers)), int(orientation.sum()), admin[ids].sum(), int(internal.sum())]
            out.extend([*np.log1p(raw).tolist(), float(peer in peers), 1.])
            if len(ids): latest = max(latest, float(d['end'][ids].max()))
        return out, latest
    for i in sorted(anchors):
        at = d['start'][i]
        observed = [host for host in hosts if first_end[host] < at]
        normal, wrong, latest, wrong_latest = [], [], -1., -1.
        for host, peer in ((str(d['src'][i]), str(d['dst'][i])), (str(d['dst'][i]), str(d['src'][i]))):
            donor = None
            if observed:
                position = int.from_bytes(hashlib.sha256(host.encode()).digest()[:8], 'big') % len(observed)
                if observed[position] == host: position = (position + 1) % len(observed)
                if observed[position] != host: donor = observed[position]
            a, last = direct(host, peer, at); b, wrong_last = direct(donor, peer, at)
            normal.extend(a); wrong.extend(b); latest = max(latest, last); wrong_latest = max(wrong_latest, wrong_last)
        require(np.allclose(d['history'][i], normal, rtol=1e-10, atol=1e-10), 'independent history arithmetic')
        require(np.allclose(d['wrong_history'][i], wrong, rtol=1e-10, atol=1e-10), 'independent wrong-host arithmetic')
        require(d['latest_history_end'][i] == latest and d['latest_wrong_history_end'][i] == wrong_latest, 'history max end')
    return {'history_anchors_independently_recomputed': len(anchors),
            'sampling': 'All lateral-stage anchors plus up to twelve index-spaced anchors per acquisition split',
            'windows_checked_per_anchor_per_policy': 4}


def audit(prepared, run, protocol):
    spec, prep = read(protocol), read(prepared / 'PREPARATION.json')
    manifest_path = SOURCE / 'PILOT_INPUTS.json'; manifest = read(manifest_path)
    require(spec['seeds'] == SEEDS and spec['classes'] == CLASSES and spec['arms'] == ARMS, 'frozen roster')
    require(spec['fit_caps_by_class'] == [20000, 5000, 5000, 5000] and spec['stage_mapping'] == STAGES, 'frozen support/stage mapping')
    require(spec['history_windows_ms'] == [300000, 1800000] and spec['roles'] == ROLES, 'frozen context')
    require(spec['input_manifest_sha256'] == digest(manifest_path) == prep['input_manifest_sha256'], 'input qualification binding')
    require(prep['data_sha256'] == digest(prepared / 'DATA.npz'), 'prepared data hash')
    require(prep['runner_sha256'] == digest(SOURCE / 'run.py') and prep['context_sha256'] == digest(SOURCE / 'context.py'), 'scientific source hash')
    complete, started, summary = (read(run / name) for name in ('COMPLETE.json', 'STARTED.json', 'SUMMARY.json'))
    require(complete == {'summary_sha256': digest(run / 'SUMMARY.json'), 'started_sha256': digest(run / 'STARTED.json')}, 'global completion binding')
    for key, value in {'protocol_sha256': digest(protocol), 'runner_sha256': prep['runner_sha256'],
                       'context_sha256': prep['context_sha256'], 'prepared_sha256': prep['data_sha256'],
                       'preparation_receipt_sha256': digest(prepared / 'PREPARATION.json')}.items():
        require(started[key] == value, 'prefit binding: ' + key)
    require(started['cloud_compute_started'] is False, 'compute receipt')
    require(summary['receipt']['models_fitted'] == 18, 'complete model count')
    for key, value in started.items(): compare(summary['receipt'][key], value, 'summary prefit ' + key)
    compare(summary['preparation'], prep, 'preparation copy')
    with np.load(prepared / 'DATA.npz', allow_pickle=False) as z:
        d = {name: z[name] for name in z.files}
    n = len(d['y'])
    require(n == prep['rows'] and set(np.unique(d['split'])) == {0, 1, 2}, 'prepared counts/split')
    require(np.isin(d['y'], np.arange(4)).all(), 'prepared labels')
    for key in ('current', 'roles', 'history', 'wrong_history'):
        require(len(d[key]) == n and np.isfinite(d[key]).all(), 'prepared finite features ' + key)
    require(d['roles'].shape == (n, 8) and d['history'].shape == (n, 36) and d['wrong_history'].shape == (n, 36), 'context dimensions')
    for key in ('latest_history_end', 'latest_wrong_history_end'):
        require(np.all(d[key] < d['start']), 'future/equal-time history guard')
    require(d['end'][d['split'] == 0].max() < d['start'][d['split'] == 1].min(), 'fit/cal temporal overlap')
    require(d['end'][d['split'] == 1].max() < d['start'][d['split'] == 2].min(), 'cal/test temporal overlap')
    role_map = {str(host): independent_role(str(host)) for host in set(d['src']) | set(d['dst'])}
    for side in ('src', 'dst'):
        expected = np.asarray([role_map[str(host)] for host in d[side]])
        require(np.array_equal(d[side + '_role'], expected), 'static topology roles')
        offset = 0 if side == 'src' else 4
        require(np.array_equal(d['roles'][:, offset:offset + 4], np.eye(4)[expected]), 'static role one-hot')
    split_counts = {name: dict(zip(CLASSES, np.bincount(d['y'][d['split'] == k], minlength=4).tolist()))
                    for k, name in enumerate(('fit', 'calibration', 'test'))}
    compare(prep['split_counts'], split_counts, 'split counts')
    require(split_counts['calibration']['LateralMovement'] == 0, 'declared calibration support changed')
    source_checks = raw_data_check(d, manifest, prep)
    history_checks = history_spot_checks(d)
    cal, test = np.flatnonzero(d['split'] == 1), np.flatnonzero(d['split'] == 2)
    require([row['seed'] for row in summary['seeds']] == SEEDS, 'summary seed roster')
    audited = []
    for seed, copied in zip(SEEDS, summary['seeds']):
        directory = run / str(seed)
        names = ['PREDICTIONS.npz', 'METRICS.json'] + [arm + '.joblib' for arm in ARMS]
        artifact_hashes(directory, read(directory / 'COMPLETE.json')['files'], names)
        result = read(directory / 'METRICS.json')
        compare(copied, result, 'summary seed copy')
        with np.load(directory / 'PREDICTIONS.npz', allow_pickle=False) as z:
            p = {name: z[name] for name in z.files}
        expected_keys = {'fit_indices', 'cal_indices', 'test_indices', 'cal_y', 'test_y'} | {arm + '__' + split for arm in ARMS for split in ('cal', 'test')}
        require(set(p) == expected_keys, 'prediction array roster')
        support = []
        for label, cap in enumerate(spec['fit_caps_by_class']):
            pool = np.flatnonzero((d['split'] == 0) & (d['y'] == label))
            order = sorted(pool, key=lambda i: hashlib.sha256(f"HOST_HISTORY_V1|{seed}|{d['group_sha256'][i]}".encode()).digest())
            support.extend(order[:cap])
        support = np.asarray(support, dtype=np.int64)
        for name, expected in {'fit_indices': support, 'cal_indices': cal, 'test_indices': test,
                               'cal_y': d['y'][cal], 'test_y': d['y'][test]}.items():
            require(np.array_equal(p[name], expected), 'prediction/support binding: ' + name)
        require(not (set(support) & set(cal)) and not (set(support) & set(test)) and not (set(cal) & set(test)), 'split disjointness')
        expected_result = {'seed': seed, 'fit_counts': dict(zip(CLASSES, np.bincount(d['y'][support], minlength=4).tolist())), 'arms': {}}
        for arm in ARMS:
            pc, pt = p[arm + '__cal'], p[arm + '__test']
            probabilities(pc, len(cal)); probabilities(pt, len(test))
            expected_result['arms'][arm] = expected_arm(d, cal, test, pc, pt)
        compare(result, expected_result, f'seed {seed} independent metrics')
        audited.append({'seed': seed, 'arms': len(ARMS), 'fit_rows': len(support),
                        'prediction_sha256': digest(directory / 'PREDICTIONS.npz'),
                        'complete_sha256': digest(directory / 'COMPLETE.json')})
    important = (d['src_role'] == 1) & (d['dst_role'] == 3)
    stratum_counts = {name: dict(zip(CLASSES, np.bincount(d['y'][important & (d['split'] == k)], minlength=4).tolist()))
                      for k, name in enumerate(('fit', 'calibration', 'test'))}
    require(stratum_counts['fit']['DataExfiltration'] == 0 and stratum_counts['calibration']['DataExfiltration'] == 0,
            'declared stratum shift changed')
    return {'audit_status': 'PASS', 'run_status': 'COMPLETE', 'audited_utc': datetime.now(timezone.utc).isoformat(),
            'auditor_sha256': digest(__file__), 'models_audited': 18, 'seeds_audited': 3,
            'artifact_hashes': {name: digest(run / name) for name in ('SUMMARY.json', 'STARTED.json', 'COMPLETE.json')},
            'bindings': {'protocol_sha256': digest(protocol), 'prepared_sha256': prep['data_sha256'],
                         'preparation_receipt_sha256': digest(prepared / 'PREPARATION.json'),
                         'input_manifest_sha256': digest(manifest_path),
                         'runner_sha256': prep['runner_sha256'], 'context_sha256': prep['context_sha256']},
            'source_checks': source_checks, 'history_checks': history_checks, 'split_counts': split_counts,
            'department_to_private_counts': stratum_counts, 'seed_receipts': audited,
            'limitations': ['Arithmetic and provenance audit, not independent verification of attack semantics.',
                            'No model refitting or inference replay; saved model files verified by hash only.',
                            'Histories independently recalculated at selected anchors; strict serialized time guards checked on every row.',
                            'No lateral calibration cases; no lateral threshold guarantee.',
                            'Single campaign temporal development evidence; current-flow features require flow completion.',
                            'History endpoint accounting verified on this corpus, which has no self-endpoint flows.']}


def main():
    parser = argparse.ArgumentParser()
    for name in ('prepared', 'run', 'protocol', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'fresh audit output required')
    try:
        result = audit(args.prepared, args.run, args.protocol)
    except Exception as exc:
        result = {'audit_status': 'FAIL', 'run_status': 'NOT_VERIFIED', 'error': str(exc),
                  'auditor_sha256': digest(__file__)}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        raise
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'audit_status': result['audit_status'], 'models_audited': result['models_audited'],
                      'source_checks': result['source_checks'], 'history_checks': result['history_checks']}))


if __name__ == '__main__':
    main()
