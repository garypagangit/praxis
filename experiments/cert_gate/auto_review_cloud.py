"""One bounded GPU bot-review attempt; raw evidence and AWS receipts stay private.

Run as python -m experiments.cert_gate.auto_review_cloud. This module performs
no cloud operation on import. It does not possess or upload an answer key.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shlex
import tarfile
import time

from experiments.apt_final.native_graph.cloud_control import (
    Controller, committed_identity, digest, parse_stamp,
)
from .auto_review import _prepared


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODEL = {
    'model_id': 'Qwen/Qwen3-4B-Instruct-2507',
    'revision': 'cdbee75f17c01a7cc42f958dc650907174af0554',
    'max_input_tokens': 16384,
    'max_new_tokens': 512,
}
PREPARED_FILES = ('CASES.json', 'REQUESTS.jsonl', 'PROMPT.txt', 'PREPARED.json')
REQUIRED_CODE = (
    'experiments/cert_gate/auto_review.py',
    'experiments/cert_gate/auto_review_cloud.py',
    'experiments/cert_gate/run_auto_review_cloud.sh',
    'experiments/apt_final/native_graph/cloud_control.py',
)
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
INPUT_NAMES = frozenset({'auto_review.py', 'BUNDLE_MANIFEST.json',
                         'records/FINAL_PROTOCOL.json', 'records/FINAL_RUNTIME.json'} |
                        {'prepared/' + name for name in PREPARED_FILES})


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, default=str) + '\n', encoding='utf-8')


def validate_model_contract(protocol):
    spec = protocol.get('automated_review', {})
    if not isinstance(spec, dict) or any(spec.get(key) != value for key, value in MODEL.items()):
        raise ValueError('Protocol automated_review must match the frozen model/revision/token caps')


def verify_runtime(protocol_path, freeze_path):
    identities = {'protocol': committed_identity(protocol_path),
                  'runtime_freeze': committed_identity(freeze_path)}
    if identities['protocol']['commit'] != identities['runtime_freeze']['commit']:
        raise ValueError('Protocol and runtime freeze must share Git HEAD')
    protocol, frozen = read_json(protocol_path), read_json(freeze_path)
    validate_model_contract(protocol)
    hashes = frozen.get('code_hashes')
    if not isinstance(hashes, dict) or not set(REQUIRED_CODE).issubset(hashes):
        raise ValueError('Runtime freeze omits mandatory bot worker/controller files')
    for relative, expected in hashes.items():
        posix = PurePosixPath(relative)
        if posix.is_absolute() or '..' in posix.parts or '\\' in relative or ':' in relative:
            raise ValueError('Runtime freeze contains an unsafe source path')
        path = (REPO / relative).resolve(strict=True)
        if not path.is_relative_to(REPO) or path.is_symlink():
            raise ValueError('Runtime source is outside the repository')
        identity = committed_identity(path)
        if identity['sha256'] != expected or identity['commit'] != identities['protocol']['commit']:
            raise ValueError('Runtime source does not match the committed freeze: ' + relative)
    return identities


def build_bundle(prepared, protocol, freeze, destination):
    """Allowlist-only bundle; sibling answer keys and source datasets are ignored."""
    prepared = Path(prepared).resolve(strict=True)
    if prepared.is_relative_to(REPO):
        raise ValueError('Prepared private cases must be outside the repository')
    identities = verify_runtime(protocol, freeze)
    manifest, cases = _prepared(prepared)
    if manifest.get('code_sha256') != digest(HERE / 'auto_review.py'):
        raise ValueError('Prepare the cases after freezing the final auto_review.py bytes')
    if manifest.get('answer_key_accessed') is not False or manifest.get('human_review_performed') is not False:
        raise ValueError('Prepared review must remain blinded and explicitly automated')
    sources = [(HERE / 'auto_review.py', 'auto_review.py'),
               (Path(protocol), 'records/FINAL_PROTOCOL.json'),
               (Path(freeze), 'records/FINAL_RUNTIME.json')]
    for name in PREPARED_FILES:
        path = prepared / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Prepared member must be a regular file')
        sources.append((path, 'prepared/' + name))
    if sum(path.stat().st_size for path, _ in sources) > MAX_ARCHIVE_BYTES:
        raise ValueError('Prepared bundle exceeds the fixed 128 MiB input bound')
    contents = {name: {'sha256': digest(path), 'bytes': path.stat().st_size}
                for path, name in sources}
    record = {'scope': 'AUTOMATED_BOT_REVIEW_NO_ANSWER_KEY', 'model': MODEL,
              'files': contents, 'identities': identities,
              'case_ids_sha256': hashlib.sha256(json.dumps(sorted(case['case_id'] for case in cases)).encode()).hexdigest(),
              'answer_key_uploaded': False, 'human_review_performed': False}
    with tarfile.open(destination, 'x:gz') as archive:
        for path, name in sources:
            archive.add(path, arcname=name, recursive=False)
        raw = (json.dumps(record, sort_keys=True) + '\n').encode('utf-8')
        member = tarfile.TarInfo('BUNDLE_MANIFEST.json')
        member.size, member.mode = len(raw), 0o600
        archive.addfile(member, io.BytesIO(raw))
    return digest(destination), record


def safe_extract(archive_path, output):
    """Extract regular bounded results into a new private directory, without links."""
    output = Path(output).resolve()
    output.mkdir(exist_ok=False)
    with tarfile.open(archive_path, 'r:gz') as pack:
        seen, total, members = set(), 0, pack.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            target = (output / member.name).resolve()
            key = str(target).casefold()
            if (path.is_absolute() or '..' in path.parts or '\\' in member.name or ':' in member.name
                    or key in seen or not target.is_relative_to(output)
                    or not (member.isfile() or member.isdir())):
                raise ValueError('Unsafe or colliding result member')
            seen.add(key)
            total += member.size
            if len(seen) > 256 or total > MAX_ARCHIVE_BYTES:
                raise ValueError('Result archive exceeds bounded review output size')
        for member in members:
            target = output / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with pack.extractfile(member) as source, target.open('xb') as destination:
                    while block := source.read(1024 * 1024):
                        destination.write(block)


def collect(controller, private, bundle_record):
    prefix = controller.settings['prefix'] + 'outputs/'
    archive, marker = private / 'result.tar.gz', private / 'result.sha256'
    if archive.exists() or marker.exists():
        raise ValueError('Refuse to overwrite existing result downloads')
    controller.transfer('download', marker, prefix + 'result.sha256')
    controller.transfer('download', archive, prefix + 'result.tar.gz')
    if archive.stat().st_size > MAX_ARCHIVE_BYTES or marker.read_text().strip() != digest(archive):
        raise ValueError('Result archive size or transport checksum mismatch')
    output = private / 'collected'
    safe_extract(archive, output)
    worker_path = output / 'outputs/WORKER_STATUS.json'
    worker = read_json(worker_path) if worker_path.exists() else None
    frozen_path = output / 'outputs/review/frozen/FROZEN.json'
    answer_status = 'NO_FROZEN_REVIEW'
    if frozen_path.exists():
        frozen = read_json(frozen_path)
        if (frozen.get('reviewer_kind') != 'AUTOMATED_BOT' or frozen.get('case_count') != 50
                or frozen.get('human_review_performed') is not False
                or frozen.get('answer_key_accessed') is not False
                or any(frozen.get('model', {}).get(k) != v for k, v in MODEL.items())
                or frozen.get('prepared_manifest_sha256') != bundle_record['files']['prepared/PREPARED.json']['sha256']
                or frozen.get('code_sha256') != bundle_record['files']['auto_review.py']['sha256']):
            raise ValueError('Collected review does not match the frozen blinded run')
        for name, key in [('ANSWERS.json', 'answers_sha256'), ('RAW_OUTPUTS.jsonl', 'raw_outputs_sha256')]:
            if digest(frozen_path.parent / name) != frozen.get(key):
                raise ValueError('Collected review output hash mismatch')
        answers = read_json(frozen_path.parent / 'ANSWERS.json')
        ids = [row['case_id'] for row in answers]
        if (len(answers) != 50 or len(set(ids)) != 50
                or hashlib.sha256(json.dumps(sorted(ids)).encode()).hexdigest() != bundle_record['case_ids_sha256']):
            raise ValueError('Collected review case identities are incomplete')
        answer_status = 'FROZEN_AUTOMATED_REVIEW_COLLECTED_UNGRADED'
    return {'transport_sha256': digest(archive), 'transport_bytes': archive.stat().st_size,
            'worker': worker, 'answer_status': answer_status, 'human_review_performed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('settings', 'prepared', 'protocol', 'freeze'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    private = args.settings.resolve(strict=True).parent
    if private.is_relative_to(REPO):
        raise ValueError('Settings and cloud receipts must stay outside the repository')
    controller = Controller(args.settings)
    summary_path = private / 'EXECUTION.json'
    if summary_path.exists() or controller.active_path.exists():
        raise ValueError('A cloud attempt already exists; no automatic restart')
    bundle = private / 'bundle.tar.gz'
    sha, bundle_record = build_bundle(args.prepared, args.protocol, args.freeze, bundle)
    summary = {'scope': 'AUTOMATED_BOT_REVIEW_ONLY', 'status': 'PREPARED',
               'started_utc': datetime.now(timezone.utc).isoformat(),
               'bundle_sha256': sha, 'bundle_bytes': bundle.stat().st_size,
               'model': MODEL, 'compute_started': False, 'automated_review_collected': False,
               'human_review_performed': False, 'answer_key_uploaded': False}

    def save():
        write_json(summary_path, summary)

    def emit(event, **fields):
        print(json.dumps({'event': event, **fields}), flush=True)

    settings = controller.settings
    save()
    try:
        controller.transfer('upload', bundle, settings['prefix'] + 'input/bundle.tar.gz')
        summary['start'] = controller.start(args.protocol, args.freeze)
        summary['compute_started'] = True
        save()
        emit('start_requested_watchdog_verified')
        for _ in range(36):
            state = controller.instance()['State']['Name']
            info = controller.client('ssm').describe_instance_information(Filters=[
                {'Key': 'InstanceIds', 'Values': [settings['instance']]}])['InstanceInformationList']
            if state == 'running' and any(row.get('PingStatus') == 'Online' for row in info):
                break
            time.sleep(10)
        else:
            raise ValueError('Host did not become SSM-ready within six minutes')
        active = controller.active()
        remaining = (parse_stamp(active['worker_deadline_utc']) - datetime.now(timezone.utc)).total_seconds()
        timeout = min(3000, int(remaining) - 160)
        if timeout < 360:
            raise ValueError('Insufficient remaining worker budget')
        deadline = int(time.time()) + timeout - 30
        bundle_uri = 's3://' + settings['bucket'] + '/' + settings['prefix'] + 'input/bundle.tar.gz'
        output_uri = 's3://' + settings['bucket'] + '/' + settings['prefix'] + 'outputs'
        run_id = 'cert-gate-bot-' + active['run_id'][:16]
        script = (HERE / 'run_auto_review_cloud.sh').read_text(encoding='utf-8')
        delimiter = 'CERT_GATE_AUTOMATED_REVIEW_SCRIPT'
        if delimiter in script:
            raise ValueError('Bootstrap delimiter collision')
        invocation = 'set -- ' + ' '.join(shlex.quote(str(x)) for x in
                                         (bundle_uri, sha, output_uri, run_id, deadline)) + '\n'
        bootstrap = private / 'bootstrap.sh'
        bootstrap.write_text("bash <<'" + delimiter + "'\n" + invocation + script + '\n' + delimiter + '\n',
                             encoding='utf-8', newline='\n')
        summary['command'] = controller.send(bootstrap, timeout)
        summary['command_timeout_seconds'] = timeout
        save()
        emit('worker_submitted', timeout_seconds=timeout)
        errors = 0
        while True:
            try:
                result = controller.poll(summary['command']['command_id'])
                errors = 0
            except Exception:
                errors += 1
                if errors > 3 or datetime.now(timezone.utc) >= parse_stamp(active['worker_deadline_utc']):
                    raise
                time.sleep(10)
                continue
            summary['last_poll'] = result
            progress = {}
            try:
                item = controller.client('s3').get_object(Bucket=settings['bucket'], Key=settings['prefix'] + 'outputs/PROGRESS.json')
                body = item['Body']
                try:
                    observed = json.loads(body.read(8193))
                finally:
                    body.close()
                count = observed.get('cases_completed')
                if type(count) is int and 0 <= count <= 50:
                    progress['cases_completed'] = count
            except Exception:
                pass  # Progress publication is diagnostic; SSM and watchdog remain authoritative.
            save()
            emit('worker_status', status=result['status'], **progress)
            if result['status'] in {'Success', 'Failed', 'TimedOut', 'Cancelled', 'Cancelling'}:
                break
            if datetime.now(timezone.utc) >= parse_stamp(active['worker_deadline_utc']):
                raise ValueError('Absolute worker deadline reached')
            time.sleep(25)
        summary['status'] = 'WORKER_FINISHED'
    except Exception as error:
        summary.update(status='INCOMPLETE', error_type=type(error).__name__, private_error=str(error))
        emit('attempt_incomplete', error_type=type(error).__name__)
    finally:
        if controller.active_path.exists():
            try:
                summary['stop'] = controller.stop()
                save()
                emit('stop_requested')
                for _ in range(42):
                    summary['finalize'] = controller.finalize()
                    save()
                    if summary['finalize'].get('status') == 'CLOSED_VERIFIED_STOPPED':
                        emit('host_stopped_verified')
                        break
                    time.sleep(10)
                else:
                    summary['shutdown_unresolved'] = True
            except Exception as error:
                summary.update(shutdown_unresolved=True, shutdown_error_type=type(error).__name__)
        save()
    try:
        summary['collection'] = collect(controller, private, bundle_record)
        summary['automated_review_collected'] = (summary['collection']['answer_status'] ==
                                                'FROZEN_AUTOMATED_REVIEW_COLLECTED_UNGRADED')
        worker_ok = (summary['collection']['worker'] or {}).get('status') == 'COMPLETE'
        if (summary['automated_review_collected'] and worker_ok
                and summary.get('last_poll', {}).get('status') == 'Success'
                and summary.get('finalize', {}).get('status') == 'CLOSED_VERIFIED_STOPPED'):
            summary['status'] = 'COMPLETED_AND_STOPPED'
    except Exception as error:
        summary.update(collection_error_type=type(error).__name__, collection_error=str(error))
    save()
    emit('closed', status=summary['status'], automated_review_collected=summary['automated_review_collected'])
    return 0 if summary['status'] == 'COMPLETED_AND_STOPPED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
