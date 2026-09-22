"""Independent saved-evidence audit for the controlled loopback stage lab.

This module never imports model fitting functions or the collector's outcome
classifier. Receipt/hash verification and numerical recomputation are independent.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
from pathlib import Path
import re

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, roc_auc_score


class AuditError(ValueError):
    pass


def require(condition: bool, message: str):
    if not condition:
        raise AuditError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_file_map(root: Path, expected: dict[str, str]):
    resolved_root = root.resolve()
    for relative, digest in expected.items():
        path = (resolved_root / relative).resolve()
        require(path.is_relative_to(resolved_root), 'Artifact path escapes its declared root')
        require(path.is_file(), f'Missing bound artifact: {relative}')
        require(sha256(path) == digest, f'Artifact hash differs: {relative}')


def compare(actual, expected, path='root'):
    """Recursive comparison that rejects nonfinite metrics and extra fields."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), f'Field mismatch at {path}')
        for key in expected:
            compare(actual[key], expected[key], f'{path}.{key}')
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f'List mismatch at {path}')
        for index, value in enumerate(expected):
            compare(actual[index], value, f'{path}[{index}]')
    elif isinstance(expected, float):
        require(isinstance(actual, (int, float)) and math.isfinite(actual)
                and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12),
                f'Numeric mismatch at {path}')
    else:
        require(actual == expected, f'Value mismatch at {path}')


def outcome_metrics(truth: np.ndarray, probabilities: np.ndarray,
                    predictions: np.ndarray) -> dict:
    truth, probabilities, predictions = map(np.asarray, (truth, probabilities, predictions))
    require(truth.ndim == 2 and truth.shape[1] == 2, 'Truth must have separate R/T outputs')
    require(probabilities.shape == truth.shape == predictions.shape, 'Prediction dimensions differ')
    require(bool(np.isin(truth, [0, 1]).all() and np.isin(predictions, [0, 1]).all()), 'Outcome values must be binary')
    require(bool(np.isfinite(probabilities).all() and (probabilities >= 0).all()
                 and (probabilities <= 1).all()), 'Invalid outcome probabilities')
    require(len(truth) > 0, 'An empty subset cannot receive a successful metric')
    outputs = {}
    for column, name in enumerate(['R', 'T']):
        y, pred, score = truth[:, column], predictions[:, column], probabilities[:, column]
        tn, fp, fn, tp = [int(v) for v in confusion_matrix(y, pred, labels=[0, 1]).ravel()]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0
        outputs[name] = {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
                         'precision': precision, 'recall': recall, 'f1': f1,
                         'prevalence': float(y.mean()),
                         'ap': float(average_precision_score(y, score)) if y.sum() else None,
                         'roc_auc': float(roc_auc_score(y, score)) if len(np.unique(y)) == 2 else None}
    truth_codes = truth[:, 0].astype(int) + 2 * truth[:, 1].astype(int)
    prediction_codes = predictions[:, 0].astype(int) + 2 * predictions[:, 1].astype(int)
    return {'rows': len(truth), 'outputs': outputs,
            'macro_f1': (outputs['R']['f1'] + outputs['T']['f1']) / 2,
            'exact_set_accuracy': float(np.all(truth == predictions, axis=1).mean()),
            'four_outcome_confusion': confusion_matrix(truth_codes, prediction_codes, labels=[0, 1, 2, 3]).tolist()}


