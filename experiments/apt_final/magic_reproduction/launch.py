"""One bounded GPU attempt using the existing host and a verified frozen bundle."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import tarfile
import time

from ..native_graph.cloud_control import Controller, parse_stamp
from .provenance import HERE, REPO, digest, read, verify_runtime
NATIVE = HERE.parent / "native_graph"


def build_bundle(data_dir, source_dir, wheel_dir, registration, destination):
    record = verify_runtime(registration, data_dir, source_dir)
    sources = [(REPO/rel, 'repo/'+rel) for rel in record['code_hashes']]
    sources += [(Path(registration),'repo/experiments/apt_final/magic_reproduction/REGISTRATION.json')]
    sources += [(Path(data_dir)/rel,'data/'+rel) for rel in record['data_files']]
    sources += [(Path(source_dir)/rel,'upstream/'+rel) for rel in record['upstream_files']]
    sources += [(Path(source_dir)/'SOURCE_MANIFEST.json','upstream/SOURCE_MANIFEST.json')]
    runtime = read(HERE/'RUNTIME.json')
    wheel = Path(wheel_dir)/runtime['wheel']
    if digest(wheel) != runtime['wheel_sha256']:
        raise ValueError('DGL wheel hash mismatch')
    sources += [(wheel,'wheels/'+wheel.name)]
    if len(sources)>2000 or sum(p.stat().st_size for p,_ in sources)>4_000_000_000:
        raise ValueError('Input archive exceeds frozen bound')
    with tarfile.open(destination,'x:gz') as archive:
        for path,rel in sources:
            archive.add(path,arcname=rel,recursive=False)
    return digest(destination)


def collect(controller, private):
    settings = controller.settings
    result_prefix = settings['prefix'] + 'outputs/'
    archive = private / 'result.tar.gz'
    marker = private / 'result.sha256'
    controller.transfer('download', marker, result_prefix + 'result.sha256')
    controller.transfer('download', archive, result_prefix + 'result.tar.gz')
    if marker.read_text().strip() != digest(archive):
        raise ValueError('Result transport checksum mismatch')
    output = private / 'collected'
    output.mkdir(exist_ok=False)
    with tarfile.open(archive, 'r:gz') as pack:
        names = set()
        total = 0
        for member in pack.getmembers():
            name = member.name.rstrip('/') if member.isdir() else member.name
            parts = name.split('/')
            if (not name or PurePosixPath(name).is_absolute() or '\\' in name or ':' in name
                    or any(p in {'','.', '..'} for p in parts) or parts[0] != 'outputs' or member.size < 0):
                raise ValueError('Unsafe output member path')
            target = (output/member.name).resolve()
            key = str(target).casefold()
            if key in names or not target.is_relative_to(output.resolve()) or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe or colliding output member')
            names.add(key)
            total += member.size
            if len(names) > 2000 or total > 4_000_000_000:
                raise ValueError('Output exceeds collection bound')
        pack.extractall(output)
    return {'transport_sha256': digest(archive), 'transport_bytes': archive.stat().st_size,
            'worker': read(output/'outputs/RESULTS.json') if (output/'outputs/RESULTS.json').exists() else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--settings', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--registration', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--wheel-dir', type=Path, required=True)
    parser.add_argument('--datasets', choices=['theia','cadets','theia,cadets'], default='theia,cadets')
    args = parser.parse_args()
    controller = Controller(args.settings)
    private = args.settings.resolve().parent
    summary_path = private / 'EXECUTION.json'
    if summary_path.exists() or controller.active_path.exists():
        raise ValueError('Use a separately reviewed new attempt; this attempt already exists')
    bundle = private/'bundle.tar.gz'
    sha = build_bundle(args.data_dir, args.source_dir, args.wheel_dir, args.registration, bundle)
    summary = {'scope': 'DEVELOPMENT_ONLY', 'started_utc': datetime.now(timezone.utc).isoformat(),
               'bundle_sha256': sha, 'bundle_bytes': bundle.stat().st_size,
               'status': 'PREPARED', 'controller_sha256': digest(NATIVE/'cloud_control.py'),
               'compute_started': False, 'scientific_completion': False, 'datasets':args.datasets.split(',')}
    def save():
        summary_path.write_text(json.dumps(summary, indent=2, default=str)+'\n', encoding='utf-8')
    def emit(event, **fields):
        print(json.dumps({'event':event, **fields}, default=str), flush=True)
    save()
    settings = controller.settings
    controller.transfer('upload', bundle, settings['prefix']+'input/bundle.tar.gz')
    try:
        summary['start'] = controller.start(HERE/'PROTOCOL.md', args.registration)
        summary['compute_started'] = True
        save()
        emit('start_requested_watchdog_verified')
        for _ in range(36):
            state = controller.instance()['State']['Name']
            status = controller.client('ssm').describe_instance_information(Filters=[
                {'Key':'InstanceIds','Values':[settings['instance']]}])['InstanceInformationList']
            if state == 'running' and any(x.get('PingStatus') == 'Online' for x in status):
                break
            time.sleep(10)
        else:
            raise ValueError('Host did not become SSM-ready within six minutes')
        active = controller.active()
        remaining = (parse_stamp(active['worker_deadline_utc']) - datetime.now(timezone.utc)).total_seconds()
        timeout = min(3000, int(remaining)-160)
        if timeout < 360:
            raise ValueError('Insufficient remaining worker budget')
        # Delivery and bootstrap consume this deadline; publication gets 240s inside it.
        script_deadline = int(time.time()) + timeout - 30
        bundle_uri = 's3://'+settings['bucket']+'/'+settings['prefix']+'input/bundle.tar.gz'
        output_uri = 's3://'+settings['bucket']+'/'+settings['prefix']+'outputs'
        run_id = 'apt-magic-repro-'+active['run_id'][:16]
        bootstrap = private/'bootstrap.sh'
        body = (HERE/'run_cloud.sh').read_text(encoding='utf-8')
        # Arguments are explicit shell-quoted values, never stringified shell code.
        invocation = 'set -- '+' '.join(shlex.quote(str(x)) for x in
                     [bundle_uri,sha,output_uri,run_id,script_deadline,args.datasets])+'\n'
        delimiter = 'APT_MAGIC_REPRODUCTION_SCRIPT'
        if delimiter in body:
            raise ValueError('Bootstrap delimiter collision')
        bootstrap.write_text("bash <<'"+delimiter+"'\n"+invocation+body+'\n'+delimiter+'\n',
                             encoding='utf-8', newline='\n')
        summary['command'] = controller.send(bootstrap, timeout)
        summary['command_timeout_seconds'] = timeout
        save()
        command_id = summary['command']['command_id']
        emit('worker_submitted', timeout_seconds=timeout)
        poll_errors = 0
        while True:
            try:
                result = controller.poll(command_id)
                poll_errors = 0
            except Exception:
                poll_errors += 1
                if poll_errors > 3 or datetime.now(timezone.utc) >= parse_stamp(active['worker_deadline_utc']):
                    raise
                time.sleep(10)
                continue
            summary['last_poll'] = result
            save()
            emit('worker_status', status=result['status'])
            if result['status'] in {'Success','Failed','TimedOut','Cancelled','Cancelling'}:
                break
            if datetime.now(timezone.utc) >= parse_stamp(active['worker_deadline_utc']):
                raise ValueError('Absolute worker deadline reached')
            time.sleep(25)
        summary['status'] = 'WORKER_FINISHED'
    except Exception as error:
        summary.update(status='INCOMPLETE', error_type=type(error).__name__)
        # Detailed account/API errors stay in private controller receipts.
        if isinstance(error, ValueError):
            summary['reason'] = str(error)
        emit('attempt_incomplete', error_type=type(error).__name__)
    finally:
        if controller.active_path.exists():
            try:
                summary['stop'] = controller.stop()
                save()
                emit('stop_requested')
                for _ in range(42):
                    final = controller.finalize()
                    summary['finalize'] = final
                    save()
                    if final.get('status') == 'CLOSED_VERIFIED_STOPPED':
                        emit('host_stopped_verified')
                        break
                    time.sleep(10)
                else:
                    summary['shutdown_unresolved'] = True
            except Exception as error:
                summary.update(shutdown_unresolved=True, shutdown_error_type=type(error).__name__)
        save()
    try:
        summary['collection'] = collect(controller, private)
        worker = summary['collection']['worker'] or {}
        summary['scientific_completion'] = worker.get('all_selected_evaluations_complete') is True
        summary['all_registered_evaluations_complete_in_this_attempt'] = worker.get('all_registered_evaluations_complete_in_this_attempt') is True
        if summary.get('finalize',{}).get('status') == 'CLOSED_VERIFIED_STOPPED':
            if worker.get('status') == 'COMPLETE_SELECTED_REPRODUCTIONS' and summary['scientific_completion']:
                summary['status'] = 'COMPLETED_AND_STOPPED'
            elif worker.get('status') == 'COMPLETE_FEASIBILITY_WITH_DEFERRED_EVALUATION':
                summary['status'] = 'FEASIBILITY_COMPLETE_AND_STOPPED'
    except Exception as error:
        summary['collection_error_type'] = type(error).__name__
    save()
    emit('closed', status=summary['status'], scientific_completion=summary['scientific_completion'])
    return 0 if summary['status'] in {'COMPLETED_AND_STOPPED','FEASIBILITY_COMPLETE_AND_STOPPED'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
