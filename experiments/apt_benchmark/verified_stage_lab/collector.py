"""Bounded three-process RPC mechanism lab; no shell or arbitrary destination.

The source worker makes the measured peer RPC. Controller dispatch requests are
an excluded control channel. Completion labels come from independently readable
worker artifacts, never the requested operation or injected failure mode.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import http.client
from http.server import BaseHTTPRequestHandler, HTTPServer
import itertools
import json
import multiprocessing as mp
from pathlib import Path
import random
import re
import secrets
import time

VERSION = 'FIXED_REMOTE_HASH_V1'
MAX_PAYLOAD = 4096
REPLY_BYTES = 256
MODES = ('success', 'auth_denied', 'operation_fail')


def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def dump(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n', encoding='utf-8')


def compact(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True).encode('utf-8')


def remote_result(nonce, payload):
    return sha_bytes(b'FIXED_REMOTE_HASH_V1\x00' + nonce.encode('ascii') + b'\x00' + payload)


def _worker(host, root, capability, controller_key, control, stop):
    """Own only this process's fixed workspace and the parent's fixed peers."""
    root = Path(root)
    for folder in ('receipts', 'remote_results', 'received'):
        (root / folder).mkdir(parents=True, exist_ok=True)
    peers = []

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_):
            pass

        def answer(self, code, body):
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers(); self.wfile.write(body)

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20000:
                    raise ValueError('Request size outside fixed bound')
                request = json.loads(self.rfile.read(length))
                if self.path == '/dispatch':
                    if request.get('controller_key') != controller_key:
                        raise ValueError('Invalid private dispatch capability')
                    target = request['target']
                    if not isinstance(target, int) or target not in range(len(peers)) or peers[target]['host'] == host:
                        raise ValueError('Invalid peer index')
                    peer = peers[target]
                    body = compact(request['rpc'])
                    connection = http.client.HTTPConnection('127.0.0.1', peer['port'], timeout=10)
                    began = time.perf_counter_ns()
                    try:
                        connection.request('POST', '/rpc', body=body, headers={'Content-Type': 'application/json'})
                        response = connection.getresponse(); reply = response.read()
                        code = response.status
                    finally:
                        connection.close()
                    ended = time.perf_counter_ns()
                    result = {'start_ns': began, 'end_ns': ended, 'request_bytes': len(body),
                              'response_bytes': len(reply), 'status': code, 'src': host, 'dst': peer['host']}
                    self.answer(200, compact(result)); return
                if self.path != '/rpc':
                    raise ValueError('Unsupported fixed route')
                nonce = request['nonce']
                if not isinstance(nonce, str) or not re.fullmatch('[0-9a-f]{32}', nonce):
                    raise ValueError('Invalid bounded nonce')
                mask, fail = request['operation'], request['gate']
                if type(mask) is not int or mask not in range(4) or type(fail) is not int or fail not in (0, 1):
                    raise ValueError('Invalid fixed operation')
                payload_hex = request['payload_hex']
                if not isinstance(payload_hex, str) or len(payload_hex) > 2 * MAX_PAYLOAD:
                    raise ValueError('Invalid bounded dummy payload')
                payload = bytes.fromhex(payload_hex)
                if not payload:
                    raise ValueError('Empty dummy payload')
                receipt_path = root / 'receipts' / (nonce + '.json')
                if receipt_path.exists():
                    raise ValueError('Replayed nonce')
                accepted = secrets.compare_digest(str(request.get('capability', '')), capability)
                events = [{'time_ns': time.perf_counter_ns(), 'host': host, 'kind': 'authentication',
                           'success': accepted, 'bytes': 0}]
                receipt = {'version': 1, 'nonce': nonce, 'worker': host, 'worker_pid': mp.current_process().pid,
                           'received_payload_bytes': len(payload), 'received_payload_sha256': sha_bytes(payload),
                           'remote_artifact': None, 'transfer_artifact': None, 'events': events}
                status = 401 if not accepted else 500 if fail else 200
                if accepted:
                    if mask & 1:
                        # A fixed computation, never an externally supplied command.
                        if not fail:
                            result_digest = remote_result(nonce, payload)
                            finished = time.perf_counter_ns()
                            artifact = {'version': VERSION, 'nonce': nonce, 'worker': host,
                                        'completed_ns': finished, 'result_sha256': result_digest}
                            path = root / 'remote_results' / (nonce + '.json'); dump(path, artifact)
                            receipt['remote_artifact'] = {'relative_path': 'remote_results/' + path.name,
                                                          'sha256': sha_file(path), 'completed_ns': finished}
                        events.append({'time_ns': time.perf_counter_ns(), 'host': host, 'kind': 'remote_job',
                                       'success': not bool(fail), 'bytes': 0})
                    if mask & 2:
                        # A failed transfer writes an intentionally incomplete object.
                        received = payload[:len(payload) // 2] if fail else payload
                        path = root / 'received' / (nonce + '.bin'); path.write_bytes(received)
                        finished = time.perf_counter_ns()
                        receipt['transfer_artifact'] = {'relative_path': 'received/' + path.name,
                                                        'sha256': sha_file(path), 'bytes': len(received),
                                                        'completed_ns': finished}
                        events.append({'time_ns': finished, 'host': host, 'kind': 'file_write',
                                       'success': not bool(fail), 'bytes': len(received)})
                events.append({'time_ns': time.perf_counter_ns(), 'host': host, 'kind': 'request_end',
                               'success': status == 200, 'bytes': len(payload)})
                receipt['response_status'] = status
                dump(receipt_path, receipt)
                # Exactly the same response envelope and size for all outcomes.
                answer = b'{"recorded":true}'
                self.answer(status, answer + b' ' * (REPLY_BYTES - len(answer)))
            except Exception:
                # Invalid controller requests are infrastructure failures, not labels.
                answer = b'{"invalid_request":true}'
                self.answer(400, answer + b' ' * (REPLY_BYTES - len(answer)))

    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.timeout = .2
    control.send({'host': host, 'port': server.server_address[1], 'pid': mp.current_process().pid,
                  'clock_ns': time.perf_counter_ns()})
    peers.extend(control.recv())
    try:
        while not stop.is_set():
            server.handle_request()
    finally:
        server.server_close(); control.close()


def verify_worker_artifacts(worker_root, nonce, payload):
    """Inspect actual persisted evidence; requested mask and mode are not inputs."""
    worker_root = Path(worker_root)
    receipt_path = worker_root / 'receipts' / (nonce + '.json')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt['nonce'] != nonce or receipt['received_payload_bytes'] != len(payload) or receipt['received_payload_sha256'] != sha_bytes(payload):
        raise ValueError('Worker received a different dummy payload')
    completed = 0
    marker = receipt['remote_artifact']
    if marker is not None:
        path = worker_root / 'remote_results' / (nonce + '.json')
        if marker['relative_path'] != 'remote_results/' + path.name or sha_file(path) != marker['sha256']:
            raise ValueError('Remote artifact binding mismatch')
        actual = json.loads(path.read_text(encoding='utf-8'))
        if (actual['version'] == VERSION and actual['nonce'] == nonce and actual['worker'] == receipt['worker']
                and actual['result_sha256'] == remote_result(nonce, payload)):
            completed |= 1
    transfer = receipt['transfer_artifact']
    if transfer is not None:
        path = worker_root / 'received' / (nonce + '.bin')
        if transfer['relative_path'] != 'received/' + path.name or sha_file(path) != transfer['sha256']:
            raise ValueError('Transfer artifact binding mismatch')
        if path.read_bytes() == payload:
            completed |= 2
    return completed, receipt


def _dispatch(peer, target, controller_key, rpc):
    connection = http.client.HTTPConnection('127.0.0.1', peer['port'], timeout=15)
    before = time.perf_counter_ns()
    try:
        body = compact({'controller_key': controller_key, 'target': target, 'rpc': rpc})
        connection.request('POST', '/dispatch', body=body, headers={'Content-Type': 'application/json'})
        response = connection.getresponse(); data = response.read()
        if response.status != 200:
            raise RuntimeError('Control dispatch failed')
        flow = json.loads(data)
    finally:
        connection.close()
    after = time.perf_counter_ns()
    if not before <= flow['start_ns'] <= flow['end_ns'] <= after:
        raise RuntimeError('Cross-process monotonic clock check failed')
    if flow['response_bytes'] != REPLY_BYTES or flow['status'] not in (200, 401, 500):
        raise RuntimeError('Fixed RPC response contract failed')
    flow['controllerarrival_ns'] = after
    return flow


def collect(output: Path, seed: int, blocks: int = 48, reps: int = 1):
    output = Path(output).resolve()
    if blocks < 1 or reps < 1 or blocks * reps > 192:
        raise ValueError('Collection outside bounded block/repetition range')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Fresh collection directory required')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'payloads').mkdir()
    rng = random.Random(seed)
    scheme = {'prior_masks': [0, 1, 2, 3], 'requested_masks': [0, 1, 2, 3], 'modes': list(MODES)}
    manifest = {'version': 1, 'seed': seed, 'blocks': blocks, 'reps': reps,
                'episodes_per_block_per_rep': 48, 'planned_current_episodes': blocks * reps * 48,
                'scheme': scheme, 'payload_buckets': [512, 2048], 'reply_bytes': REPLY_BYTES,
                'source_sha256': sha_file(__file__), 'started_utc': datetime.now(timezone.utc).isoformat(),
                'worker_hosts': ['worker_0', 'worker_1', 'worker_2'],
                'role_assignments': 'Assigned by the separately frozen model protocol; workers are otherwise identical processes.',
                'scope': 'Local loopback process mechanism test; not actual intrusion, APT, independent machines or live threat detection.',
                'measurement': 'FLOW byte counts measure HTTP request/response bodies, not packet-capture bytes. Control dispatch traffic excluded.',
                'clock': 'One OS perf_counter_ns clock; every peer RPC interval checked inside controller interval.',
                'state': 'Nonce-isolated artifacts; model history must use only the corresponding episode prelude, not other episodes.',
                'worker_secret_values_in_artifacts': False}
    dump(output / 'MANIFEST.json', manifest)
    context = mp.get_context('spawn'); stop = context.Event()
    workers, pipes, peers = [], [], []
    controller_key = secrets.token_hex(32)
    capabilities = [secrets.token_hex(32) for _ in range(3)]
    total_started = time.perf_counter()
    counts = {'0': 0, '1': 0, '2': 0, '3': 0}
    completed_episodes = 0
    try:
        for i in range(3):
            parent, child = context.Pipe()
            process = context.Process(target=_worker,
                                      args=(f'worker_{i}', str(output / 'workers' / f'worker_{i}'), capabilities[i], controller_key, child, stop),
                                      name=f'fixed-lab-worker-{i}')
            process.start(); child.close()
            workers.append(process); pipes.append(parent)
        for pipe in pipes:
            if not pipe.poll(20):
                raise RuntimeError('Worker startup timeout')
            peers.append(pipe.recv())
        for pipe in pipes: pipe.send(peers)
        dump(output / 'WORKERS.json', {'workers': peers, 'all_loopback': True})
        paths = {name: output / (name + '.jsonl') for name in ('TELEMETRY', 'FLOW', 'TRUTH')}
        with paths['TELEMETRY'].open('w', encoding='utf-8') as telemetry, paths['FLOW'].open('w', encoding='utf-8') as flows, paths['TRUTH'].open('w', encoding='utf-8') as truth:
            for block in range(blocks):
                combinations = list(itertools.product(range(4), range(4), MODES, range(reps)))
                rng.shuffle(combinations)
                for local, (prior_mask, requested, mode, repetition) in enumerate(combinations):
                    episode = f'b{block:04d}_e{local:04d}'
                    src = rng.randrange(3); dst = rng.choice([j for j in range(3) if j != src])
                    payload_size = rng.choice([512, 2048])
                    payload = rng.randbytes(payload_size)
                    current_nonce = f'{rng.getrandbits(128):032x}'
                    prior_nonce = f'{rng.getrandbits(128):032x}'
                    # The same benign random buffer is used in both phases.
                    (output / 'payloads' / (current_nonce + '.bin')).write_bytes(payload)
                    (output / 'payloads' / (prior_nonce + '.bin')).write_bytes(payload)
                    phase_evidence = {}
                    for phase, mask, phase_mode, nonce in [('prior', prior_mask, 'success', prior_nonce),
                                                          ('current', requested, mode, current_nonce)]:
                        token = capabilities[dst] if phase_mode != 'auth_denied' else '0' * 64
                        if token == capabilities[dst] and phase_mode == 'auth_denied':
                            token = '1' * 64
                        rpc = {'nonce': nonce, 'capability': token, 'operation': mask,
                               'gate': int(phase_mode == 'operation_fail'), 'payload_hex': payload.hex()}
                        flow = _dispatch(peers[src], dst, controller_key, rpc)
                        flow.update({'block': block, 'episode': episode, 'phase': phase})
                        flows.write(json.dumps(flow, separators=(',', ':')) + '\n')
                        worker_root = output / 'workers' / peers[dst]['host']
                        completed, receipt = verify_worker_artifacts(worker_root, nonce, payload)
                        observed_at = time.perf_counter_ns()
                        if phase == 'prior' and completed != prior_mask:
                            raise RuntimeError('Prelude did not complete as intended')
                        for event in receipt['events']:
                            if not flow['start_ns'] <= event['time_ns'] <= flow['end_ns']:
                                raise RuntimeError('Event outside corresponding RPC interval')
                            telemetry.write(json.dumps({'block': block, 'episode': episode, 'phase': phase, **event,
                                                        'eventtime_ns': event['time_ns'], 'controllerarrival_ns': observed_at}, separators=(',', ':')) + '\n')
                        receipt_path = worker_root / 'receipts' / (nonce + '.json')
                        phase_evidence[phase] = {'completed_mask': completed,
                                                 'receipt_relpath': receipt_path.relative_to(output).as_posix(),
                                                 'receipt_sha256': sha_file(receipt_path)}
                        if phase == 'prior': time.sleep(rng.uniform(.0001, .001))
                    row = {'block': block, 'episode': episode, 'repetition': repetition,
                           'prior_mask': prior_mask, 'requested_mask': requested,
                           'completed_mask': phase_evidence['current']['completed_mask'], 'mode': mode,
                           'current_nonce': current_nonce, 'prior_nonce': prior_nonce,
                           'src': peers[src]['host'], 'dst': peers[dst]['host'],
                           'payload_bytes': payload_size, 'payload_sha256': sha_bytes(payload),
                           'receipt_relpath': phase_evidence['current']['receipt_relpath'],
                           'receipt_sha256': phase_evidence['current']['receipt_sha256'],
                           'prior_receipt_relpath': phase_evidence['prior']['receipt_relpath'],
                           'prior_receipt_sha256': phase_evidence['prior']['receipt_sha256']}
                    truth.write(json.dumps(row, separators=(',', ':')) + '\n')
                    counts[str(row['completed_mask'])] += 1; completed_episodes += 1
                telemetry.flush(); flows.flush(); truth.flush()
                print(f'COLLECT_BLOCK {block + 1}/{blocks} episodes={completed_episodes}', flush=True)
        result = {'status': 'COMPLETE', 'completed_episodes': completed_episodes,
                  'planned_episodes': manifest['planned_current_episodes'], 'completed_mask_counts': counts,
                  'peer_rpc_count': 2 * completed_episodes, 'elapsed_seconds': time.perf_counter() - total_started,
                  'source_sha256': sha_file(__file__), 'manifest_sha256': sha_file(output / 'MANIFEST.json'),
                  'worker_process_count': 3, 'local_loopback_only': True,
                  'scientific_scope': manifest['scope'],
                  'artifact_hashes': {name: sha_file(output / name) for name in ('MANIFEST.json', 'WORKERS.json', 'TELEMETRY.jsonl', 'FLOW.jsonl', 'TRUTH.jsonl')}}
        if completed_episodes != manifest['planned_current_episodes']:
            raise RuntimeError('Incomplete frozen roster')
        dump(output / 'COLLECT_RECEIPT.json', result)
        dump(output / 'COMPLETE.json', {'receipt_sha256': sha_file(output / 'COLLECT_RECEIPT.json')})
        return result
    except Exception as exc:
        dump(output / 'INCOMPLETE.json', {'status': 'INCOMPLETE', 'error_type': type(exc).__name__,
                                         'completed_episodes': completed_episodes,
                                         'planned_episodes': manifest['planned_current_episodes']})
        raise
    finally:
        stop.set()
        for process in workers:
            process.join(timeout=3)
            if process.is_alive():
                process.terminate(); process.join(timeout=3)
        for pipe in pipes: pipe.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--blocks', type=int, default=48)
    parser.add_argument('--reps', type=int, default=1)
    args = parser.parse_args()
    receipt = collect(args.output, args.seed, args.blocks, args.reps)
    print(json.dumps({key: receipt[key] for key in ('status', 'completed_episodes', 'completed_mask_counts', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