def four_class_metrics(truth: np.ndarray, probabilities: np.ndarray) -> dict:
    truth, probabilities = np.asarray(truth), np.asarray(probabilities)
    require(truth.ndim == 1 and bool(np.isin(truth, [0, 1, 2, 3]).all()), 'Invalid four-outcome truth')
    require(probabilities.shape == (len(truth), 4), 'Four probability columns required')
    require(bool(np.isfinite(probabilities).all() and (probabilities >= 0).all()
                 and (probabilities <= 1).all()), 'Invalid four-outcome probabilities')
    require(bool(np.allclose(probabilities.sum(axis=1), 1, atol=1e-8, rtol=1e-8)),
            'Class probabilities do not sum to one')
    pred = probabilities.argmax(axis=1)
    bits = np.column_stack((truth & 1, (truth & 2) // 2))
    pred_bits = np.column_stack((pred & 1, (pred & 2) // 2))
    scores = np.column_stack((probabilities[:, 1] + probabilities[:, 3],
                              probabilities[:, 2] + probabilities[:, 3]))
    separate = outcome_metrics(bits, scores, pred_bits)
    return {'rows': len(truth), 'macro_f1': float(f1_score(truth, pred, labels=[0, 1, 2, 3], average='macro', zero_division=0)),
            'accuracy': float((truth == pred).mean()),
            'confusion': confusion_matrix(truth, pred, labels=[0, 1, 2, 3]).tolist(),
            'remote': separate['outputs']['R'], 'transfer': separate['outputs']['T']}


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def audit_collection(root: Path, collector_source: Path | None = None) -> tuple[dict, list[dict]]:
    """Return a sanitized receipt plus private joined rows for feature verification."""
    root = root.resolve()
    complete = read_json(root / 'COMPLETE.json')
    require(complete['receipt_sha256'] == sha256(root / 'COLLECT_RECEIPT.json'), 'Collection completion binding differs')
    receipt = read_json(root / 'COLLECT_RECEIPT.json')
    require(receipt['status'] == 'COMPLETE', 'Collection is not complete')
    require(set(receipt['artifact_hashes']) == {'MANIFEST.json', 'WORKERS.json', 'TELEMETRY.jsonl', 'FLOW.jsonl', 'TRUTH.jsonl'},
            'Collection receipt omits a required raw stream')
    verify_file_map(root, receipt['artifact_hashes'])
    source = collector_source or Path(__file__).with_name('collector.py')
    require(receipt['source_sha256'] == sha256(source), 'Collector source differs from its receipt')
    manifest = read_json(root / 'MANIFEST.json')
    require(manifest['source_sha256'] == receipt['source_sha256'], 'Manifest collector source differs')
    require(receipt['manifest_sha256'] == sha256(root / 'MANIFEST.json'), 'Manifest hash differs')
    require(manifest['episodes_per_block_per_rep'] == 48, 'Unexpected collection roster')
    require(manifest['scheme'] == {'prior_masks': [0, 1, 2, 3], 'requested_masks': [0, 1, 2, 3],
                                  'modes': ['success', 'auth_denied', 'operation_fail']}, 'Collection cells differ')
    expected_count = manifest['blocks'] * manifest['reps'] * 48
    require(manifest['planned_current_episodes'] == expected_count == receipt['completed_episodes']
            == receipt['planned_episodes'], 'Incomplete collection roster')
    workers = read_json(root / 'WORKERS.json')
    require(workers['all_loopback'] is True and receipt['local_loopback_only'] is True,
            'This audit only covers the declared loopback topology')
    worker_map = {w['host']: w for w in workers['workers']}
    require(set(worker_map) == {'worker_0', 'worker_1', 'worker_2'}, 'Worker roster differs')
    require(len({w['pid'] for w in worker_map.values()}) == 3, 'Three distinct worker processes required')
    require(len({w['port'] for w in worker_map.values()}) == 3, 'Workers must bind distinct ports')
    truth = read_jsonl(root / 'TRUTH.jsonl')
    flows = read_jsonl(root / 'FLOW.jsonl')
    telemetry = read_jsonl(root / 'TELEMETRY.jsonl')
    require(len(truth) == expected_count and len(flows) == 2 * expected_count == receipt['peer_rpc_count'],
            'Recorded episode/flow counts differ')
    require(len({r['episode'] for r in truth}) == len(truth), 'Repeated execution episode identifier')
    flow_map = {}
    for flow in flows:
        key = (flow['episode'], flow['phase'])
        require(key not in flow_map and flow['phase'] in {'prior', 'current'}, 'Duplicate or unknown flow phase')
        require(flow['src'] in worker_map and flow['dst'] in worker_map and flow['src'] != flow['dst'],
                'Remote-action analogue must involve distinct processes')
        require(type(flow['start_ns']) is int and type(flow['end_ns']) is int
                and 0 < flow['start_ns'] < flow['end_ns'] <= flow['controllerarrival_ns'], 'Invalid monotonic flow interval')
        require(flow['response_bytes'] == 256 and flow['status'] in [200, 401, 500], 'RPC observation contract differs')
        flow_map[key] = flow
    event_map = {}
    for event in telemetry:
        require(set(event) == {'block', 'episode', 'phase', 'time_ns', 'eventtime_ns', 'controllerarrival_ns',
                               'host', 'kind', 'success', 'bytes'}, 'Unexpected observation fields')
        key = (event['episode'], event['phase'])
        require(key in flow_map, 'Telemetry has no matching flow')
        require(event['kind'] in {'authentication', 'remote_job', 'file_write', 'request_end'}, 'Unknown telemetry kind')
        require(type(event['success']) is bool and type(event['bytes']) is int and event['bytes'] >= 0,
                'Invalid service observation')
        flow = flow_map[key]
        require(event['host'] == flow['dst'] and event['block'] == flow['block'], 'Observation host/block differs')
        require(flow['start_ns'] <= event['time_ns'] <= flow['end_ns'], 'Observation outside its RPC interval')
        require(event['time_ns'] == event['eventtime_ns']
                and event['controllerarrival_ns'] >= flow['end_ns'], 'Invalid observation arrival or source time')
        event_map.setdefault(key, []).append(event)
    all_nonces, artifact_digests, joined = set(), {}, []
    completed_counts = {str(i): 0 for i in range(4)}
    block_cells = {}
    for row in truth:
        require(row['src'] in worker_map and row['dst'] in worker_map and row['src'] != row['dst'], 'Invalid truth endpoint pair')
        require(row['prior_mask'] in range(4) and row['requested_mask'] in range(4)
                and row['mode'] in ['success', 'auth_denied', 'operation_fail'], 'Invalid manifest cell')
        cell = (row['prior_mask'], row['requested_mask'], row['mode'], row['repetition'])
        cells = block_cells.setdefault(row['block'], set())
        require(cell not in cells, 'Repeated collection cell within a block')
        cells.add(cell)
        phase_rows = {}
        for phase in ['prior', 'current']:
            key = (row['episode'], phase)
            require(key in flow_map and key in event_map, 'Missing episode phase')
            flow = flow_map[key]
            require(flow['src'] == row['src'] and flow['dst'] == row['dst'] and flow['block'] == row['block'],
                    'Flow and truth linkage differs')
            nonce = row[f'{phase}_nonce']
            require(isinstance(nonce, str) and bool(re.fullmatch('[0-9a-f]{32}', nonce))
                    and nonce not in all_nonces, 'Invalid or reused nonce')
            all_nonces.add(nonce)
            payload_path = root / 'payloads' / f'{nonce}.bin'
            payload = payload_path.read_bytes()
            require(len(payload) == row['payload_bytes'] and len(payload) in manifest['payload_buckets']
                    and hashlib.sha256(payload).hexdigest() == row['payload_sha256'], 'Independent dummy payload differs')
            # Verify that operation/mode digits do not change allowed request-body size.
            envelope = {'nonce': '0' * 32, 'capability': '0' * 64, 'operation': 0,
                        'gate': 0, 'payload_hex': '0' * (2 * len(payload))}
            expected_bytes = len(json.dumps(envelope, separators=(',', ':'), sort_keys=True).encode())
            require(flow['request_bytes'] == expected_bytes, 'Request size encodes more than the permitted envelope/payload')
            prefix = '' if phase == 'current' else 'prior_'
            expected_receipt = f"workers/{row['dst']}/receipts/{nonce}.json"
            require(row[prefix + 'receipt_relpath'] == expected_receipt, 'Worker receipt path differs')
            receipt_path = root / expected_receipt
            require(sha256(receipt_path) == row[prefix + 'receipt_sha256'], 'Worker receipt hash differs')
            worker = read_json(receipt_path)
            require(worker['version'] == 1 and worker['nonce'] == nonce and worker['worker'] == row['dst']
                    and worker['worker_pid'] == worker_map[row['dst']]['pid'], 'Receipt process/nonce binding differs')
            require(worker['received_payload_bytes'] == len(payload)
                    and worker['received_payload_sha256'] == hashlib.sha256(payload).hexdigest(), 'Receiver payload differs')
            require(worker['response_status'] == flow['status'], 'Worker response and traffic status differ')
            stripped = [{k: v for k, v in event.items() if k not in {'block', 'episode', 'phase', 'eventtime_ns', 'controllerarrival_ns'}}
                        for event in event_map[key]]
            compare(stripped, worker['events'], 'worker_observation_channel')
            require([e['kind'] for e in worker['events']].count('authentication') == 1
                    and worker['events'][0]['kind'] == 'authentication'
                    and worker['events'][-1]['kind'] == 'request_end', 'Service observation boundaries differ')
            mask = 0
            worker_root = root / 'workers' / row['dst']
            remote_path = worker_root / 'remote_results' / f'{nonce}.json'
            marker = worker['remote_artifact']
            if marker is None:
                require(not remote_path.exists(), 'Unbound remote completion artifact')
            else:
                require(marker['relative_path'] == f'remote_results/{nonce}.json'
                        and marker['sha256'] == sha256(remote_path), 'Remote artifact binding differs')
                actual = read_json(remote_path)
                require(actual['completed_ns'] == marker['completed_ns']
                        and flow['start_ns'] <= actual['completed_ns'] <= flow['end_ns'], 'Remote completion is outside cutoff')
                expected = hashlib.sha256(b'FIXED_REMOTE_HASH_V1\x00' + nonce.encode('ascii') + b'\x00' + payload).hexdigest()
                if (actual['version'] == 'FIXED_REMOTE_HASH_V1' and actual['nonce'] == nonce
                        and actual['worker'] == row['dst'] and actual['result_sha256'] == expected):
                    mask |= 1
                artifact_digests[remote_path.relative_to(root).as_posix()] = sha256(remote_path)
            transfer_path = worker_root / 'received' / f'{nonce}.bin'
            marker = worker['transfer_artifact']
            if marker is None:
                require(not transfer_path.exists(), 'Unbound transfer artifact')
            else:
                require(marker['relative_path'] == f'received/{nonce}.bin'
                        and marker['sha256'] == sha256(transfer_path)
                        and marker['bytes'] == transfer_path.stat().st_size, 'Transfer artifact binding differs')
                require(flow['start_ns'] <= marker['completed_ns'] <= flow['end_ns'], 'Transfer completion is outside cutoff')
                if transfer_path.read_bytes() == payload:
                    mask |= 2
                artifact_digests[transfer_path.relative_to(root).as_posix()] = sha256(transfer_path)
            expected_mask = row['completed_mask'] if phase == 'current' else row['prior_mask']
            require(mask == expected_mask, 'Recorded outcome differs from independently verified completion')
            artifact_digests[payload_path.relative_to(root).as_posix()] = sha256(payload_path)
            artifact_digests[expected_receipt] = sha256(receipt_path)
            phase_rows[phase] = {'flow': flow, 'events': event_map[key], 'verified_mask': mask}
        require(phase_rows['prior']['flow']['end_ns'] < phase_rows['current']['flow']['start_ns'],
                'Prelude does not strictly precede the current request')
        for event in phase_rows['prior']['events']:
            require(event['time_ns'] < phase_rows['current']['flow']['start_ns'], 'Future/equal prior observation')
            require(event['controllerarrival_ns'] < phase_rows['current']['flow']['start_ns'], 'Prelude observation arrived after current start')
        completed_counts[str(row['completed_mask'])] += 1
        joined.append({'truth': row, **phase_rows})
    expected_cells = set(itertools.product(range(4), range(4), ['success', 'auth_denied', 'operation_fail'], range(manifest['reps'])))
    require(set(block_cells) == set(range(manifest['blocks']))
            and all(cells == expected_cells for cells in block_cells.values()), 'Collection manifest crossing is incomplete')
    compare(receipt['completed_mask_counts'], completed_counts, 'completion_counts')
    evidence_digest = hashlib.sha256(json.dumps(artifact_digests, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    sanitized = {'audit_status': 'PASS', 'executions': len(truth), 'blocks': manifest['blocks'],
                 'peer_rpc_flows': len(flows), 'service_observations': len(telemetry),
                 'completed_mask_counts': completed_counts, 'unique_nonces': len(all_nonces),
                 'verified_private_artifact_count': len(artifact_digests),
                 'private_artifact_hash_map_sha256': evidence_digest,
                 'collection_receipt_sha256': sha256(root / 'COLLECT_RECEIPT.json'),
                 'collector_source_sha256': sha256(source),
                 'scope': 'Three loopback processes performing fixed harmless RPCs; completed remote-action and dummy-transfer analogues, not APT detection.'}
    return sanitized, joined


CONDITIONS = ('clean', 'drop_remote', 'drop_file', 'delay50ms', 'role_permutation')
KINDS = ('authentication', 'remote_job', 'file_write', 'request_end')
ARMS = ('current', 'current_roles', 'current_history', 'current_roles_history',
        'current_roles_wrong_history', 'history_only', 'timing_diagnostic')
CLASSES = ('Neither', 'RemoteAction', 'FileTransfer', 'Both')
CURRENT_NAMES = ('log_request_body_bytes', 'log_response_body_bytes', 'status200', 'status401', 'status500',
                 'log_prior_record_count', 'prior_records_observed', 'earlier_wrong_source_exists',
                 'remote_channel_available', 'file_channel_available')
HISTORY_NAMES = tuple(f'prior_{kind}_{field}' for kind in KINDS for field in ('log_count', 'log_success_count', 'log_bytes'))


def reconstruct_data(joined: list[dict]) -> dict:
    """Reconstruct every prepared feature without importing the feature builder."""
    ordered = sorted(joined, key=lambda r: r['current']['flow']['start_ns'])
    flows = [r['current']['flow'] for r in ordered]
    truth = [r['truth'] for r in ordered]
    n = len(flows)
    hosts = ['worker_0', 'worker_1', 'worker_2']
    require(all(f['src'] in hosts and f['dst'] in hosts for f in flows), 'Unknown predeclared process role')
    role_matrix = np.zeros((n, 6))
    for i, f in enumerate(flows):
        role_matrix[i, hosts.index(f['src'])] = 1
        role_matrix[i, 3 + hosts.index(f['dst'])] = 1
    donors = np.full(n, -1, dtype=int)
    for i, f in enumerate(flows):
        candidates = [j for j in range(i) if flows[j]['block'] == f['block']
                      and flows[j]['src'] != f['src'] and flows[j]['end_ns'] < f['start_ns']]
        if candidates:
            donors[i] = candidates[-1]
    d = {'episode': np.asarray([f['episode'] for f in flows]), 'block': np.asarray([f['block'] for f in flows]),
         'src': np.asarray([f['src'] for f in flows]), 'dst': np.asarray([f['dst'] for f in flows]),
         'start_ns': np.asarray([f['start_ns'] for f in flows], dtype=np.int64),
         'end_ns': np.asarray([f['end_ns'] for f in flows], dtype=np.int64), 'donor': donors,
         'roles': role_matrix, 'timing': np.log1p(np.asarray([f['end_ns'] - f['start_ns'] for f in flows], dtype=float) / 1e6)[:, None],
         'current_names': np.asarray(CURRENT_NAMES), 'history_names': np.asarray(HISTORY_NAMES),
         'y': np.asarray([r['completed_mask'] for r in truth]),
         'prior_mask': np.asarray([r['prior_mask'] for r in truth]),
         'requested_mask': np.asarray([r['requested_mask'] for r in truth])}
    d['linked'] = d['prior_mask'] == d['requested_mask']
    d['split'] = np.select([d['block'] < 24, d['block'] < 32], [0, 1], default=2)
    for condition in CONDITIONS:
        base = np.zeros((n, 10))
        history = np.zeros((n, 12))
        latest = np.full(n, -1, dtype=np.int64)
        for i, f in enumerate(flows):
            selected = []
            for event in ordered[i]['prior']['events']:
                arrival = event['controllerarrival_ns'] + (50_000_000 if condition == 'delay50ms' else 0)
                if event['time_ns'] >= f['start_ns'] or arrival >= f['start_ns']:
                    continue
                if (condition == 'drop_remote' and event['kind'] == 'remote_job'
                        or condition == 'drop_file' and event['kind'] == 'file_write'):
                    continue
                selected.append(event)
                latest[i] = max(latest[i], arrival)
            for j, kind in enumerate(KINDS):
                matched = [e for e in selected if e['kind'] == kind]
                history[i, 3 * j:3 * j + 3] = np.log1p([len(matched), sum(e['success'] for e in matched),
                                                       sum(e['bytes'] for e in matched)])
            base[i] = [np.log1p(f['request_bytes']), np.log1p(f['response_bytes']), f['status'] == 200,
                       f['status'] == 401, f['status'] == 500, np.log1p(len(selected)), bool(selected),
                       donors[i] >= 0, condition != 'drop_remote', condition != 'drop_file']
        wrong = np.zeros_like(history)
        for i, donor in enumerate(donors):
            if donor >= 0:
                require(d['end_ns'][donor] < d['start_ns'][i] and d['block'][donor] == d['block'][i],
                        'Wrong-source donor violates causality or block boundary')
                wrong[i] = history[donor]
        roles = role_matrix.copy()
        if condition == 'role_permutation':
            roles = role_matrix[:, [2, 0, 1, 5, 3, 4]]
        d[condition + '__current'] = base
        d[condition + '__history'] = history
        d[condition + '__wrong_history'] = wrong
        d[condition + '__roles'] = roles
        d[condition + '__latest_arrival'] = latest
    return d


def audit_preparation(prepared: Path, protocol: Path, collection: Path, joined: list[dict]) -> tuple[dict, dict]:
    spec = read_json(protocol)
    require(spec['status'] == 'FROZEN_BEFORE_COLLECTION_AND_FITS', 'Protocol is not frozen')
    verify_file_map(Path(__file__).parent, spec['source_bindings'])
    manifest = read_json(collection / 'MANIFEST.json')
    expected_collection = spec['collection']
    require(all(manifest[key] == expected_collection[key] for key in ['seed', 'blocks', 'reps'])
            and manifest['episodes_per_block_per_rep'] == expected_collection['transactions_per_block']
            and manifest['planned_current_episodes'] == expected_collection['expected_current_transactions']
            and len(manifest['worker_hosts']) == expected_collection['workers'],
            'Collected execution roster or randomization differs from frozen protocol')
    require(spec['fit_blocks'] == list(range(24)) and spec['calibration_blocks'] == list(range(24, 32))
            and spec['test_blocks'] == list(range(32, 48)), 'Execution block split differs')
    require(tuple(spec['arms']) == ARMS and tuple(spec['conditions']) == CONDITIONS, 'Model/condition roster differs')
    prep = read_json(prepared / 'PREPARATION.json')
    require(prep['protocol_sha256'] == sha256(protocol) and prep['data_sha256'] == sha256(prepared / 'DATA.npz'),
            'Prepared data/protocol binding differs')
    require(prep['collection_receipt_sha256'] == sha256(collection / 'COLLECT_RECEIPT.json'), 'Prepared collection binding differs')
    expected = reconstruct_data(joined)
    with np.load(prepared / 'DATA.npz', allow_pickle=False) as archive:
        require(set(archive.files) == set(expected), 'Prepared feature field inventory differs')
        actual = {k: archive[k] for k in archive.files}
    for name, value in expected.items():
        require(np.array_equal(actual[name], value), f'Prepared values differ from observable reconstruction: {name}')
    require(len(actual['y']) == 2304, 'Full frozen execution roster required')
    counts = {}
    for split, name in enumerate(['fit', 'calibration', 'test']):
        counts[name] = {}
        for linked, population in [(True, 'linked'), (False, 'crossed')]:
            idx = np.flatnonzero((actual['split'] == split) & (actual['linked'] == linked))
            counts[name][population] = {'rows': len(idx), 'outcomes': dict(zip(CLASSES, np.bincount(actual['y'][idx], minlength=4).tolist()))}
    compare(prep['counts'], counts, 'prepared_counts')
    return actual, {'audit_status': 'PASS', 'rows': len(actual['y']), 'counts': counts,
                    'all_feature_arrays_reconstructed': True, 'main_arms_exclude_timing': True,
                    'same_current_observation_controls': True, 'source_split_unit': 'complete execution block',
                    'role_permutation_scope': 'logical role metadata counterfactual on the same recorded processes',
                    'prepared_sha256': sha256(prepared / 'DATA.npz'), 'protocol_sha256': sha256(protocol)}


def reported_metrics(truth: np.ndarray, probabilities: np.ndarray) -> dict:
    """Match the public runner schema using independent confusion arithmetic."""
    checked = four_class_metrics(truth, probabilities)
    matrix = np.asarray(checked['confusion'])
    per_class = {}
    for i, name in enumerate(CLASSES):
        tp, support, predicted = int(matrix[i, i]), int(matrix[i].sum()), int(matrix[:, i].sum())
        per_class[name] = {'precision': tp / predicted if predicted else 0.,
                           'recall': tp / support if support else 0.,
                           'f1': 2 * tp / (support + predicted) if support + predicted else 0., 'support': support}
    outcomes = {}
    for name in ['remote', 'transfer']:
        m = checked[name]
        outcomes[name] = {key: m[key] for key in ['tp', 'fp', 'fn', 'precision', 'recall', 'f1', 'ap', 'roc_auc']}
        if m['tp'] + m['fn'] == 0:
            outcomes[name]['recall'] = None
    return {'rows': checked['rows'], 'accuracy': checked['accuracy'], 'macro_f1': checked['macro_f1'],
            'confusion': checked['confusion'], 'per_class': per_class, 'outcomes': outcomes}


def audit_models(run: Path, prepared: Path, protocol: Path, data: dict) -> dict:
    import joblib
    spec = read_json(protocol)
    complete = read_json(run / 'COMPLETE.json')
    require(complete['summary_sha256'] == sha256(run / 'SUMMARY.json')
            and complete['started_sha256'] == sha256(run / 'STARTED.json'), 'Run completion hashes differ')
    summary = read_json(run / 'SUMMARY.json')
    receipt = summary['receipt']
    require(receipt['protocol_sha256'] == sha256(protocol)
            and receipt['prepared_sha256'] == sha256(prepared / 'DATA.npz')
            and receipt['preparation_sha256'] == sha256(prepared / 'PREPARATION.json'), 'Run input bindings differ')
    compare(summary['preparation'], read_json(prepared / 'PREPARATION.json'), 'summary_preparation')
    for key, value in read_json(run / 'STARTED.json').items():
        compare(receipt[key], value, 'started_receipt.' + key)
    require(receipt['models_fitted'] == 21, 'Incomplete model roster')
    fit_idx = np.flatnonzero((data['split'] == 0) & data['linked'])
    cal_idx = np.flatnonzero((data['split'] == 1) & data['linked'])
    groups = {name: np.flatnonzero((data['split'] == 2) & (data['linked'] == linked))
              for name, linked in [('linked', True), ('crossed', False)]}
    groups['factorial_all'] = np.flatnonzero(data['split'] == 2)
    require(len(fit_idx) == 288 and len(cal_idx) == 96 and len(groups['linked']) == 192
            and len(groups['crossed']) == 576 and len(groups['factorial_all']) == 768,
            'Frozen subset denominators differ')
    require(set(data['block'][fit_idx]).isdisjoint(data['block'][cal_idx])
            and set(data['block'][fit_idx]).isdisjoint(data['block'][groups['linked']])
            and set(data['block'][cal_idx]).isdisjoint(data['block'][groups['crossed']]), 'Block overlap across partitions')
    seeds = [20260922, 20260923, 20260924]
    require(spec['seeds'] == seeds and [v['seed'] for v in summary['seeds']] == seeds, 'Seed roster differs')
    metrics_checked = 0
    seed_summaries = []
    feature_counts = dict(zip(ARMS, [10, 16, 22, 28, 28, 17, 29]))
    for seed, recorded in zip(seeds, summary['seeds']):
        folder = run / str(seed)
        files = read_json(folder / 'COMPLETE.json')['files']
        require(set(files) == {'PREDICTIONS.npz', 'METRICS.json'} | {a + '.joblib' for a in ARMS}, 'Cell completion file inventory differs')
        verify_file_map(folder, files)
        compare(recorded, read_json(folder / 'METRICS.json'), 'seed_summary_binding')
        with np.load(folder / 'PREDICTIONS.npz', allow_pickle=False) as archive:
            preds = {k: archive[k] for k in archive.files}
        expected_keys = {'fit_indices', 'cal_indices', 'linked_indices', 'crossed_indices', 'factorial_all_indices'} | {a + '__cal' for a in ARMS}
        expected_keys |= {f'{a}__{c}__{p}' for a in ARMS for c in CONDITIONS for p in groups}
        require(set(preds) == expected_keys, 'Prediction array inventory differs')
        for key, value in [('fit_indices', fit_idx), ('cal_indices', cal_idx), *[(k + '_indices', v) for k, v in groups.items()]]:
            require(np.array_equal(preds[key], value), 'Saved fitting/evaluation identities differ')
        expected_arms = {}
        for arm in ARMS:
            # The hash-bound estimator is only inspected; never refitted or queried.
            model = joblib.load(folder / (arm + '.joblib'))
            require(type(model).__module__ == 'lightgbm.sklearn' and type(model).__name__ == 'LGBMClassifier', 'Unexpected fitted estimator type')
            parameters = model.get_params()
            for key, value in {**spec['parameters'], 'random_state': seed, 'n_jobs': 4,
                               'deterministic': True, 'force_col_wise': True, 'verbosity': -1}.items():
                require(parameters[key] == value, f'Fitted parameter differs: {arm}/{key}')
            require(np.array_equal(model.classes_, np.arange(4)) and model.n_features_in_ == feature_counts[arm],
                    'Estimator class/feature inventory differs')
            four_class_metrics(data['y'][cal_idx], preds[arm + '__cal'])
            expected_arms[arm] = {}
            for condition in CONDITIONS:
                expected_arms[arm][condition] = {}
                for population, idx in groups.items():
                    p = preds[f'{arm}__{condition}__{population}']
                    ok = data['clean__current'][idx, 2] > 0
                    expected_arms[arm][condition][population] = {
                        'all': reported_metrics(data['y'][idx], p),
                        'status200_only': reported_metrics(data['y'][idx][ok], p[ok])}
                    metrics_checked += 2
        compare(recorded['arms'], expected_arms, f'seed{seed}.arms')
        comparisons = {}
        for name in ['majority', 'prior_evidence_rule']:
            comparisons[name] = {}
            for condition in CONDITIONS:
                if name == 'majority':
                    labels = np.repeat(np.bincount(data['y'][fit_idx], minlength=4).argmax(), len(data['y']))
                else:
                    h, c = data[condition + '__history'], data[condition + '__current']
                    labels = ((h[:, 4] > 0).astype(int) + 2 * (h[:, 7] > 0).astype(int)) * (c[:, 2] > 0)
                p = np.eye(4)[labels]
                comparisons[name][condition] = {}
                for population, idx in groups.items():
                    ok = data['clean__current'][idx, 2] > 0
                    comparisons[name][condition][population] = {'all': reported_metrics(data['y'][idx], p[idx]),
                                                               'status200_only': reported_metrics(data['y'][idx][ok], p[idx][ok])}
                    metrics_checked += 2
        compare(recorded['comparators'], comparisons, f'seed{seed}.comparators')
        twins = {}
        for arm in ARMS:
            twins[arm] = {}
            for population, idx in groups.items():
                eligible = data['y'][idx] != 0
                probabilities = preds[f'{arm}__clean__{population}'][eligible]
                binary_scores = np.repeat(1 - probabilities[:, 0], 2)
                hidden_truth = np.tile([False, True], int(eligible.sum()))
                predicted = np.repeat(probabilities.argmax(axis=1) != 0, 2)
                twins[arm][population] = {'underlying_completed_operations': int(eligible.sum()),
                                         'counterfactual_rows': int(2 * eligible.sum()),
                                         'accuracy': float((predicted == hidden_truth).mean()),
                                         'roc_auc': float(roc_auc_score(hidden_truth, binary_scores)),
                                         'policy_context_supplied': False, 'separate_physical_executions': False}
                require(twins[arm][population]['accuracy'] == .5
                        and math.isclose(twins[arm][population]['roc_auc'], .5, abs_tol=1e-12),
                        'Identical-observation hidden-policy diagnostic exceeds identifiability bound')
        compare(recorded['hidden_policy_twins'], twins, f'seed{seed}.twins')
        seed_summaries.append({'seed': seed, 'models': len(ARMS), 'prediction_sha256': sha256(folder / 'PREDICTIONS.npz'),
                               'metrics_sha256': sha256(folder / 'METRICS.json')})
    return {'audit_status': 'PASS', 'models_audited': 21, 'metric_tables_recomputed': metrics_checked,
            'seed_receipts': seed_summaries, 'hidden_policy_twins': 'PASS_IDENTICAL_OBSERVATION_50_PERCENT_BOUND',
            'summary_sha256': sha256(run / 'SUMMARY.json'),
            'scope': 'Saved prediction and provenance verification only; no model fits or inference.'}


def main():
    import argparse
    from datetime import datetime, timezone
    parser = argparse.ArgumentParser()
    parser.add_argument('--collection', type=Path, required=True)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--run', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), 'Use a fresh audit output path')
    raw, joined = audit_collection(args.collection)
    result = {'audit_status': 'PASS', 'audited_utc': datetime.now(timezone.utc).isoformat(),
              'auditor_sha256': sha256(Path(__file__)), 'collection': raw}
    if args.prepared is not None:
        require(args.protocol is not None, 'Prepared audit requires its frozen protocol')
        data, prep = audit_preparation(args.prepared, args.protocol, args.collection, joined)
        result['preparation'] = prep
        if args.run is not None:
            result['models'] = audit_models(args.run, args.prepared, args.protocol, data)
    else:
        require(args.run is None, 'Model audit requires prepared data')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'audit_status': result['audit_status'], 'executions': raw['executions'],
                      'models_audited': result.get('models', {}).get('models_audited', 0)}))


if __name__ == '__main__':
    main()
