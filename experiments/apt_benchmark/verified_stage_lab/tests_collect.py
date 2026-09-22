"""Actual bounded process integration and independent completion checks."""
import hashlib
import json
from pathlib import Path

import pytest

from experiments.apt_benchmark.verified_stage_lab import collector


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines()]


@pytest.fixture(scope='module')
def collected(tmp_path_factory):
    root = tmp_path_factory.mktemp('mechanism_lab') / 'collection'
    receipt = collector.collect(root, seed=991, blocks=1)
    return root, receipt


def test_all_crossed_cases_are_real_peer_process_requests(collected):
    root, receipt = collected
    truth, flows = rows(root / 'TRUTH.jsonl'), rows(root / 'FLOW.jsonl')
    assert len(truth) == 48 and len(flows) == 96
    assert receipt['completed_mask_counts'] == {'0': 36, '1': 4, '2': 4, '3': 4}
    assert len({(r['prior_mask'], r['requested_mask'], r['mode']) for r in truth}) == 48
    workers = json.loads((root / 'WORKERS.json').read_text())['workers']
    assert len({r['pid'] for r in workers}) == 3
    assert all(r['src'] != r['dst'] and r['start_ns'] < r['end_ns'] <= r['controllerarrival_ns'] for r in flows)


def test_request_sizes_do_not_encode_operation_or_failure_mode(collected):
    root, _ = collected
    truth = {r['episode']: r for r in rows(root / 'TRUTH.jsonl')}
    sizes = {}
    for flow in rows(root / 'FLOW.jsonl'):
        sizes.setdefault(truth[flow['episode']]['payload_bytes'], set()).add(flow['request_bytes'])
        assert flow['response_bytes'] == 256
        if flow['phase'] == 'current':
            assert flow['status'] == {'success': 200, 'auth_denied': 401, 'operation_fail': 500}[truth[flow['episode']]['mode']]
    assert set(sizes) == {512, 2048}
    assert all(len(values) == 1 for values in sizes.values())


def test_completed_masks_come_from_independent_disk_evidence(collected):
    root, _ = collected
    partial = 0
    for row in rows(root / 'TRUTH.jsonl'):
        nonce = row['current_nonce']
        payload = (root / 'payloads' / (nonce + '.bin')).read_bytes()
        receipt_path = root / row['receipt_relpath']
        assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == row['receipt_sha256']
        receipt = json.loads(receipt_path.read_text())
        worker = root / 'workers' / row['dst']
        completed = 0
        marker = worker / 'remote_results' / (nonce + '.json')
        if marker.exists():
            actual = json.loads(marker.read_text())
            expected = hashlib.sha256(b'FIXED_REMOTE_HASH_V1\x00' + nonce.encode('ascii') + b'\x00' + payload).hexdigest()
            assert actual['result_sha256'] == expected and actual['worker'] == row['dst']
            completed |= 1
        target = worker / 'received' / (nonce + '.bin')
        if target.exists():
            if target.read_bytes() == payload:
                completed |= 2
            else:
                assert len(target.read_bytes()) == len(payload) // 2
                partial += 1
        assert completed == row['completed_mask']
        assert receipt['nonce'] == nonce
    assert partial == 8  # Both transfer-containing masks, four prior patterns.


def test_prior_events_are_observed_before_current_request_without_truth_fields(collected):
    root, _ = collected
    current = {r['episode']: r for r in rows(root / 'FLOW.jsonl') if r['phase'] == 'current'}
    events = rows(root / 'TELEMETRY.jsonl')
    allowed = {'block', 'episode', 'phase', 'time_ns', 'eventtime_ns', 'controllerarrival_ns', 'host', 'kind', 'success', 'bytes'}
    assert events
    for event in events:
        assert set(event) == allowed
        assert event['time_ns'] == event['eventtime_ns'] <= event['controllerarrival_ns']
        if event['phase'] == 'prior':
            assert event['controllerarrival_ns'] < current[event['episode']]['start_ns']
    assert {r['kind'] for r in events} == {'authentication', 'remote_job', 'file_write', 'request_end'}


def test_corrupted_transfer_rejected_even_if_receipt_claims_success(tmp_path):
    nonce, payload = '1' * 32, b'harmless dummy'
    worker = tmp_path / 'worker'
    target = worker / 'received' / (nonce + '.bin'); target.parent.mkdir(parents=True)
    target.write_bytes(payload)
    receipt = {'nonce': nonce, 'worker': 'worker', 'received_payload_bytes': len(payload),
               'received_payload_sha256': hashlib.sha256(payload).hexdigest(), 'remote_artifact': None,
               'transfer_artifact': {'relative_path': 'received/' + target.name, 'sha256': hashlib.sha256(payload).hexdigest()}}
    collector.dump(worker / 'receipts' / (nonce + '.json'), receipt)
    assert collector.verify_worker_artifacts(worker, nonce, payload)[0] == 2
    target.write_bytes(b'corrupted bytes')
    with pytest.raises(ValueError, match='Transfer artifact binding mismatch'):
        collector.verify_worker_artifacts(worker, nonce, payload)


def test_interrupted_collection_keeps_incomplete_status_and_no_completion(tmp_path, monkeypatch):
    def fail_dispatch(*args, **kwargs):
        raise RuntimeError('injected collection interruption')
    monkeypatch.setattr(collector, '_dispatch', fail_dispatch)
    root = tmp_path / 'incomplete'
    with pytest.raises(RuntimeError, match='injected collection interruption'):
        collector.collect(root, 93, blocks=1)
    assert not (root / 'COMPLETE.json').exists()
    assert json.loads((root / 'INCOMPLETE.json').read_text())['status'] == 'INCOMPLETE'


def test_existing_or_unbounded_output_rejected(tmp_path):
    root = tmp_path / 'existing'; root.mkdir(); (root / 'keep').write_text('keep')
    with pytest.raises(ValueError, match='Fresh collection'):
        collector.collect(root, 93, blocks=1)
    with pytest.raises(ValueError, match='bounded'):
        collector.collect(tmp_path / 'bad', 93, blocks=0)
    assert (root / 'keep').read_text() == 'keep'
